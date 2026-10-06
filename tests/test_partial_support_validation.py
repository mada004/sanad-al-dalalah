import contextlib
import io
import json
import unittest
from unittest.mock import patch

import ai_compare
import main


CLAIM = "والصدق وحده كافٍ لدخول الجنة."
EVIDENCE = "الصدق من الأخلاق الحميدة التي حث الإسلام عليها."


def encoded(value):
    return json.dumps(value, ensure_ascii=False)


def validation(claim, evidence, supported=None, unsupported=None):
    result = {"grounded": True, "claim_quote": claim, "evidence_quote": evidence}
    if supported is not None:
        result["partial_support"] = {
            "independent_assertions": True,
            "supported_assertion_entailed": True,
            "other_assertion_unsupported": True,
            "supported_component": supported,
            "unsupported_component": unsupported,
        }
    return result


class PartialSupportValidationTests(unittest.TestCase):
    def test_single_proposition_with_topical_evidence_cannot_keep_partial_status(self):
        reason = "الدليل يصف الصدق بأنه خلق حميد، لكنه لا يثبت كفايته وحده لدخول الجنة."
        # Even grounded reasoning + valid quotes cannot establish partial support
        # without independent, entailed assertion proof for THIS review item.
        with patch("ai_compare.ask_ai", side_effect=[
            "YES|1", encoded({"status": "partially_supported", "reason": reason, "suggestion": ""}),
            encoded(validation(CLAIM, EVIDENCE)),
            encoded({"status": "needs_review", "reason": reason, "suggestion": ""}),
            encoded(validation(CLAIM, EVIDENCE)),
        ]) as model, patch("ai_compare.basic_relation_check", return_value=True), contextlib.redirect_stdout(io.StringIO()):
            result = ai_compare.compare_claim_with_evidence(CLAIM, [{"evidence": EVIDENCE}])
        self.assertEqual(result["status"], "needs_review")
        self.assertEqual(result["reason"], reason)
        self.assertEqual(result["suggestion"], "")
        self.assertEqual(result["best_evidence"], 1)
        verifier = model.call_args_list[2].args[0]
        self.assertIn("INSIDE THIS CURRENT CLAIM", verifier)
        self.assertIn("strip an essential", verifier)
        self.assertIn("genuinely entail one COMPLETE assertion", verifier)
        self.assertIn(ai_compare.STAGE2_STATUS_RULES, model.call_args_list[3].args[0])

    def test_topical_overlap_is_not_an_entailed_component(self):
        cases = [
            (CLAIM, EVIDENCE, "والصدق", "وحده كافٍ لدخول الجنة"),
            ("القراءة وحدها تضمن النجاح.", "القراءة نشاط مفيد.", "القراءة", "وحدها تضمن النجاح"),
            ("المكتبة تفتح الجمعة، والدخول مجاني.", "المكتبة مؤسسة ثقافية.",
             "المكتبة تفتح الجمعة", "الدخول مجاني"),
        ]
        for claim, evidence, supported, unsupported in cases:
            proof = validation(claim, evidence, supported, unsupported)
            # Independent semantic verifier must reject subject/predicate splits
            # and merely related evidence, even with real non-overlapping quotes.
            proof["partial_support"]["supported_assertion_entailed"] = False
            with self.subTest(claim=claim), patch("ai_compare.ask_ai", return_value=encoded(proof)):
                self.assertFalse(ai_compare._reason_is_grounded(
                    claim, "الدليل يتناول الموضوع ولا يثبت النتيجة.", evidence, "partially_supported"))

    def test_component_proof_fails_closed_for_missing_invalid_or_overlapping_anchors(self):
        claim = "المكتبة تفتح الجمعة، والدخول مجاني."
        evidence = "المكتبة تفتح الجمعة."
        valid = validation(claim, evidence, "المكتبة تفتح الجمعة", "الدخول مجاني")
        invalid = [None, {}, {**valid["partial_support"], "independent_assertions": "true"},
                   {**valid["partial_support"], "independent_assertions": False},
                   {**valid["partial_support"], "other_assertion_unsupported": False},
                   {**valid["partial_support"], "supported_component": "المكتبة متاحة"},
                   {**valid["partial_support"], "supported_component": claim},
                   {**valid["partial_support"], "unsupported_component": "المكتبة تفتح الجمعة"},
                   {**valid["partial_support"], "supported_component": 1}]
        for proof in invalid:
            with self.subTest(proof=proof), patch("ai_compare.ask_ai", return_value=encoded({
                **valid, "partial_support": proof,
            })):
                self.assertFalse(ai_compare._reason_is_grounded(
                    claim, "الدليل يثبت موعد الفتح ولا يثبت مجانية الدخول.", evidence, "partially_supported"))

    def test_failed_repair_cannot_reintroduce_partial_without_component_proof(self):
        reason = "الدليل لا يثبت كفاية الصدق وحده لدخول الجنة."
        with patch("ai_compare.ask_ai", side_effect=[
            "YES|1", encoded({"status": "partially_supported", "reason": reason, "suggestion": ""}),
            encoded(validation(CLAIM, EVIDENCE)),
            encoded({"status": "partially_supported", "reason": reason, "suggestion": ""}),
            encoded(validation(CLAIM, EVIDENCE)),
        ]), patch("ai_compare.basic_relation_check", return_value=True), contextlib.redirect_stdout(io.StringIO()):
            result = ai_compare.compare_claim_with_evidence(CLAIM, [{"evidence": EVIDENCE}])
        self.assertEqual(result["status"], "needs_review")
        self.assertEqual(result["suggestion"], "")

    def test_all_four_statuses_reach_api_with_valid_current_item_proofs(self):
        cases = [
            ("supported", "المكتبة تفتح الجمعة.", "المكتبة تفتح الجمعة.",
             "الدليل يثبت موعد فتح المكتبة.", None, None),
            ("partially_supported", "المكتبة تفتح الجمعة، والدخول مجاني.", "المكتبة تفتح الجمعة.",
             "الدليل يثبت موعد الفتح ولا يثبت مجانية الدخول.", "المكتبة تفتح الجمعة", "الدخول مجاني"),
            ("needs_context", "المكتبة متاحة للزوار.", "المكتبة متاحة للزوار المسجلين فقط.",
             "الدليل يشترط التسجيل لإتاحة المكتبة.", None, None),
            ("needs_review", "المكتبة تفتح الجمعة.", "المكتبة مغلقة الجمعة.",
             "الدليل يقول إن المكتبة مغلقة الجمعة خلاف المعلومة.", None, None),
        ]
        for status, claim, evidence, reason, supported, unsupported in cases:
            item = {"evidence": evidence, "source_name": "reference", "source_location": "location"}
            with self.subTest(status=status), patch("main.extract_claims", return_value=[claim]), \
                 patch("main.search_hadiths", return_value=[item]), patch("main.search_dorar", return_value=[]), \
                 patch("main.search_central_db", return_value=[]), patch("ai_compare._propose_revision", return_value=""), \
                 patch("ai_compare.ask_ai", side_effect=[
                     "YES|1", encoded({"status": status, "reason": reason, "suggestion": ""}),
                     encoded(validation(claim, evidence, supported, unsupported)),
                 ]), contextlib.redirect_stdout(io.StringIO()):
                result = main.analyze(main.AnalyzeRequest(text=claim))["claims"][0]
            self.assertEqual(result["status"], status)
            self.assertEqual(result["evidence"], [item])
            self.assertEqual(result["reason"], reason)


if __name__ == "__main__":
    unittest.main()
