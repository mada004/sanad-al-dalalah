import contextlib
import io
import json
import unittest
from unittest.mock import patch

import requests

import ai_compare


CLAIM = "أركان الإسلام ٣"
EVIDENCE = "بني الإسلام على خمس: شهادة أن لا إله إلا الله وأن محمدًا رسول الله، وإقام الصلاة، وإيتاء الزكاة، والحج، وصوم رمضان."
SUGGESTION = "أركان الإسلام خمسة."
REASON = "الادعاء يذكر ثلاثة أركان، بينما ينص الدليل على أن الإسلام بني على خمس."


class FactualCorrectionTests(unittest.TestCase):
    def compare(self, claim=CLAIM, evidence=EVIDENCE, suggestion=SUGGESTION,
                validation=None, reason=REASON):
        responses = ["YES|1", json.dumps({
            "status": "needs_review", "reason": reason, "suggestion": suggestion,
        }, ensure_ascii=False)]
        if suggestion:
            responses.append(validation if validation is not None else json.dumps({
                "grounded": True, "evidence_quote": "بني الإسلام على خمس",
            }, ensure_ascii=False))
        with patch("ai_compare.ask_ai", side_effect=responses) as model, contextlib.redirect_stdout(io.StringIO()):
            result = ai_compare.compare_claim_with_evidence(claim, [{
                "evidence": evidence, "source_name": "HadeethEnc", "source_location": "مصدر الحديث",
            }])
        return result, model

    def test_specific_mismatch_and_grounded_correction_retained(self):
        result, model = self.compare()
        self.assertEqual(result, {"best_evidence": 1, "status": "needs_review", "reason": REASON, "suggestion": SUGGESTION})
        self.assertEqual(model.call_count, 3)
        self.assertIn("يناقض", model.call_args_list[0].args[0])
        self.assertIn("التعارض المحدد", model.call_args_list[1].args[0])
        self.assertIn(EVIDENCE, model.call_args_list[2].args[0])

    def test_correction_is_general_not_tied_to_example_or_number(self):
        evidence = "إن عدة الشهور عند الله اثنا عشر شهرا."
        suggestion = "عدد الشهور اثنا عشر."
        validation = json.dumps({"grounded": True, "evidence_quote": evidence}, ensure_ascii=False)
        result, _ = self.compare("عدد الشهور أحد عشر", evidence, suggestion, validation, "النص يذكر اثني عشر لا أحد عشر.")
        self.assertEqual(result["suggestion"], suggestion)
        self.assertEqual(result["status"], "needs_review")

    def test_ambiguous_evidence_cannot_supply_a_correction(self):
        result, _ = self.compare(evidence="الإسلام يحث على الأخلاق الحسنة.", validation='{"grounded": false, "evidence_quote": ""}')
        self.assertEqual(result["status"], "needs_review")
        self.assertEqual(result["suggestion"], "")

    def test_fabricated_quote_or_invalid_validator_output_clears_suggestion(self):
        for validation in [
            '{"grounded": true, "evidence_quote": "quote not present"}',
            '{"grounded": true, "evidence_quote": ""}',
            '{"grounded": "true", "evidence_quote": "بني الإسلام على خمس"}',
            "not JSON", "[]",
        ]:
            with self.subTest(validation=validation):
                result, _ = self.compare(validation=validation)
                self.assertEqual(result["suggestion"], "")

    def test_validator_failure_fails_closed(self):
        with patch("ai_compare.ask_ai", side_effect=requests.Timeout()):
            self.assertFalse(ai_compare._correction_is_grounded(CLAIM, SUGGESTION, EVIDENCE))

    def test_no_suggestion_adds_no_validation_call(self):
        result, model = self.compare(suggestion="")
        self.assertEqual(result["suggestion"], "")
        self.assertEqual(model.call_count, 2)

    def test_no_relevant_evidence_does_not_invent_a_correction(self):
        with patch("ai_compare.ask_ai", return_value="NO"), contextlib.redirect_stdout(io.StringIO()):
            result = ai_compare.compare_claim_with_evidence(CLAIM, [])
        self.assertIsNone(result["best_evidence"])
        self.assertEqual(result["status"], "needs_review")
        self.assertEqual(result["suggestion"], "")


if __name__ == "__main__":
    unittest.main()
