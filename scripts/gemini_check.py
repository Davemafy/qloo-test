"""Standalone public-safe model check. No Igor imports or Qloo requests."""
import json
import os
import re
import socket
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

MODEL = "gemini-2.5-flash"


def choose_model(data):
    allowed = []
    for model in data.get("models", []):
        name = model.get("name", "")
        if (re.fullmatch(r"models/gemini-[a-z0-9.-]+", name)
                and "flash" in name
                and not any(word in name for word in ("image", "audio", "live", "native", "tts", "preview", "exp"))
                and "generateContent" in model.get("supportedGenerationMethods", [])):
            allowed.append(name)
    if not allowed:
        raise ValueError("no_supported_stable_flash_model")
    for preferred in ("models/gemini-3.5-flash-lite", "models/gemini-3.8-flash", "models/gemini-3.5-flash", "models/gemini-2.5-flash-lite", "models/gemini-2.5-flash"):
        if preferred in allowed:
            return preferred.removeprefix("models/"), sorted(allowed)
    return sorted(allowed)[-1].removeprefix("models/"), sorted(allowed)
PROFILES = [
    {"id": "amara", "likes": ["Radiohead"]},
    {"id": "leo", "likes": ["Kendrick Lamar"]},
    {"id": "june", "likes": ["Spirited Away"]},
    {"id": "sam", "likes": ["Arrival"]},
    {"id": "noor", "likes": ["Laufey"]},
    {"id": "eli", "likes": ["Moonlight"]},
]


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def request_body():
    schema = {
        "type": "OBJECT",
        "properties": {
            "participant_ids": {"type": "ARRAY", "items": {"type": "STRING"}},
            "budget": {"type": "NUMBER"},
            "duration_minutes": {"type": "INTEGER"},
            "unknown_facts": {"type": "ARRAY", "items": {"type": "STRING"}},
            "needs_clarification": {"type": "BOOLEAN"},
        },
        "required": ["participant_ids", "budget", "duration_minutes", "unknown_facts", "needs_clarification"],
    }
    context = {
        "goal": "Plan a six-person gathering with a film and music.",
        "profiles": PROFILES,
        "budget": 60,
        "currency": "USD",
        "duration_minutes": 180,
        "candidates": [],
        "facts": "Sample profiles only. Prices, durations and availability are unknown. No Qloo results supplied.",
    }
    return {
        "systemInstruction": {"parts": [{"text": "Extract only supplied facts. Call submit_brief once. Keep all six participants distinct. Do not invent candidates or practical facts. List unknown facts as prices, durations, availability. A feasible programme requires clarification."}]},
        "contents": [{"role": "user", "parts": [{"text": json.dumps(context)}]}],
        "tools": [{"functionDeclarations": [{"name": "submit_brief", "description": "Submit the extracted brief; no external actions.", "parameters": schema}]}],
        "toolConfig": {"functionCallingConfig": {"mode": "ANY", "allowedFunctionNames": ["submit_brief"]}},
        "generationConfig": {"temperature": 0, "maxOutputTokens": 600, "thinkingConfig": {"thinkingBudget": 0}},
    }


def validate(response):
    candidates = response.get("candidates", [])
    if len(candidates) != 1 or candidates[0].get("finishReason") != "STOP":
        raise ValueError("incomplete_or_blocked_response")
    parts = candidates[0].get("content", {}).get("parts", [])
    if len(parts) != 1 or parts[0].get("functionCall", {}).get("name") != "submit_brief":
        raise ValueError("unauthorized_or_missing_function")
    args = parts[0]["functionCall"].get("args")
    expected = {"participant_ids", "budget", "duration_minutes", "unknown_facts", "needs_clarification"}
    if not isinstance(args, dict) or set(args) != expected:
        raise ValueError("invalid_fields")
    ids = args["participant_ids"]
    if not isinstance(ids, list) or len(ids) != 6 or set(ids) != {p["id"] for p in PROFILES}:
        raise ValueError("participant_loss_or_duplication")
    if type(args["budget"]) not in (int, float) or args["budget"] != 60:
        raise ValueError("budget_changed")
    if type(args["duration_minutes"]) is not int or args["duration_minutes"] != 180:
        raise ValueError("duration_changed")
    if args["needs_clarification"] is not True:
        raise ValueError("unknowns_not_respected")
    unknowns = args["unknown_facts"]
    if (not isinstance(unknowns, list) or len(unknowns) != 3
            or not all(isinstance(item, str) for item in unknowns)
            or {item.strip().casefold() for item in unknowns} != {"prices", "durations", "availability"}):
        raise ValueError("unknown_facts_changed")
    return {**args, "unknown_facts": [item.strip().casefold() for item in unknowns]}


def main():
    out = Path("artifacts")
    out.mkdir(exist_ok=True)
    report = {"at": datetime.now(timezone.utc).isoformat(), "model_requested": MODEL,
              "model_requests": 0, "discovery_requests": 0, "qloo_requests": 0, "status": "blocked",
              "scope": "Structured brief extraction only; not product integration or Qloo value evaluation.",
              "profile_origin": "synthetic sample profiles", "request": request_body()}
    code = 1
    key = os.environ.get("GEMINI_API_KEY", "")
    try:
        if not key:
            raise ValueError("missing_gemini_secret")
        opener = urllib.request.build_opener(NoRedirect())
        report["discovery_requests"] = 1
        listing = urllib.request.Request(
            "https://generativelanguage.googleapis.com/v1beta/models?pageSize=1000",
            headers={"x-goog-api-key": key})
        with opener.open(listing, timeout=30) as result:
            listing_raw = result.read(1000001)
        if len(listing_raw) > 1000000:
            raise ValueError("model_listing_size_limit")
        model, names = choose_model(json.loads(listing_raw))
        report["available_stable_flash_models"] = names
        report["model_requested"] = model
        if not model.startswith("gemini-2.5-"):
            report["request"]["generationConfig"].pop("thinkingConfig", None)
        request = urllib.request.Request(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            data=json.dumps(report["request"]).encode(),
            headers={"Content-Type": "application/json", "x-goog-api-key": key}, method="POST")
        report["model_requests"] = 1
        with opener.open(request, timeout=75) as result:
            raw = result.read(100001)
        if len(raw) > 100000:
            raise ValueError("response_size_limit")
        response = json.loads(raw)
        report["provider_response"] = response
        report["result"] = validate(response)
        report["model_returned"] = response.get("modelVersion")
        usage = response.get("usageMetadata", {})
        report["usage"] = {k: v for k, v in usage.items() if k in ("promptTokenCount", "candidatesTokenCount", "totalTokenCount", "thoughtsTokenCount") and type(v) is int}
        report["status"] = "passed"
        code = 0
    except urllib.error.HTTPError as error:
        report["error"] = f"http_{error.code}"
        try:
            detail = json.loads(error.read(8192)).get("error", {})
            report["provider_error"] = {k: str(detail[k])[:1200] for k in ("status", "message") if k in detail}
        except (ValueError, AttributeError, TypeError):
            report["provider_error"] = {"status": "unparseable_error_body"}
    except (TimeoutError, socket.timeout):
        report["error"] = "timeout"
    except urllib.error.URLError:
        report["error"] = "network_error"
    except (ValueError, KeyError, TypeError, AttributeError) as error:
        report["error"] = "invalid_response_or_configuration"
        report["validation_error"] = str(error)[:300]
    serialized = json.dumps(report, indent=2)
    if key:
        serialized = serialized.replace(key, "[REDACTED]")
    (out / "gemini-check.json").write_text(serialized)
    print(json.dumps({k: report[k] for k in ("status", "model_requests", "qloo_requests")}))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
