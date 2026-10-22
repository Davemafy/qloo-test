#!/usr/bin/env python3
"""Quota-safe, single-request Qloo smoke test. Never prints or persists credentials."""
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


class NoRedirect(urllib.request.HTTPRedirectHandler):
    # Do not forward X-Api-Key to a redirect destination.
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


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
        return [sanitize(item, api_key, depth + 1) for item in value[:20]] + (
            [{"_truncated_items": len(value) - 20}] if len(value) > 20 else []
        )
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

    # One fixed endpoint and one fixed query. No retries, loops, or fallback hosts.
    query = urllib.parse.urlencode({
        "query": "Radiohead",
        "types": "urn:entity:artist",
    })
    url = f"{BASE_URL}/search?{query}"
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
        "test": "single_search_smoke",
        "request_budget": 1,
        "requests_attempted": 1,
        "endpoint_host": "hackathon.api.qloo.com",
        "endpoint_path": "/search",
        "query": {"query": "Radiohead", "types": "urn:entity:artist"},
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
                result["response_text_preview"] = body.decode("utf-8", errors="replace")[:2000]
    except urllib.error.HTTPError as exc:
        # No retries. Redirects are blocked, so an HTTP 3xx is recorded safely.
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
        # Do not retain the credential in any output object.
        api_key = None

    serialized = json.dumps(result, indent=2, ensure_ascii=False)
    if len(serialized) > MAX_ARTIFACT_CHARS:
        result.pop("response", None)
        result.pop("response_text_preview", None)
        result["error"] = result.get("error", "Response omitted") + " Sanitized payload exceeded artifact size limit."
        serialized = json.dumps(result, indent=2, ensure_ascii=False)
    with open("results.json", "w", encoding="utf-8") as output:
        output.write(serialized + "\n")

    # Print only high-level metadata. Full sanitized result is available as a short-lived artifact.
    print(json.dumps({
        "test": result["test"],
        "http_status": result.get("http_status"),
        "requests_attempted": result["requests_attempted"],
        "result_keys": list(result.get("response", {}).keys()) if isinstance(result.get("response"), dict) else [],
        "error": result.get("error"),
        "artifact": "results.json",
    }, ensure_ascii=False))
    return 0 if result.get("http_status") == 200 else 1


if __name__ == "__main__":
    raise SystemExit(main())
