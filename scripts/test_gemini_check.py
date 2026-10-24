import copy
import unittest
from gemini_check import PROFILES, request_body, validate, choose_model


def response():
    return {"candidates": [{"finishReason": "STOP", "content": {"parts": [{"functionCall": {
        "name": "submit_brief", "args": {"participant_ids": [p["id"] for p in PROFILES], "budget": 60,
        "duration_minutes": 180, "unknown_facts": ["prices", "durations", "availability"], "needs_clarification": True}
    }}]}}]}


class Contracts(unittest.TestCase):
    def test_model_discovery_filters_untrusted_or_unsuitable_models(self):
        names = ["models/gemini-2.5-flash-lite", "models/gemini-2.5-flash-image", "https://evil.test/flash", "models/gemini-pro", "models/gemini-flash-preview"]
        selected, available = choose_model({"models": [{"name": n, "supportedGenerationMethods": ["generateContent"]} for n in names]})
        self.assertEqual(selected, "gemini-2.5-flash-lite")
        self.assertEqual(available, ["models/gemini-2.5-flash-lite"])

    def test_empty_or_non_generation_model_listing_blocks(self):
        for data in ({}, {"models": [{"name": "models/gemini-2.5-flash", "supportedGenerationMethods": ["embedContent"]}]}):
            with self.assertRaises(ValueError):
                choose_model(data)

    def test_valid(self):
        self.assertEqual(validate(response())["budget"], 60)

    def test_unknown_labels_normalize_case_without_losing_unknowns(self):
        data = response()
        data["candidates"][0]["content"]["parts"][0]["functionCall"]["args"]["unknown_facts"] = ["Prices", " Durations ", "Availability"]
        self.assertEqual(validate(data)["unknown_facts"], ["prices", "durations", "availability"])
        for unknowns in (["Prices", "Prices", "Availability"], ["Prices", 1, "Availability"]):
            data["candidates"][0]["content"]["parts"][0]["functionCall"]["args"]["unknown_facts"] = unknowns
            with self.assertRaises(ValueError):
                validate(data)

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
