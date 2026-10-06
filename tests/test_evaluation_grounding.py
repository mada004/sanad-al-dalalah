import contextlib
import io
import json
import unittest
from unittest.mock import patch

import requests

import ai_compare
import main


CLAIM = "الصدق من الأخلاق المهمة في الإسلام، وهو وحده كافٍ لدخول الجنة."
EVIDENCE = "1– الصدق من الأخلاق الحميدة التي حث الإسلام عليها."
REASON = "الدليل يؤيد الحث على الصدق، لكنه لا يثبت أن الصدق وحده كاف لدخول الجنة."
REVISION = "الصدق من الأخلاق الحميدة التي حث الإسلام عليها."
STALE_REASON = "الدليل يتحدث عن تعلم القرآن وتعليمه ولكن الادعاء يشير إلى حفظ الشعر العربي."


def encoded(value):
    return json.dumps(value, ensure_ascii=False)


def reason_validation(claim=CLAIM, evidence=EVIDENCE):
    validation = {"grounded": True, "claim_quote": claim, "evidence_quote": evidence}
    if claim == CLAIM:
        validation["partial_support"] = {
            "independent_assertions": True, "supported_assertion_entailed": True,
            "other_assertion_unsupported": True,
            "supported_component": "الصدق من الأخلاق المهمة في الإسلام",
            "unsupported_component": "هو وحده كافٍ لدخول الجنة",
        }
    return encoded(validation)


def revision_validation(evidence=EVIDENCE):
    return encoded({"grounded": True, "evidence_quote": evidence})


class EvaluationGroundingTests(unittest.TestCase):
    def compare(self, responses):
        with patch("ai_compare.ask_ai", side_effect=responses) as model, contextlib.redirect_stdout(io.StringIO()):
            result = ai_compare.compare_claim_with_evidence(CLAIM, [{
                "evidence": EVIDENCE, "source_name": "reference", "source_location": "location",
            }])
        return result, model

    def test_unrelated_reason_rejected_and_missing_partial_revision_generated(self):
        result, model = self.compare([
            "YES|1", encoded({"status": "partially_supported", "reason": STALE_REASON, "suggestion": ""}),
            '{"grounded": false}', encoded({"status": "partially_supported", "reason": REASON, "suggestion": ""}),
            reason_validation(), encoded({"suggestion": REVISION}), revision_validation(),
        ])
        self.assertNotIn("القرآن", result["reason"])
        self.assertNotIn("الشعر", result["reason"])
        self.assertEqual(result["reason"], REASON)
        self.assertEqual(result["status"], "partially_supported")
        self.assertEqual(result["suggestion"], REVISION)
        # The evaluator receives only the current pair, not illustrative cases.
        prompt = model.call_args_list[1].args[0]
        self.assertIn(CLAIM, prompt)
        self.assertIn(EVIDENCE, prompt)
        self.assertNotIn("الشعر", prompt)
        self.assertNotIn("القرآن", prompt)

    def test_rejected_explanation_retried_once_with_current_pair_only(self):
        result, model = self.compare([
            "YES|1", encoded({"status": "needs_review", "reason": STALE_REASON, "suggestion": ""}),
            '{"grounded": false}', encoded({"status": "partially_supported", "reason": REASON, "suggestion": REVISION}),
            reason_validation(), revision_validation(),
        ])
        self.assertEqual(result["status"], "partially_supported")
        self.assertEqual(result["reason"], REASON)
        self.assertEqual(result["suggestion"], REVISION)
        retry_prompt = model.call_args_list[3].args[0]
        self.assertIn(CLAIM, retry_prompt)
        self.assertIn(EVIDENCE, retry_prompt)
        self.assertNotIn(STALE_REASON, retry_prompt)

    def test_failed_retry_cannot_return_second_unrelated_reason(self):
        result, model = self.compare([
            "YES|1", encoded({"status": "supported", "reason": STALE_REASON, "suggestion": REVISION}),
            '{"grounded": false}', encoded({"status": "needs_review", "reason": STALE_REASON, "suggestion": ""}),
            '{"grounded": false}',
        ])
        self.assertNotIn("القرآن", result["reason"])
        self.assertNotIn("الشعر", result["reason"])
        self.assertEqual(result["status"], "needs_review")
        self.assertEqual(result["suggestion"], "")
        self.assertEqual(model.call_count, 5)

    def test_partial_revision_can_remove_unproven_clause_without_contradiction(self):
        result, model = self.compare([
            "YES|1", encoded({"status": "partially_supported", "reason": REASON, "suggestion": REVISION}),
            reason_validation(), revision_validation(),
        ])
        self.assertEqual(result["reason"], REASON)
        self.assertEqual(result["suggestion"], REVISION)
        self.assertEqual(result["status"], "partially_supported")
        self.assertIn("لا يشترط أن يناقض", model.call_args_list[-1].args[0])

    def test_unsupported_revision_rejected_without_changing_partial_status(self):
        result, _ = self.compare([
            "YES|1", encoded({"status": "partially_supported", "reason": REASON, "suggestion": CLAIM}),
            reason_validation(), '{"grounded": false}', '{"suggestion": ""}',
        ])
        self.assertEqual(result["suggestion"], "")
        self.assertEqual(result["status"], "partially_supported")

    def test_rejected_revision_can_be_replaced_only_by_validated_safe_revision(self):
        result, _ = self.compare([
            "YES|1", encoded({"status": "partially_supported", "reason": REASON, "suggestion": CLAIM}),
            reason_validation(), '{"grounded": false}', encoded({"suggestion": REVISION}), revision_validation(),
        ])
        self.assertNotEqual(result["suggestion"], CLAIM)
        self.assertEqual(result["suggestion"], REVISION)

    def test_needs_context_revision_uses_only_explicit_evidence_qualification(self):
        claim = "الخدمة متاحة للجميع"
        evidence = "الخدمة متاحة للمستخدم المسجل فقط"
        reason = "الدليل يقيد إتاحة الخدمة بالتسجيل، بينما الادعاء يعمم الإتاحة على الجميع."
        with patch("ai_compare.ask_ai", side_effect=[
            "YES|1", encoded({"status": "needs_context", "reason": reason, "suggestion": evidence}),
            reason_validation(claim, evidence), revision_validation(evidence),
        ]), contextlib.redirect_stdout(io.StringIO()):
            result = ai_compare.compare_claim_with_evidence(claim, [{"evidence": evidence}])
        self.assertEqual(result["status"], "needs_context")
        self.assertEqual(result["suggestion"], evidence)

    def test_no_safe_revision_leaves_suggestion_empty(self):
        result, _ = self.compare([
            "YES|1", encoded({"status": "needs_context", "reason": REASON, "suggestion": ""}),
            reason_validation(), '{"suggestion": ""}',
        ])
        self.assertEqual(result["suggestion"], "")
        self.assertEqual(result["status"], "needs_context")

    def test_reason_validation_fails_closed_on_invalid_proofs_or_service_failure(self):
        for response in ["not JSON", "[]", '{"grounded": true}',
                         encoded({"grounded": "true", "claim_quote": CLAIM, "evidence_quote": EVIDENCE}),
                         encoded({"grounded": True, "claim_quote": "unrelated", "evidence_quote": EVIDENCE}),
                         encoded({"grounded": True, "claim_quote": CLAIM, "evidence_quote": "other evidence"})]:
            with self.subTest(response=response), patch("ai_compare.ask_ai", return_value=response):
                self.assertFalse(ai_compare._reason_is_grounded(CLAIM, REASON, EVIDENCE))
        with patch("ai_compare.ask_ai", side_effect=requests.Timeout()):
            self.assertFalse(ai_compare._reason_is_grounded(CLAIM, REASON, EVIDENCE))

    def test_revision_validation_requires_literal_selected_evidence_quote(self):
        with patch("ai_compare.ask_ai", return_value=revision_validation("unselected reference")):
            self.assertFalse(ai_compare._correction_is_grounded(CLAIM, REVISION, EVIDENCE, "partially_supported"))

    def test_revision_generation_failure_keeps_empty_suggestion(self):
        for response in ["invalid JSON", "[]", '{"suggestion": 1}']:
            with patch("ai_compare.ask_ai", return_value=response):
                self.assertEqual(ai_compare._propose_revision(CLAIM, EVIDENCE), "")
        with patch("ai_compare.ask_ai", side_effect=requests.ConnectionError()):
            self.assertEqual(ai_compare._propose_revision(CLAIM, EVIDENCE), "")

    def test_selected_original_index_grounding_and_api_response_use_same_evidence(self):
        weak = {"evidence": "الصدق في الكلام", "source_name": "HadeethEnc", "source_location": "location"}
        selected = {"evidence": EVIDENCE, "source_name": "central", "source_location": "location"}
        with patch("main.extract_claims", return_value=[CLAIM]), \
             patch("main.search_hadiths", return_value=[weak]), patch("main.search_dorar", return_value=[]), \
             patch("main.search_central_db", return_value=[selected]), \
             patch("ai_compare.ask_ai", side_effect=[
                 "YES|2", encoded({"status": "partially_supported", "reason": REASON, "suggestion": REVISION}),
                 reason_validation(), revision_validation(),
             ]) as model, contextlib.redirect_stdout(io.StringIO()):
            result = main.analyze(main.AnalyzeRequest(text=CLAIM))["claims"][0]
        self.assertEqual(result["evidence"], [selected])
        self.assertEqual(result["reason"], REASON)
        self.assertEqual(result["suggestion"], REVISION)
        self.assertEqual(result["status"], "partially_supported")
        self.assertEqual(result["additional_evidence"], [weak])
        for call in model.call_args_list[1:]:
            self.assertIn(EVIDENCE, call.args[0])
            self.assertNotIn(weak["evidence"], call.args[0])


if __name__ == "__main__":
    unittest.main()
