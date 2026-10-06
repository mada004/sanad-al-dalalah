import contextlib
import io
import json
import unittest
from unittest.mock import patch

import requests

import ai_compare


SUPPORTED = ("المكتبة متاحة للزوار المسجلين فقط.", "المكتبة متاحة للزوار المسجلين فقط.",
             "supported", "الدليل يشترط التسجيل كما تذكر المعلومة.", "")
PARTIAL = ("المكتبة متاحة للزوار المسجلين، والدخول مجاني.", "المكتبة متاحة للزوار المسجلين.",
           "partially_supported", "الدليل يثبت إتاحة المكتبة للزوار المسجلين، لكنه لا يثبت مجانية الدخول.",
           "المكتبة متاحة للزوار المسجلين.")
CONTEXT = ("المكتبة متاحة للزوار.", "المكتبة متاحة للزوار المسجلين فقط.",
           "needs_context", "المعلومة تغفل شرط التسجيل الذي يورده الدليل لإتاحة المكتبة.",
           "المكتبة متاحة للزوار المسجلين فقط.")
REVIEW = ("المكتبة مفتوحة يوم السبت.", "المكتبة مغلقة يوم السبت.",
          "needs_review", "المعلومة تقول إن المكتبة مفتوحة يوم السبت، بينما ينص الدليل على أنها مغلقة.", "")
INSUFFICIENT = ("المكتبة متاحة للزوار المسجلين.", "المكتبة تضم قاعة للقراءة.",
                "needs_review", "الدليل يذكر قاعة القراءة، ولا يثبت إتاحة المكتبة للزوار المسجلين.", "")


def encoded(value):
    return json.dumps(value, ensure_ascii=False)


def proof(claim, evidence):
    validation = {"grounded": True, "claim_quote": claim, "evidence_quote": evidence}
    if claim == PARTIAL[0]:
        validation["partial_support"] = {
            "independent_assertions": True, "supported_assertion_entailed": True,
            "other_assertion_unsupported": True,
            "supported_component": "المكتبة متاحة للزوار المسجلين",
            "unsupported_component": "الدخول مجاني",
        }
    return encoded(validation)


def revision_proof(evidence):
    return encoded({"grounded": True, "evidence_quote": evidence})


class Stage2QualityTests(unittest.TestCase):
    def evaluate(self, case, responses=None):
        claim, evidence, status, reason, suggestion = case
        if responses is None:
            responses = ["YES|1", encoded({"status": status, "reason": reason, "suggestion": suggestion}),
                         proof(claim, evidence)]
            if suggestion:
                responses.append(revision_proof(evidence))
        item = {"evidence": evidence, "source_name": "reference", "source_location": "location"}
        with patch("ai_compare.ask_ai", side_effect=responses) as model, contextlib.redirect_stdout(io.StringIO()):
            result = ai_compare.compare_claim_with_evidence(claim, [item])
        self.assertEqual(item["evidence"], evidence)
        return result, model

    def test_supported_vs_independently_unsupported_additional_component(self):
        supported, _ = self.evaluate(SUPPORTED)
        partial, model = self.evaluate(PARTIAL)
        self.assertEqual(supported["status"], "supported")
        self.assertEqual(supported["suggestion"], "")
        self.assertEqual(partial["status"], "partially_supported")
        self.assertEqual(partial["suggestion"], PARTIAL[4])
        self.assertIn(ai_compare.STAGE2_STATUS_RULES, model.call_args_list[1].args[0])

    def test_independent_component_vs_missing_qualification_of_same_core(self):
        partial, _ = self.evaluate(PARTIAL)
        context, model = self.evaluate(CONTEXT)
        self.assertEqual(partial["status"], "partially_supported")
        self.assertEqual(context["status"], "needs_context")
        self.assertEqual(context["suggestion"], CONTEXT[4])
        prompt = model.call_args_list[1].args[0]
        self.assertIn("قبل استخدام partially_supported", prompt)
        self.assertIn("التأهيل الناقص يقتضي needs_context", prompt)

    def test_missing_context_vs_conflicting_core_fact(self):
        context, _ = self.evaluate(CONTEXT)
        review, model = self.evaluate(REVIEW)
        self.assertEqual(context["status"], "needs_context")
        self.assertEqual(review["status"], "needs_review")
        self.assertEqual(review["suggestion"], "")
        self.assertIn("تغيير الحقيقة ليس إضافة سياق", model.call_args_list[1].args[0])

    def test_false_core_labeled_as_context_is_rejected_by_status_grounding(self):
        claim, evidence, _, reason, suggestion = REVIEW
        result, model = self.evaluate(REVIEW, [
            "YES|1", encoded({"status": "needs_context", "reason": "تحتاج المكتبة إلى سياق إضافي.", "suggestion": ""}),
            '{"grounded": false}', encoded({"status": "needs_review", "reason": reason, "suggestion": suggestion}),
            proof(claim, evidence),
        ])
        self.assertEqual(result["status"], "needs_review")
        self.assertEqual(result["reason"], reason)
        self.assertEqual(result["suggestion"], "")
        self.assertIn('Chosen status: "needs_context"', model.call_args_list[2].args[0])
        self.assertIn("a false core fact or", model.call_args_list[2].args[0])
        self.assertIn(ai_compare.STAGE2_STATUS_RULES, model.call_args_list[2].args[0])

    def test_insufficient_evidence_cannot_fabricate_revision(self):
        result, model = self.evaluate(INSUFFICIENT)
        self.assertEqual(result["status"], "needs_review")
        self.assertEqual(result["suggestion"], "")
        self.assertEqual(model.call_count, 3)

    def test_arabic_claim_english_reason_is_rewritten_then_grounded(self):
        claim, evidence, status, reason, suggestion = CONTEXT
        result, model = self.evaluate(CONTEXT, [
            "YES|1", encoded({"status": status, "reason": "The evidence requires registration.", "suggestion": suggestion}),
            encoded({"reason": reason}), proof(claim, evidence), revision_proof(evidence),
        ])
        self.assertEqual(result["status"], status)
        self.assertEqual(result["reason"], reason)
        self.assertTrue(ai_compare._is_arabic_output(result["reason"], claim, evidence))
        self.assertIn("Rewrite ONLY", model.call_args_list[2].args[0])
        self.assertIn(reason, model.call_args_list[3].args[0])

    def test_english_suggestion_becomes_arabic_and_is_revalidated(self):
        claim, evidence, status, reason, suggestion = PARTIAL
        result, model = self.evaluate(PARTIAL, [
            "YES|1", encoded({"status": status, "reason": reason, "suggestion": "The library is available to registered visitors."}),
            proof(claim, evidence), encoded({"suggestion": suggestion}), revision_proof(evidence),
        ])
        self.assertEqual(result["suggestion"], suggestion)
        self.assertTrue(ai_compare._is_arabic_output(result["suggestion"], claim, evidence))
        self.assertIn(suggestion, model.call_args_list[-1].args[0])

    def test_generated_revision_also_passes_arabic_enforcement(self):
        claim, evidence, status, reason, suggestion = CONTEXT
        result, _ = self.evaluate(CONTEXT, [
            "YES|1", encoded({"status": status, "reason": reason, "suggestion": ""}), proof(claim, evidence),
            encoded({"suggestion": "The library is available only to registered visitors."}),
            encoded({"suggestion": suggestion}), revision_proof(evidence),
        ])
        self.assertEqual(result["status"], "needs_context")
        self.assertEqual(result["suggestion"], suggestion)

    def test_failed_arabic_rewrite_never_leaks_english_reason(self):
        with patch("ai_compare.ask_ai", side_effect=[
            "YES|1", encoded({"status": "supported", "reason": "This statement is supported.", "suggestion": ""}),
            requests.Timeout(),
        ]), patch("ai_compare._repair_evaluation", return_value=None), contextlib.redirect_stdout(io.StringIO()):
            result = ai_compare.compare_claim_with_evidence(SUPPORTED[0], [{"evidence": SUPPORTED[1]}])
        self.assertEqual(result["status"], "needs_review")
        self.assertTrue(ai_compare._is_arabic_output(result["reason"], SUPPORTED[0], SUPPORTED[1]))
        self.assertEqual(result["suggestion"], "")

    def test_arabic_rewrite_cannot_bypass_grounding(self):
        claim, evidence, status, _, suggestion = PARTIAL
        result, _ = self.evaluate(PARTIAL, [
            "YES|1", encoded({"status": status, "reason": PARTIAL[3], "suggestion": "Admission is free."}),
            proof(claim, evidence), encoded({"suggestion": "الدخول مجاني للجميع."}),
            '{"grounded": false}', '{"suggestion": ""}',
        ])
        self.assertEqual(result["status"], status)
        self.assertEqual(result["suggestion"], "")

    def test_grounding_guards_reject_unlocalized_fields_before_model_call(self):
        with patch("ai_compare.ask_ai") as model:
            self.assertFalse(ai_compare._reason_is_grounded(CONTEXT[0], "The evidence adds a condition.", CONTEXT[1]))
            self.assertFalse(ai_compare._correction_is_grounded(CONTEXT[0], "Registered visitors only.", CONTEXT[1], "needs_context"))
        model.assert_not_called()

    def test_actual_citations_and_names_do_not_translate_evidence(self):
        evidence = 'المكتبة المسماة ReadingRoom متاحة. The library is available.'
        self.assertTrue(ai_compare._is_arabic_output('الدليل يذكر ReadingRoom.', CONTEXT[0], evidence))
        self.assertTrue(ai_compare._is_arabic_output('النص يقول «The library is available.»', CONTEXT[0], evidence))
        self.assertFalse(ai_compare._is_arabic_output('The library is available.', CONTEXT[0], evidence))
        self.assertFalse(ai_compare._is_arabic_output('الدليل says the library is available.', CONTEXT[0], evidence))
        self.assertFalse(ai_compare._is_arabic_output('الدليل The Library Is Available.', CONTEXT[0], 'The Library Is Available.'))
        with patch("ai_compare.ask_ai") as model:
            self.assertEqual(ai_compare._arabic_field(CONTEXT[0], evidence, 'الدليل يذكر ReadingRoom.', "reason"), 'الدليل يذكر ReadingRoom.')
        model.assert_not_called()

    def test_repair_uses_same_status_rules_and_localizes_reason(self):
        claim, evidence, status, reason, suggestion = CONTEXT
        with patch("ai_compare.ask_ai", side_effect=[
            encoded({"status": status, "reason": "Registration is required.", "suggestion": suggestion}),
            encoded({"reason": reason}), proof(claim, evidence),
        ]) as model:
            repaired = ai_compare._repair_evaluation(claim, evidence)
        self.assertEqual(repaired["status"], "needs_context")
        self.assertEqual(repaired["reason"], reason)
        self.assertIn(ai_compare.STAGE2_STATUS_RULES, model.call_args_list[0].args[0])

    def test_non_arabic_input_is_not_forced_through_arabic_translation(self):
        case = ("The library is open.", "The library is open.", "supported", "The evidence states the same fact.", "")
        result, model = self.evaluate(case)
        self.assertEqual(result["reason"], case[3])
        self.assertEqual(model.call_count, 3)


if __name__ == "__main__":
    unittest.main()
