import contextlib
import io
import json
import re
import unittest
from unittest.mock import patch

import ai_compare
import central_db
import main


CLAIM = "الصدق من الأخلاق التي حث عليها الإسلام"
STRONG = "1– الصدق من الأخلاق الحميدة التي حث الإسلام عليها."
WEAK = "اللهم إني أعوذ بك من منكرات الأخلاق والأعمال والأهواء."


def evidence(text, source):
    return {"evidence": text, "source_name": source, "source_location": "location"}


class EvidenceSelectionTests(unittest.TestCase):
    def test_embedded_letters_are_not_negation(self):
        self.assertEqual(ai_compare.extract_constraints(CLAIM), [])
        self.assertEqual(ai_compare.extract_constraints("لا تكذب كل يوم"), ["كل يوم", "لا"])
        self.assertEqual(ai_compare.extract_constraints("لَا تكذب"), ["لا"])

    def test_near_exact_text_first_regardless_of_source_or_input_order(self):
        for source in ["HadeethEnc", "Dorar.net", central_db.SOURCE_NAME]:
            strong = evidence(STRONG, source)
            weak = evidence(WEAK, "another source")
            for candidates in [[weak, strong], [strong, weak]]:
                with self.subTest(source=source, strong_index=candidates.index(strong)):
                    ranked = ai_compare.prioritize_evidence(CLAIM, candidates)
                    self.assertEqual(ranked[0]["evidence"], strong)
                    self.assertEqual(ranked[0]["original_index"], candidates.index(strong) + 1)
                    self.assertEqual(len(ranked), len(candidates))

    def test_constraints_prioritize_without_excluding_other_evidence(self):
        candidates = [evidence("قراءة القرآن", "one"), evidence("قراءة القرآن كل يوم", "two")]
        ranked = ai_compare.prioritize_evidence("قراءة القرآن كل يوم", candidates)
        self.assertEqual([item["original_index"] for item in ranked], [2, 1])

    def test_vocalized_matches_and_punctuation(self):
        vocalized = evidence("الصِّدقُ من الأخْلاق الحميدة التي حث الإسلام عليها.", "HadeethEnc")
        ranked = ai_compare.prioritize_evidence(CLAIM, [evidence(WEAK, "other"), vocalized])
        self.assertEqual(ranked[0]["original_index"], 2)

    def test_no_is_not_turned_into_supported_by_ranking(self):
        with patch("ai_compare.ask_ai", return_value="NO") as ask, contextlib.redirect_stdout(io.StringIO()):
            result = ai_compare.compare_claim_with_evidence(CLAIM, [evidence(STRONG, central_db.SOURCE_NAME)])
        self.assertEqual(result["status"], "needs_review")
        self.assertIsNone(result["best_evidence"])
        ask.assert_called_once()

    def test_ai_can_still_choose_a_lower_ranked_evidence(self):
        candidates = [evidence(WEAK, "HadeethEnc"), evidence(STRONG, central_db.SOURCE_NAME)]
        with patch("ai_compare.ask_ai", side_effect=[
            "YES|1", json.dumps({"status": "needs_review", "reason": "weak evidence", "suggestion": ""}),
        ]), contextlib.redirect_stdout(io.StringIO()):
            result = ai_compare.compare_claim_with_evidence(CLAIM, candidates)
        self.assertEqual(result["best_evidence"], 1)
        self.assertEqual(result["status"], "needs_review")

    def test_analyze_uses_ranked_prompt_and_original_central_evidence_index(self):
        weak = evidence(WEAK, "HadeethEnc")
        strong = evidence(STRONG, central_db.SOURCE_NAME)
        prompts = []

        def model(prompt):
            prompts.append(prompt)
            if len(prompts) == 1:
                # Simulate selecting the first ranked candidate; verify its label
                # maps back to the original combined list rather than position 1.
                index = re.search(r"الدليل رقم (\d+):", prompt).group(1)
                self.assertEqual(index, "2")
                self.assertLess(prompt.index(STRONG), prompt.index(WEAK))
                return f"YES|{index}"
            self.assertIn(STRONG, prompt)
            self.assertNotIn(WEAK, prompt)
            return json.dumps({"status": "supported", "reason": "same meaning", "suggestion": ""})

        with patch("main.extract_claims", return_value=[CLAIM]), \
             patch("main.search_hadiths", return_value=[weak]), \
             patch("main.search_dorar", return_value=[]), \
             patch("main.search_central_db", return_value=[strong]), \
             patch("ai_compare.ask_ai", side_effect=model), contextlib.redirect_stdout(io.StringIO()):
            result = main.analyze(main.AnalyzeRequest(text=CLAIM))
        self.assertEqual(result, {"claims": [{
            "claim": CLAIM, "status": "supported", "evidence": [strong],
            "reason": "same meaning", "suggestion": "",
        }]})


if __name__ == "__main__":
    unittest.main()
