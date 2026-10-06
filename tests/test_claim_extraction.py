import json
import unittest
from unittest.mock import patch

import requests

from claim_extraction import extract_claims
import main


class ClaimExtractionTests(unittest.TestCase):
    def extract(self, text, claims):
        with patch("claim_extraction.ask_ai", return_value=json.dumps({"claims": claims}, ensure_ascii=False)):
            return extract_claims(text)

    def test_empty_punctuation_and_single_words_do_not_call_model(self):
        for text in ["", "؟! ... ،", "الصدق", "***"]:
            with self.subTest(text=text), patch("claim_extraction.ask_ai") as model:
                self.assertEqual(extract_claims(text), [])
                model.assert_not_called()

    def test_sentence_preserved_without_comma_or_conjunction_splitting(self):
        statement = "إنما الأعمال بالنيات، وإنما لكل امرئ ما نوى."
        self.assertEqual(self.extract(statement, [statement]), [statement])

    def test_decimal_and_arabic_wording_preserved(self):
        statement = "نصاب الذهب 85.5 غرامًا."
        self.assertEqual(self.extract(statement, [statement]), [statement])

    def test_short_self_contained_statement_is_allowed(self):
        self.assertEqual(self.extract("الصلاة واجبة.", ["الصلاة واجبة."]), ["الصلاة واجبة."])

    def test_semantic_filter_receives_headings_questions_subjective_and_fragments(self):
        statement = "الصدق من الأخلاق التي حث عليها الإسلام."
        text = "الأخلاق الإسلامية\n***\nلأن الإنسان\nهل الصدق مهم؟\nأرى أن هذا الكلام جميل جدًا.\n" + statement
        with patch("claim_extraction.ask_ai", return_value=json.dumps({"claims": [statement]}, ensure_ascii=False)) as model:
            self.assertEqual(extract_claims(text), [statement])
        prompt = model.call_args.args[0]
        for instruction in ["headings", "incomplete fragments", "questions", "personal opinions", "factual statements"]:
            self.assertIn(instruction, prompt)

    def test_unassertive_input_returns_no_claims(self):
        self.assertEqual(self.extract("عنوان جميل\nلماذا؟\nفي هذا الموضوع", []), [])

    def test_invented_words_questions_and_duplicates_rejected(self):
        statement = "الصدق من الأخلاق التي حث عليها الإسلام."
        text = statement + " هل هذا صحيح؟"
        claims = ["معلومة لم ترد في النص", "الصدق", "هل هذا صحيح؟", statement, statement, 7]
        self.assertEqual(self.extract(text, claims), [statement])

    def test_inline_statement_in_natural_conversation_is_retained(self):
        statement = "الصدق من الأخلاق التي حث عليها الإسلام"
        text = "مرحبًا بكم، اليوم نتحدث عن الأخلاق، " + statement + "، ما رأيكم؟"
        self.assertEqual(self.extract(text, [statement]), [statement])

    def test_statement_need_not_follow_a_sentence_boundary(self):
        statement = "الصلاة واجبة"
        self.assertEqual(self.extract("أريد أن أوضح لكم أن " + statement + " وأتمنى أن يكون الشرح مفيدًا", [statement]), [statement])

    def test_partial_words_rejected(self):
        self.assertEqual(self.extract("والصدق من الأخلاق الحميدة", ["الصدق من الأخلاق"]), [])

    def test_full_natural_input_is_passed_intact_to_extraction(self):
        text = "مقدمة\nمرحبًا!\nهل الصلاة واجبة؟\nأحب هذا الموضوع.\nالصلاة واجبة."
        with patch("claim_extraction.ask_ai", return_value='{"claims": []}') as model:
            self.assertEqual(extract_claims(text), [])
        self.assertTrue(model.call_args.args[0].endswith(text))

    def test_analyze_reviews_only_extracted_span_and_preserves_request_text(self):
        statement = "الصلاة واجبة"
        text = "مرحبًا! عنوان الدرس\nأود أن أخبركم أن " + statement + "، ماذا تعلمتم؟"
        request = main.AnalyzeRequest(text=text)
        with patch("claim_extraction.ask_ai", return_value=json.dumps({"claims": [statement]}, ensure_ascii=False)), \
             patch("main.search_hadiths", return_value=[]) as hadeeth, \
             patch("main.search_dorar", return_value=[]) as dorar, \
             patch("main.search_central_db", return_value=[]) as central:
            result = main.analyze(request)
        self.assertEqual(request.text, text)
        self.assertEqual([claim["claim"] for claim in result["claims"]], [statement])
        hadeeth.assert_called_once_with(statement, top_k=3)
        dorar.assert_called_once_with(statement)
        central.assert_called_once_with(statement, top_k=5)

    def test_original_order_and_fenced_json(self):
        first, second = "الصلاة واجبة.", "الصدق خلق محمود."
        with patch("claim_extraction.ask_ai", return_value='```json\n' + json.dumps({"claims": [second, first]}, ensure_ascii=False) + '\n```'):
            self.assertEqual(extract_claims(first + "\n" + second), [first, second])

    def test_extraction_failures_do_not_fabricate_claims(self):
        for response in ["not JSON", '[]', '{"claims": null}']:
            with patch("claim_extraction.ask_ai", return_value=response):
                self.assertEqual(extract_claims("الصلاة واجبة"), [])
        with patch("claim_extraction.ask_ai", side_effect=requests.Timeout()):
            self.assertEqual(extract_claims("الصلاة واجبة"), [])

    def test_no_claims_skips_all_retrieval_and_evaluation(self):
        with patch("main.extract_claims", return_value=[]), \
             patch("main.search_hadiths") as hadeeth, patch("main.search_dorar") as dorar, \
             patch("main.search_central_db") as central, patch("main.compare_claim_with_evidence") as compare:
            self.assertEqual(main.analyze(main.AnalyzeRequest(text="عنوان")), {"claims": []})
        for mock in [hadeeth, dorar, central, compare]:
            mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
