#!/usr/bin/env python3
"""Quota-safe, single-request Qloo Insights probe. Never prints or persists credentials."""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

BASE_URL = "https://hackathon.api.qloo.com"
MAX_RESPONSE_BYTES = 256_000
MAX_ARTIFACT_CHARS = 30_000
SECRET_FIELDS = ("api_key", "apikey", "authorization", "token", "secret", "email", "phone")
RADIOHEAD_ENTITY_ID = "70CAE5BF-2F4C-445C-A3E5-4EDACFC3591C"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    # Do not forward X-Api-Key to a redirect destination.
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def safe_preview(body, api_key, limit=2000):
    text = body.decode("utf-8", errors="replace")
    if api_key:
        text = text.replace(api_key, "[redacted]")
    return text[:limit]


def sanitize(value, api_key=None, depth=0):
    if depth > 8:
        return "[depth limit]"
    if isinstance(value, dict):
        out = {}
        for key, item in list(value.items())[:60]:
            key_text = str(key)
            if any(term in key_text.lower() for term in SECRET_FIELDS):
                out[key_text] = "[redacted]"
            else:
                out[key_text] = sanitize(item, api_key, depth + 1)
        if len(value) > 60:
            out["_truncated_keys"] = len(value) - 60
        return out
    if isinstance(value, list):
        items = [sanitize(item, api_key, depth + 1) for item in value[:20]]
        if len(value) > 20:
            items.append({"_truncated_items": len(value) - 20})
        return items
    if isinstance(value, str):
        result = value[:1000]
        if api_key:
            result = result.replace(api_key, "[redacted]")
        return result
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return str(value)[:500]


def main():
    api_key = os.environ.get("QLOO_API_KEY", "")
    configured_budget = os.environ.get("MAX_REQUESTS", "")
    if not api_key:
        print("Missing QLOO_API_KEY; no request made.", file=sys.stderr)
        return 2
    if configured_budget != "1":
        print("Safety stop: MAX_REQUESTS must equal 1; no request made.", file=sys.stderr)
        return 2

    # Exactly one cross-domain Insights request: Radiohead -> book recommendations.
    # No retries, loops, or fallback hosts.
    params = {
        "filter.type": "urn:entity:book",
        "signal.interests.entities": RADIOHEAD_ENTITY_ID,
        "take": "10",
        "feature.explainability": "true",
    }
    query = urllib.parse.urlencode(params)
    url = f"{BASE_URL}/v2/insights?{query}"
    request = urllib.request.Request(
        url,
        headers={
            "X-Api-Key": api_key,
            "Accept": "application/json",
            "User-Agent": "qloo-test-harness/0.1",
        },
        method="GET",
    )
    opener = urllib.request.build_opener(NoRedirect)
    result = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "test": "single_insights_cross_domain",
        "request_budget": 1,
        "requests_attempted": 1,
        "endpoint_host": "hackathon.api.qloo.com",
        "endpoint_path": "/v2/insights",
        "query": params,
        "hypothesis": "A music-artist signal can retrieve Qloo-affinity-ranked books, exposing a cross-domain taste association.",
        "seed_entity": {"name": "Radiohead", "entity_id": RADIOHEAD_ENTITY_ID},
        "result_type": "urn:entity:book",
    }

    try:
        with opener.open(request, timeout=20) as response:
            status = response.status
            body = response.read(MAX_RESPONSE_BYTES + 1)
        result["http_status"] = status
        if len(body) > MAX_RESPONSE_BYTES:
            result["error"] = f"Response exceeded {MAX_RESPONSE_BYTES} bytes; body omitted."
        else:
            try:
                parsed = json.loads(body.decode("utf-8"))
                result["response"] = sanitize(parsed, api_key)
            except (UnicodeDecodeError, json.JSONDecodeError):
                result["response_text_preview"] = safe_preview(body, api_key)
    except urllib.error.HTTPError as exc:
        result["http_status"] = exc.code
        result["error"] = "HTTP error response; inspect status and sanitized body preview."
        try:
            body = exc.read(8000)
            parsed = json.loads(body.decode("utf-8"))
            result["response"] = sanitize(parsed, api_key)
        except Exception:
            result["response_text_preview"] = "[omitted: non-JSON or unreadable error body]"
    except urllib.error.URLError as exc:
        result["error"] = "Network/endpoint error: " + str(getattr(exc, "reason", "unknown"))[:300]
    except TimeoutError:
        result["error"] = "Request timed out after 20 seconds; no retry attempted."
    finally:
        api_key = None

    serialized = json.dumps(result, indent=2, ensure_ascii=False)
    if len(serialized) > MAX_ARTIFACT_CHARS:
        result.pop("response", None)
        result.pop("response_text_preview", None)
        result["error"] = result.get("error", "Response omitted") + " Sanitized payload exceeded artifact size limit."
        serialized = json.dumps(result, indent=2, ensure_ascii=False)
    with open("results.json", "w", encoding="utf-8") as output:
        output.write(serialized + "\n")

    response = result.get("response", {})
    results = response.get("results", []) if isinstance(response, dict) else []
    print(json.dumps({
        "test": result["test"],
        "http_status": result.get("http_status"),
        "requests_attempted": result["requests_attempted"],
        "result_count": len(results) if isinstance(results, list) else None,
        "first_result_names": [x.get("name") for x in results[:5] if isinstance(x, dict)] if isinstance(results, list) else [],
        "explainability_present": "query" in response if isinstance(response, dict) else False,
        "error": result.get("error"),
        "artifact": "results.json",
    }, ensure_ascii=False))
    return 0 if result.get("http_status") == 200 else 1


if __name__ == "__main__":
    raise SystemExit(main())
