import unittest
from gathering_probe import rows, resolve, select_call, check_selection

ID = "11111111-1111-4111-8111-111111111111"


class Contracts(unittest.TestCase):
    def test_exact_and_ambiguous_resolution(self):
        row = {"entity_id": ID, "name": "Radiohead", "subtype": "urn:entity:artist"}
        self.assertEqual(resolve({"results": [row]}, "Radiohead", "artist")["providerId"], ID)
        self.assertEqual(resolve({"results": [row, row]}, "Radiohead", "artist")["status"], "ambiguous")
        self.assertIsNone(resolve({"results": [row]}, "Wrong", "artist")["providerId"])

    def test_empty_and_malformed(self):
        self.assertEqual(rows({"results": {"entities": []}}), [])
        for body in ({}, {"results": [{"entity_id": "bad", "name": "bad"}]}):
            with self.assertRaises((ValueError, KeyError)):
                rows(body)

    def test_live_search_types_array(self):
        row = {"entity_id": ID, "name": "Radiohead", "types": ["urn:entity:artist"]}
        self.assertEqual(resolve({"results": [row]}, "Radiohead", "artist")["status"], "resolved")
        self.assertEqual(resolve({"results": [row]}, "Radiohead", "movie")["status"], "unresolved")

    def test_selection_rejects_fabrication_duplicates_and_extra_fields(self):
        self.assertEqual(check_selection({"ids": [ID]}, [{"id": ID}]), [ID])
        for args in ({"ids": ["fake"]}, {"ids": [ID, ID]}, {"ids": [], "claim": "feasible"}):
            with self.assertRaises(ValueError):
                check_selection(args, [{"id": ID}])

    def test_unauthorized_incomplete_or_multiple_tool_calls(self):
        for response in ({}, {"candidates": [{"finishReason": "STOP", "content": {"parts": [{"functionCall": {"name": "fetch_url"}}]}}]}):
            with self.assertRaises(ValueError):
                select_call(response, "inspect_candidates")


if __name__ == "__main__":
    unittest.main()
