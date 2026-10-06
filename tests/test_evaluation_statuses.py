import contextlib
import io
import json
import unittest
from unittest.mock import patch

import ai_compare
import main


STATUSES = ("supported", "partially_supported", "needs_context", "needs_review")


class EvaluationStatusTests(unittest.TestCase):
    def compare(self, response, claim="الصدق محمود", evidence="الصدق محمود في هذا السياق"):
        with patch("ai_compare.ask_ai", side_effect=["YES|1", response, json.dumps({
            "grounded": True, "claim_quote": claim, "evidence_quote": evidence,
        })]), \
             patch("ai_compare._propose_revision", return_value=""), \
             contextlib.redirect_stdout(io.StringIO()):
            return ai_compare.compare_claim_with_evidence(claim, [{
                "evidence": evidence, "source_name": "reference", "source_location": "location",
            }])

    def test_each_valid_model_status_survives_evaluation(self):
        # These are transport/validation fixtures, not prescribed AI judgments.
        for status in STATUSES:
            with self.subTest(status=status):
                result = self.compare(json.dumps({"status": status, "reason": "model reason", "suggestion": ""}))
                self.assertEqual(result["status"], status)
                self.assertEqual(result["reason"], "model reason")
                self.assertEqual(result["best_evidence"], 1)

    def test_each_status_survives_analyze_contract(self):
        claim = "الصدق محمود"
        evidence = {"evidence": "الصدق محمود", "source_name": "reference", "source_location": "location"}
        for status in STATUSES:
            with self.subTest(status=status), patch("main.extract_claims", return_value=[claim]), \
                 patch("main.search_hadiths", return_value=[evidence]), \
                 patch("main.search_dorar", return_value=[]), patch("main.search_central_db", return_value=[]), \
                 patch("ai_compare.ask_ai", side_effect=["YES|1", json.dumps({
                     "status": status, "reason": "model reason", "suggestion": "",
                 }), json.dumps({"grounded": True, "claim_quote": claim, "evidence_quote": evidence["evidence"]})]), \
                 patch("ai_compare._propose_revision", return_value=""), contextlib.redirect_stdout(io.StringIO()):
                result = main.analyze(main.AnalyzeRequest(text=claim))
                self.assertEqual(result["claims"][0]["status"], status)
                self.assertEqual(result["claims"][0]["evidence"], [evidence])

    def test_unknown_status_fails_conservatively(self):
        result = self.compare('{"status": "unknown", "reason": "reason", "suggestion": ""}')
        self.assertEqual(result["status"], "needs_review")

    def test_invalid_json_fails_conservatively(self):
        result = self.compare("not JSON")
        self.assertEqual(result["status"], "needs_review")

    def test_no_selected_evidence_never_reaches_status_evaluation(self):
        with patch("ai_compare.ask_ai", return_value="NO") as model, \
             contextlib.redirect_stdout(io.StringIO()):
            result = ai_compare.compare_claim_with_evidence("الصدق محمود", [{
                "evidence": "عدد الشهور اثنا عشر", "source_name": "reference", "source_location": "location",
            }])
        model.assert_called_once()
        self.assertEqual(result["status"], "needs_review")
        self.assertIsNone(result["best_evidence"])

    def test_unrelated_evidence_cannot_keep_positive_model_status(self):
        for status in STATUSES[:-1]:
            with self.subTest(status=status):
                result = self.compare(json.dumps({"status": status, "reason": "reason", "suggestion": ""}),
                                      evidence="عدد الشهور اثنا عشر")
                self.assertEqual(result["status"], "needs_review")


if __name__ == "__main__":
    unittest.main()
