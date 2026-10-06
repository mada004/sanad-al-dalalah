import json
import unittest
from unittest.mock import patch

from claim_extraction import extract_claims, _candidate_statements
import main


class ClaimExtractionTests(unittest.TestCase):
    def extract(self, text, selected):
        with patch("claim_extraction.ask_ai", return_value=json.dumps({"claims": selected})):
            return extract_claims(text)

    def test_empty_and_punctuation_artifacts_skip_model(self):
        with patch("claim_extraction.ask_ai") as model:
            for text in ["", " \n\t ", "؟! ... ،", "***", "و", "و و و", "اَ", "٣", "123", "___"]:
                self.assertEqual(extract_claims(text), [])
        model.assert_not_called()

    def test_nonassertions_return_zero_and_skip_retrieval(self):
        for text in ["كيف حالك", "مرحبا، كيف حالك؟", "مرحبا", "هل الصلاة واجبة؟", "الصدق"]:
            with self.subTest(text=text), patch("claim_extraction.ask_ai", return_value='{"claims": []}'), \
                 patch("main.search_hadiths") as hadeeth, patch("main.search_dorar") as dorar, \
                 patch("main.search_central_db") as central:
                request = main.AnalyzeRequest(text=text)
                self.assertEqual(main.analyze(request), {"claims": []})
                self.assertEqual(request.text, text)
                for source in [hadeeth, dorar, central]:
                    source.assert_not_called()

    def test_short_assertions_reach_retrieval_and_comparison(self):
        evidence = {"evidence": "بني الإسلام على خمس.", "source_name": "HadeethEnc", "source_location": "location"}
        for text in ["أركان الإسلام 3", "أركان الإسلام ٣", "أركان الإسلام خمسة", "الصدق من الأخلاق التي حث عليها الإسلام"]:
            with self.subTest(text=text), patch("claim_extraction.ask_ai", return_value=json.dumps({"claims": [text]})), \
                 patch("main.search_hadiths", return_value=[evidence]) as hadeeth, \
                 patch("main.search_dorar", return_value=[]) as dorar, \
                 patch("main.search_central_db", return_value=[]) as central, \
                 patch("main.compare_claim_with_evidence", return_value={
                     "best_evidence": 1, "status": "needs_review", "reason": "reason", "suggestion": "",
                 }) as compare:
                result = main.analyze(main.AnalyzeRequest(text=text))
                hadeeth.assert_called_once_with(text, top_k=3)
                dorar.assert_called_once_with(text)
                central.assert_called_once_with(text, top_k=5)
                compare.assert_called_once_with(text, [evidence])
                self.assertEqual(result["claims"][0]["claim"], text)

    def test_greeting_and_assertion_preserve_original_only_review_assertion(self):
        assertion = "الصدق من الأخلاق التي حث عليها الإسلام"
        text = "مرحبا، كيف حالك؟ " + assertion + "."
        with patch("claim_extraction.ask_ai", return_value=json.dumps({"claims": [assertion]})), \
             patch("main.search_hadiths", return_value=[]) as hadeeth, \
             patch("main.search_dorar", return_value=[]), patch("main.search_central_db", return_value=[]):
            request = main.AnalyzeRequest(text=text)
            result = main.analyze(request)
        hadeeth.assert_called_once_with(assertion, top_k=3)
        self.assertEqual(request.text, text)
        self.assertEqual([c["claim"] for c in result["claims"]], [assertion])

    def test_unsupported_factual_assertion_remains_review_item(self):
        text = "عدد المساجد في هذه المدينة 12345"
        with patch("claim_extraction.ask_ai", return_value=json.dumps({"claims": [text]})), \
             patch("main.search_hadiths", return_value=[]) as hadeeth, \
             patch("main.search_dorar", return_value=[]) as dorar, \
             patch("main.search_central_db", return_value=[]) as central:
            result = main.analyze(main.AnalyzeRequest(text=text))
        for source in [hadeeth, dorar, central]:
            self.assertEqual(source.call_count, 1)
        self.assertEqual(result, {"claims": [{
            "claim": text, "status": "needs_review", "evidence": [],
            "reason": "لم يتم العثور على دليل مناسب للمقارنة.", "suggestion": "",
        }]})

    def test_literal_spans_order_deduplication_and_no_invention(self):
        first, second = "أركان الإسلام 3", "الصلاة واجبة"
        self.assertEqual(self.extract(first + ". " + second, [second, first, first, "أركان الإسلام خمسة", "ركان"]), [first, second])

    def test_no_comma_conjunction_decimal_or_wrapped_line_splitting(self):
        for text in ["إنما الأعمال بالنيات، وإنما لكل امرئ ما نوى.",
                     "د. أحمد يشرح أن نصاب الذهب 85.5 غرامًا.",
                     "الصدق من الأخلاق التي\nحث عليها الإسلام."]:
            self.assertEqual(_candidate_statements(text), [text])
            self.assertEqual(self.extract(text, [text]), [text])

    def test_prompt_does_not_use_evidence_gate(self):
        with patch("claim_extraction.ask_ai", return_value='{"claims": []}') as model:
            extract_claims("كيف حالك")
        prompt = model.call_args.args[0]
        self.assertIn("Do not assess truth or evidence availability", prompt)

    def test_model_failure_not_misrepresented_as_zero_assertions(self):
        for raw in ["not JSON", '{"claims": null}']:
            with patch("claim_extraction.ask_ai", return_value=raw), self.assertRaises(ValueError):
                extract_claims("أركان الإسلام 3")

    def test_json_with_model_explanation_is_accepted(self):
        text = "أركان الإسلام 3"
        raw = "Selected assertions:\n```json\n" + json.dumps({"claims": [text]}) + "\n```\nExplanation"
        with patch("claim_extraction.ask_ai", return_value=raw):
            self.assertEqual(extract_claims(text), [text])

    def test_subjective_or_heading_content_has_no_review_cards(self):
        for text in ["أحب هذا الموضوع", "عنوان الدرس"]:
            self.assertEqual(self.extract(text, []), [])

    def test_retrieved_insufficient_evidence_does_not_delete_assertion(self):
        text = "عدد المساجد في هذه المدينة 12345"
        evidence = {"evidence": "نص مختلف", "source_name": "HadeethEnc", "source_location": "location"}
        with patch("claim_extraction.ask_ai", return_value=json.dumps({"claims": [text]})), \
             patch("main.search_hadiths", return_value=[evidence]), \
             patch("main.search_dorar", return_value=[]), patch("main.search_central_db", return_value=[]), \
             patch("main.compare_claim_with_evidence", return_value={
                 "best_evidence": None, "status": "needs_review", "reason": "insufficient", "suggestion": "",
             }):
            result = main.analyze(main.AnalyzeRequest(text=text))
        self.assertEqual(result["claims"][0]["claim"], text)
        self.assertEqual(result["claims"][0]["status"], "needs_review")


if __name__ == "__main__":
    unittest.main()
