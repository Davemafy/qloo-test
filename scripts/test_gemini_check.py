import copy
import unittest
from gemini_check import PROFILES, request_body, validate


def response():
    return {"candidates": [{"finishReason": "STOP", "content": {"parts": [{"functionCall": {
        "name": "submit_brief", "args": {"participant_ids": [p["id"] for p in PROFILES], "budget": 60,
        "duration_minutes": 180, "unknown_facts": ["prices", "durations", "availability"], "needs_clarification": True}
    }}]}}]}


class Contracts(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(validate(response())["budget"], 60)

    def test_rejects_invalid_contracts(self):
        cases = [({"budget": 600}), ({"duration_minutes": 200}), ({"needs_clarification": False}),
                 ({"participant_ids": ["amara"] * 6}), ({"unknown_facts": []}), ({"invented": True})]
        for patch in cases:
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                data = response()
                data["candidates"][0]["content"]["parts"][0]["functionCall"]["args"].update(patch)
                validate(data)

    def test_rejects_missing_truncated_and_unauthorized(self):
        for data in [{}, {"candidates": []}, {"candidates": [{"finishReason": "MAX_TOKENS"}]}]:
            with self.subTest(data=data), self.assertRaises(ValueError):
                validate(data)
        data = response()
        data["candidates"][0]["content"]["parts"][0]["functionCall"]["name"] = "fetch_url"
        with self.assertRaises(ValueError):
            validate(data)

    def test_request_bounded_and_no_qloo(self):
        body = request_body()
        self.assertEqual(body["generationConfig"]["maxOutputTokens"], 600)
        self.assertEqual(body["toolConfig"]["functionCallingConfig"]["allowedFunctionNames"], ["submit_brief"])
        self.assertEqual(len(body["tools"][0]["functionDeclarations"]), 1)


if __name__ == "__main__":
    unittest.main()
