import unittest
from unittest.mock import Mock, patch

import requests

import central_db
import main


class CentralDBTests(unittest.TestCase):
    def setUp(self):
        self.example = {
            "source_text": "نص الدليل العربي",
            "target_text": "English translation",
            "similarity_percent": 78.18,
            "phrase_id": "phrase-123",
        }

    def search(self, payload):
        response = Mock(status_code=200)
        response.json.return_value = payload
        with patch("central_db.requests.get", return_value=response) as get:
            results = central_db.search_central_db("claim")
            get.assert_called_once_with(
                central_db.CENTRAL_DB_URL,
                params={"query": "claim", "k": 5},
                timeout=15,
            )
        return results

    def test_arabic_evidence_and_clean_source_location(self):
        results = self.search({
            "project_id": None,
            "search_scope": "all_books_latest_versions",
            "examples": [self.example],
        })
        self.assertEqual(len(results), 1)
        self.assertEqual(set(results[0]), {"evidence", "source_name", "source_location"})
        self.assertEqual(results[0]["evidence"], self.example["source_text"])
        self.assertEqual(results[0]["source_name"], central_db.SOURCE_NAME)
        location = results[0]["source_location"]
        self.assertEqual(location, "نتيجة موثقة من القاعدة المركزية")

    def test_actual_book_title_displayed_without_technical_metadata(self):
        example = dict(self.example, book_title="Returned title", version_id=3)
        example["metadata"] = {"project": {"id": 7}}
        location = self.search({"project_id": 7, "examples": [example]})[0]["source_location"]
        self.assertEqual(location, "Returned title")

    def test_actual_book_and_human_version(self):
        example = dict(self.example, metadata={"book": {"title": "كتاب حقيقي"}, "version": {"number": 2}})
        self.assertEqual(self.search({"examples": [example]})[0]["source_location"], "كتاب حقيقي – الإصدار 2")

    def test_network_errors(self):
        for error in [requests.Timeout(), requests.ConnectionError(), requests.RequestException()]:
            with self.subTest(error=type(error).__name__), patch("central_db.requests.get", side_effect=error):
                self.assertEqual(central_db.search_central_db("claim"), [])

    def test_non_200(self):
        for status in [204, 301, 403, 429, 500]:
            response = Mock(status_code=status)
            with self.subTest(status=status), patch("central_db.requests.get", return_value=response):
                self.assertEqual(central_db.search_central_db("claim"), [])
                response.json.assert_not_called()

    def test_invalid_json(self):
        response = Mock(status_code=200)
        response.json.side_effect = ValueError("Invalid JSON")
        with patch("central_db.requests.get", return_value=response):
            self.assertEqual(central_db.search_central_db("claim"), [])

    def test_malformed_response(self):
        payloads = [None, [], {}, {"examples": None}, {"examples": {}}, {"examples": [None]}]
        for field, value in [
            ("source_text", None), ("source_text", ""), ("phrase_id", None),
            ("similarity_percent", None), ("similarity_percent", float("nan")),
        ]:
            payloads.append({"examples": [dict(self.example, **{field: value})]})
        for payload in payloads:
            with self.subTest(payload=payload):
                self.assertEqual(self.search(payload), [])
        self.assertEqual(self.search({"examples": []}), [])


class AnalyzeIntegrationTests(unittest.TestCase):
    def setUp(self):
        patcher = patch("main.extract_claims", side_effect=lambda text: [text])
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_sources_combined_and_selected_result_contract(self):
        evidence = [
            {"evidence": "HadeethEnc text", "source_name": "HadeethEnc", "source_location": "location"},
            {"evidence": "Dorar text", "source_name": "Dorar.net", "source_location": "location"},
            {"evidence": "Central text", "source_name": central_db.SOURCE_NAME, "source_location": "phrase_id: 1 | similarity_percent: 78.18"},
        ]
        with patch("main.search_hadiths", return_value=evidence[:1]) as hadeeth, \
             patch("main.search_dorar", return_value=evidence[1:2]), \
             patch("main.search_central_db", return_value=evidence[2:]) as central, \
             patch("main.compare_claim_with_evidence", return_value={
                 "best_evidence": 3, "status": "supported", "reason": "reason", "suggestion": "",
             }) as compare:
            result = main.analyze(main.AnalyzeRequest(text="claim"))
        hadeeth.assert_called_once_with("claim", top_k=3)
        central.assert_called_once_with("claim", top_k=5)
        compare.assert_called_once_with("claim", evidence)
        self.assertEqual(result, {"claims": [{
            "claim": "claim", "status": "supported", "evidence": evidence[2:],
            "reason": "reason", "suggestion": "",
        }]})

    def test_optional_sources_fail_without_breaking_hadeethenc(self):
        evidence = {"evidence": "text", "source_name": "HadeethEnc", "source_location": "location"}
        with patch("main.search_hadiths", return_value=[evidence]), \
             patch("dorar.requests.get", side_effect=requests.HTTPError("HTTP 403")), \
             patch("main.compare_claim_with_evidence", return_value={"best_evidence": 1, "status": "supported"}) as compare:
            result = main.analyze(main.AnalyzeRequest(text="claim"))
        compare.assert_called_once_with("claim", [evidence])
        self.assertEqual(result["claims"][0]["evidence"], [evidence])

    def test_no_evidence_preserves_needs_review(self):
        with patch("main.search_hadiths", return_value=[]), \
             patch("main.search_dorar", return_value=[]), \
             patch("main.search_central_db", return_value=[]), \
             patch("main.compare_claim_with_evidence") as compare:
            result = main.analyze(main.AnalyzeRequest(text="claim"))
        compare.assert_not_called()
        self.assertEqual(result["claims"][0]["status"], "needs_review")
        self.assertEqual(result["claims"][0]["evidence"], [])


if __name__ == "__main__":
    unittest.main()
