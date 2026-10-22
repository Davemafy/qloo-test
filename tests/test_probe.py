import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from probe import summarize_response


class InsightsSummaryTests(unittest.TestCase):
    def test_supports_results_entities_shape(self):
        payload = {
            "results": {
                "entities": [
                    {"name": "Book One", "entity_id": "book-1", "score": 0.91},
                    {"name": "Book Two", "entity_id": "book-2"},
                ],
                "query": {"explainability": {"signal": "artist"}},
            }
        }
        summary = summarize_response(payload)
        self.assertEqual(summary["entity_collection"], "results.entities")
        self.assertEqual(summary["result_count"], 2)
        self.assertEqual(summary["entities"][0]["name"], "Book One")
        self.assertEqual(summary["explainability_present"], True)

    def test_supports_list_results_shape(self):
        summary = summarize_response({"results": [{"title": "Book A"}, {"name": "Book B"}]})
        self.assertEqual(summary["entity_collection"], "results")
        self.assertEqual(summary["result_count"], 2)
        self.assertEqual(summary["entities"][0]["title"], "Book A")

    def test_supports_entities_top_level(self):
        summary = summarize_response({"entities": [{"name": "Book A"}]})
        self.assertEqual(summary["entity_collection"], "entities")
        self.assertEqual(summary["result_count"], 1)

    def test_unknown_shape_still_reports_schema(self):
        summary = summarize_response({"results": {"items": [], "meta": {"page": 1}}})
        self.assertIsNone(summary["entity_collection"])
        self.assertIsNone(summary["result_count"])
        self.assertEqual(summary["results_keys"], ["items", "meta"])

    def test_redacts_secret_fields_and_values(self):
        summary = summarize_response({
            "results": {"entities": [{
                "name": "Book A",
                "email": "private@example.com",
                "explanation": {"token": "do-not-leak"},
            }]}
        })
        rendered = str(summary)
        self.assertNotIn("private@example.com", rendered)
        self.assertNotIn("do-not-leak", rendered)
        self.assertIn("[redacted]", rendered)


if __name__ == "__main__":
    unittest.main()
