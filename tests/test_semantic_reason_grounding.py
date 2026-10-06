import contextlib
import io
import json
import unittest
from unittest.mock import patch

import ai_compare


CLAIM = "تجب الزكاة على المسلم في ماله."
EVIDENCE = "ويقيموا الصلاة ويؤتوا الزكاة"
REASON = "النص يذكر إيتاء الزكاة ضمن الأعمال المطلوبة، لكنه لا يحدد المال الذي تجب فيه."
UNRELATED = "الدليل يتحدث عن حفظ الشعر العربي وتعلم القرآن وتعليمه."


def encoded(value):
    return json.dumps(value, ensure_ascii=False)


def semantic_proof(grounded=True, status_fits=True):
    return encoded({"grounded": grounded, "status_fits": status_fits,
                    "semantic_basis": "المعلومة تتناول وجوب الزكاة في المال؛ النص يذكر إيتاءها ولا يفصل أحكام المال."})


class SemanticReasonGroundingTests(unittest.TestCase):
    def test_faithful_arabic_paraphrase_requires_no_literal_quotes(self):
        with patch("ai_compare.ask_ai", return_value=semantic_proof()) as model, \
             self.assertLogs("ai_compare", level="DEBUG") as logs:
            self.assertTrue(ai_compare._reason_is_grounded(CLAIM, REASON, EVIDENCE))
        self.assertIn("semantic_proof", logs.output[-1])
        prompt = model.call_args.args[0]
        self.assertIn("Faithful paraphrases", prompt)
        self.assertIn("No literal quotes are required", prompt)
        self.assertIn("Reject any concept absent from BOTH texts", prompt)

    def test_status_fit_accepts_semantic_paraphrase_without_lexical_identity(self):
        claim = "المكتبة متاحة للزوار المسجلين."
        evidence = "يمكن للزائر المسجل استخدام المكتبة."
        reason = "النص يسمح للمسجلين بالانتفاع بالمكتبة كما تقول المعلومة."
        for status in ("supported", "needs_review"):
            # Status is supplied by the evaluator; the validator must actually
            # judge fit. This test exercises parsing separately from AI judgment.
            with self.subTest(status=status), patch("ai_compare.ask_ai", return_value=encoded({
                "grounded": True, "status_fits": status == "supported",
                "semantic_basis": "استخدام المكتبة وإتاحتها للمسجلين يعبران عن المعنى نفسه.",
            })), self.assertLogs("ai_compare", level="DEBUG") as logs:
                self.assertEqual(ai_compare._reason_is_grounded(claim, reason, evidence, status),
                                 status == "supported")
            if status == "needs_review":
                self.assertIn("status_does_not_fit", logs.output[-1])

    def test_unrelated_reason_still_rejected_despite_positive_status_fit(self):
        with patch("ai_compare.ask_ai", return_value=semantic_proof(grounded=False)), \
             self.assertLogs("ai_compare", level="WARNING") as logs:
            self.assertFalse(ai_compare._reason_is_grounded(CLAIM, UNRELATED, EVIDENCE, "supported"))
        self.assertIn("reason_not_grounded", logs.output[-1])

    def test_exact_pair_trace_keeps_model_status_when_both_verdicts_pass(self):
        # No prescribed religious verdict: test the guard path with an evaluator
        # result and independent semantic/status verdict supplied by model mocks.
        for status in ("supported", "needs_context", "needs_review"):
            with self.subTest(status=status), patch("ai_compare.ask_ai", side_effect=[
                "YES|1", encoded({"status": status, "reason": REASON, "suggestion": ""}), semantic_proof(),
            ]) as model, patch("ai_compare._propose_revision", return_value=""), \
                 contextlib.redirect_stdout(io.StringIO()) as trace, self.assertLogs("ai_compare", level="DEBUG") as logs:
                result = ai_compare.compare_claim_with_evidence(CLAIM, [{"evidence": EVIDENCE}])
            self.assertEqual(result["status"], status)
            self.assertEqual(result["reason"], REASON)
            self.assertEqual(result["suggestion"], "")
            self.assertEqual(model.call_count, 3)
            self.assertIn(REASON, trace.getvalue())  # Raw Stage 2 result is traced.
            self.assertTrue(any("Stage 2 parsed status" in line for line in logs.output))
            self.assertTrue(any("semantic_proof" in line for line in logs.output))

    def test_grounded_arabic_rewrite_reaches_semantic_guard(self):
        with patch("ai_compare.ask_ai", side_effect=[
            "YES|1", encoded({"status": "needs_review", "reason": "The text mentions zakat but does not detail wealth conditions.", "suggestion": ""}),
            encoded({"reason": REASON}), semantic_proof(),
        ]) as model, contextlib.redirect_stdout(io.StringIO()), self.assertLogs("ai_compare", level="DEBUG") as logs:
            result = ai_compare.compare_claim_with_evidence(CLAIM, [{"evidence": EVIDENCE}])
        self.assertEqual(result["reason"], REASON)
        self.assertIn(REASON, model.call_args_list[-1].args[0])
        self.assertTrue(any("Arabic rewrite accepted: reason" in line for line in logs.output))

    def test_genuinely_ungrounded_evaluation_and_retry_still_fall_back(self):
        bad = encoded({"status": "supported", "reason": UNRELATED, "suggestion": ""})
        with patch("ai_compare.ask_ai", side_effect=[
            "YES|1", bad, semantic_proof(grounded=False), bad, semantic_proof(grounded=False),
        ]), contextlib.redirect_stdout(io.StringIO()), self.assertLogs("ai_compare", level="WARNING") as logs:
            result = ai_compare.compare_claim_with_evidence(CLAIM, [{"evidence": EVIDENCE}])
        self.assertEqual(result["status"], "needs_review")
        self.assertIn("تعذر التحقق", result["reason"])
        self.assertNotIn("الشعر", result["reason"])
        self.assertEqual(result["suggestion"], "")
        self.assertEqual(sum("reason_not_grounded" in line for line in logs.output), 2)
        self.assertIn("final fallback", logs.output[-1])

    def test_invalid_semantic_proofs_and_nonboolean_flags_fail_closed(self):
        invalid = [
            {"grounded": True, "status_fits": True},
            {"grounded": True, "status_fits": True, "semantic_basis": " "},
            {"grounded": "true", "status_fits": True, "semantic_basis": "meaning"},
            {"grounded": True, "status_fits": "true", "semantic_basis": "meaning"},
            {"grounded": True, "semantic_basis": "meaning"},
        ]
        for proof in invalid:
            with self.subTest(proof=proof), patch("ai_compare.ask_ai", return_value=encoded(proof)), \
                 self.assertLogs("ai_compare", level="WARNING"):
                self.assertFalse(ai_compare._reason_is_grounded(CLAIM, REASON, EVIDENCE, "supported"))

    def test_semantic_proof_does_not_bypass_partial_component_validation(self):
        with patch("ai_compare.ask_ai", return_value=semantic_proof()), \
             self.assertLogs("ai_compare", level="WARNING") as logs:
            self.assertFalse(ai_compare._reason_is_grounded(CLAIM, REASON, EVIDENCE, "partially_supported"))
        self.assertIn("invalid_partial_components", logs.output[-1])

    def test_unlocalized_reason_rejected_before_semantic_verifier(self):
        with patch("ai_compare.ask_ai") as model, self.assertLogs("ai_compare", level="WARNING") as logs:
            self.assertFalse(ai_compare._reason_is_grounded(CLAIM, "The text mentions zakat.", EVIDENCE))
        model.assert_not_called()
        self.assertIn("arabic_reason_invalid", logs.output[-1])


if __name__ == "__main__":
    unittest.main()
