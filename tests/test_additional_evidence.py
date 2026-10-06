import unittest
from unittest.mock import patch

import main


CLAIM = "الصدق من الأخلاق التي حث عليها الإسلام"
PRIMARY = {"evidence": "الصدق من الأخلاق الحميدة التي حث الإسلام عليها.",
           "source_name": "القاعدة المركزية للمحتوى الإسلامي باللغات",
           "source_location": "نتيجة موثقة من القاعدة المركزية"}
EXTRA = {"evidence": "الصدق يهدي إلى البر.", "source_name": "HadeethEnc", "source_location": "مصدر الحديث"}


class AdditionalEvidenceTests(unittest.TestCase):
    def analyze(self, candidates, selected=1):
        evaluation = {"best_evidence": selected, "status": "supported", "reason": "unchanged reason", "suggestion": ""}
        with patch("main.extract_claims", return_value=[CLAIM]), \
             patch("main.search_hadiths", return_value=candidates), \
             patch("main.search_dorar", return_value=[]), \
             patch("main.search_central_db", return_value=[]), \
             patch("main.compare_claim_with_evidence", return_value=evaluation) as compare:
            result = main.analyze(main.AnalyzeRequest(text=CLAIM))["claims"][0]
        compare.assert_called_once_with(CLAIM, candidates)
        self.assertEqual(result["status"], "supported")
        self.assertEqual(result["reason"], "unchanged reason")
        self.assertEqual(result["suggestion"], "")
        return result

    def test_primary_unchanged_and_additional_preserved(self):
        result = self.analyze([EXTRA, PRIMARY], selected=2)
        self.assertEqual(result["evidence"], [PRIMARY])
        self.assertEqual(result["additional_evidence"], [EXTRA])

    def test_duplicate_primary_and_duplicate_additional_excluded(self):
        primary_copy = dict(PRIMARY, evidence="الصِّدق من الأخلاق الحميدة التي حث الإسلام عليها", source_name="Dorar.net")
        extra_copy = dict(EXTRA, source_name="Dorar.net")
        result = self.analyze([PRIMARY, primary_copy, EXTRA, extra_copy])
        self.assertEqual(result["evidence"], [PRIMARY])
        self.assertEqual(result["additional_evidence"], [EXTRA])

    def test_unrelated_and_empty_evidence_do_not_create_additional_items(self):
        unrelated = dict(EXTRA, evidence="أحكام البيع والشراء")
        blank = dict(EXTRA, evidence="")
        result = self.analyze([PRIMARY, unrelated, blank])
        self.assertNotIn("additional_evidence", result)

    def test_single_evidence_preserves_original_contract(self):
        result = self.analyze([PRIMARY])
        self.assertEqual(set(result), {"claim", "status", "evidence", "reason", "suggestion"})
        self.assertEqual(result["evidence"], [PRIMARY])

    def test_no_primary_does_not_promote_unassessed_evidence(self):
        result = self.analyze([PRIMARY, EXTRA], selected=None)
        self.assertEqual(result["evidence"], [])
        self.assertNotIn("additional_evidence", result)


if __name__ == "__main__":
    unittest.main()
