import contextlib
import io
import json
import unittest
from unittest.mock import patch

import ai_compare
import main


CLAIM = "المكتبة تفتح يوم الجمعة، والدخول إليها مجاني للجميع."
PARTIAL = "المكتبة تفتح يوم الجمعة."


class Stage1RelevanceTests(unittest.TestCase):
    def evaluate(self, claim, evidence, status, reason, suggestion):
        responses = ["YES|1", json.dumps({"status": status, "reason": reason, "suggestion": suggestion}),
                     json.dumps({"grounded": True, "claim_quote": claim, "evidence_quote": evidence})]
        if suggestion:
            responses.append(json.dumps({"grounded": True, "evidence_quote": evidence}))
        with patch("ai_compare.ask_ai", side_effect=responses) as model, contextlib.redirect_stdout(io.StringIO()):
            result = ai_compare.compare_claim_with_evidence(claim, [{
                "evidence": evidence, "source_name": "reference", "source_location": "location",
            }])
        return result, model

    def test_one_substantive_clause_is_enough_to_reach_partial_evaluation(self):
        reason = "الدليل يثبت فتح المكتبة يوم الجمعة، لكنه لا يثبت مجانية الدخول للجميع."
        result, model = self.evaluate(CLAIM, PARTIAL, "partially_supported", reason, PARTIAL)
        stage1 = model.call_args_list[0].args[0]
        self.assertIn("ANY substantive part", stage1)
        self.assertIn("Do NOT require full entailment", stage1)
        self.assertIn("Stage 2 alone decides", stage1)
        self.assertIn("must NOT reject a candidate", stage1)
        self.assertIn(CLAIM, stage1)
        self.assertIn(PARTIAL, stage1)
        self.assertIn(CLAIM, model.call_args_list[1].args[0])
        self.assertIn(PARTIAL, model.call_args_list[1].args[0])
        self.assertEqual(result["best_evidence"], 1)
        self.assertEqual(result["status"], "partially_supported")
        self.assertEqual(result["reason"], reason)
        self.assertEqual(result["suggestion"], PARTIAL)
        # Stage 2 and both grounding validators still execute.
        self.assertEqual(model.call_count, 4)

    def test_context_dependent_evidence_reaches_context_evaluation(self):
        claim = "المكتبة متاحة للزوار"
        evidence = "المكتبة متاحة للزوار المسجلين فقط"
        result, model = self.evaluate(claim, evidence, "needs_context", "إتاحة المكتبة مقيدة بالتسجيل في الدليل.", evidence)
        self.assertIn("qualifies, contextualizes", model.call_args_list[0].args[0])
        self.assertEqual(result["best_evidence"], 1)
        self.assertEqual(result["status"], "needs_context")
        self.assertEqual(result["suggestion"], evidence)
        self.assertEqual(model.call_count, 4)

    def test_completely_unrelated_evidence_rejected_before_stage2(self):
        with patch("ai_compare.ask_ai", return_value="NO") as model, \
             patch("ai_compare._reason_is_grounded") as reason_validator, \
             patch("ai_compare._correction_is_grounded") as revision_validator, \
             contextlib.redirect_stdout(io.StringIO()):
            result = ai_compare.compare_claim_with_evidence(CLAIM, [{"evidence": "السنة اثنا عشر شهرًا"}])
        model.assert_called_once()
        reason_validator.assert_not_called()
        revision_validator.assert_not_called()
        self.assertEqual(result["status"], "needs_review")
        self.assertIsNone(result["best_evidence"])
        self.assertEqual(result["suggestion"], "")

    def test_relevance_does_not_force_a_positive_stage2_status(self):
        result, _ = self.evaluate(CLAIM, "المكتبة منشأة عامة", "needs_review", "الدليل لا يذكر موعد فتح المكتبة أو رسوم الدخول.", "")
        self.assertEqual(result["best_evidence"], 1)
        self.assertEqual(result["status"], "needs_review")
        self.assertEqual(result["suggestion"], "")

    def test_literal_clause_and_context_are_not_rejected_as_full_entailment_failures(self):
        for claim, evidence, status in [
            (CLAIM, PARTIAL, "partially_supported"),
            ("المكتبة متاحة للزوار", "المكتبة متاحة للزوار المسجلين فقط", "needs_context"),
        ]:
            with self.subTest(status=status), patch("ai_compare.ask_ai", side_effect=[
                "NO", json.dumps({"status": status, "reason": "تقييم مبني على النصين", "suggestion": evidence}),
                json.dumps({"grounded": True, "claim_quote": claim, "evidence_quote": evidence}),
                json.dumps({"grounded": True, "evidence_quote": evidence}),
            ]) as model, contextlib.redirect_stdout(io.StringIO()):
                result = ai_compare.compare_claim_with_evidence(claim, [{"evidence": evidence}])
            self.assertEqual(result["best_evidence"], 1)
            self.assertEqual(result["status"], status)
            self.assertEqual(model.call_count, 4)

    def test_keyword_overlap_without_literal_clause_does_not_override_no(self):
        with patch("ai_compare.ask_ai", return_value="NO") as model, contextlib.redirect_stdout(io.StringIO()):
            result = ai_compare.compare_claim_with_evidence(CLAIM, [{"evidence": "المكتبة مغلقة يوم السبت"}])
        model.assert_called_once()
        self.assertIsNone(result["best_evidence"])

    def test_literal_anchor_keeps_existing_order_and_original_index(self):
        candidates = [{"evidence": "المكتبة مغلقة يوم السبت"}, {"evidence": PARTIAL}]
        ranked = ai_compare.prioritize_evidence(CLAIM, candidates)
        self.assertEqual(ai_compare._literal_clause_candidate(CLAIM, ranked), 2)
        self.assertIsNone(ai_compare._literal_clause_candidate("سعة المكتبة 30 مقعدًا", [
            {"original_index": 1, "evidence": {"evidence": "سعة المكتبة 300 مقعدًا"}},
        ]))

    def test_no_evidence_returns_safe_result_without_model_call(self):
        with patch("ai_compare.ask_ai") as model, contextlib.redirect_stdout(io.StringIO()):
            result = ai_compare.compare_claim_with_evidence(CLAIM, [])
        model.assert_not_called()
        self.assertIsNone(result["best_evidence"])
        self.assertEqual(result["status"], "needs_review")
        self.assertEqual(result["suggestion"], "")
        with patch("main.extract_claims", return_value=[CLAIM]), \
             patch("main.search_hadiths", return_value=[]), patch("main.search_dorar", return_value=[]), \
             patch("main.search_central_db", return_value=[]), patch("main.compare_claim_with_evidence") as compare:
            response = main.analyze(main.AnalyzeRequest(text=CLAIM))["claims"][0]
        compare.assert_not_called()
        self.assertEqual(response["status"], "needs_review")
        self.assertEqual(response["evidence"], [])

    def test_invalid_selected_index_does_not_pass_to_stage2(self):
        with patch("ai_compare.ask_ai", return_value="YES|99") as model, contextlib.redirect_stdout(io.StringIO()):
            result = ai_compare.compare_claim_with_evidence(CLAIM, [{"evidence": PARTIAL}])
        model.assert_called_once()
        self.assertIsNone(result["best_evidence"])
        self.assertEqual(result["status"], "needs_review")


if __name__ == "__main__":
    unittest.main()
