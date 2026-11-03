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
MAX_ARTIFACT_CHARS = 12_000
SECRET_FIELDS = ("api_key", "apikey", "authorization", "token", "secret", "email", "phone")
CONTROL_MODE = "no_taste_signal"
ENTITY_FIELDS = ("name", "title", "entity_id", "id", "type", "score", "affinity", "subtype", "description", "disambiguation", "properties")
EXPLANATION_KEYS = {"explainability", "explanation", "explanations", "reason", "reasons"}


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
    """Bounded recursive sanitizer used only for small error responses."""
    if depth > 6:
        return "[depth limit]"
    if isinstance(value, dict):
        out = {}
        for key, item in list(value.items())[:40]:
            key_text = str(key)
            if any(term in key_text.lower() for term in SECRET_FIELDS):
                out[key_text] = "[redacted]"
            else:
                out[key_text] = sanitize(item, api_key, depth + 1)
        if len(value) > 40:
            out["_truncated_keys"] = len(value) - 40
        return out
    if isinstance(value, list):
        items = [sanitize(item, api_key, depth + 1) for item in value[:5]]
        if len(value) > 5:
            items.append({"_truncated_items": len(value) - 5})
        return items
    if isinstance(value, str):
        result = value[:300]
        if api_key:
            result = result.replace(api_key, "[redacted]")
        return result
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return str(value)[:200]


def _entity_collection(payload):
    """Return (path, entities) for common Qloo response layouts without assuming one schema."""
    if not isinstance(payload, dict):
        return None, None
    candidates = [
        ("results.entities", payload.get("results", {}).get("entities")
         if isinstance(payload.get("results"), dict) else None),
        ("results", payload.get("results") if isinstance(payload.get("results"), list) else None),
        ("data.entities", payload.get("data", {}).get("entities")
         if isinstance(payload.get("data"), dict) else None),
        ("data", payload.get("data") if isinstance(payload.get("data"), list) else None),
        ("entities", payload.get("entities")),
    ]
    for path, value in candidates:
        if isinstance(value, list):
            return path, value
    return None, None


def summarize_response(payload, api_key=None):
    """Keep a compact, useful result summary instead of dropping oversized API payloads."""
    collection_path, entities = _entity_collection(payload)
    query = payload.get("query") if isinstance(payload, dict) else None
    query_explainability = query.get("explainability") if isinstance(query, dict) else None
    # Some response versions may nest query metadata under results.
    if query_explainability is None and isinstance(payload, dict):
        results = payload.get("results")
        if isinstance(results, dict) and isinstance(results.get("query"), dict):
            query_explainability = results["query"].get("explainability")

    summary = {
        "top_level_keys": list(payload.keys())[:30] if isinstance(payload, dict) else [],
        "results_type": type(payload.get("results")).__name__
            if isinstance(payload, dict) and "results" in payload else None,
        "results_keys": list(payload["results"].keys())[:30]
            if isinstance(payload, dict) and isinstance(payload.get("results"), dict) else [],
        "entity_collection": collection_path,
        "result_count": len(entities) if entities is not None else None,
        "entities": [],
        "explainability_fields": [],
        "query_present": False,
        "query_explainability": sanitize(query_explainability, api_key)
            if query_explainability is not None else None,
    }

    if entities is not None:
        for entity in entities[:10]:
            if not isinstance(entity, dict):
                summary["entities"].append({"value_type": type(entity).__name__})
                continue
            item = {}
            for field in ENTITY_FIELDS:
                if field in entity and not any(term in field.lower() for term in SECRET_FIELDS):
                    item[field] = sanitize(entity[field], api_key)
            for field in entity:
                if str(field).lower() in EXPLANATION_KEYS:
                    summary["explainability_fields"].append("entity." + str(field))
                    item[str(field)] = sanitize(entity[field], api_key)
            summary["entities"].append(item)

    def collect_explanation_keys(value, prefix="", depth=0):
        if depth > 5 or not isinstance(value, dict):
            return
        for field, nested in list(value.items())[:40]:
            path = (prefix + "." if prefix else "") + str(field)
            if str(field).lower() == "query":
                summary["query_present"] = True
            if str(field).lower() in EXPLANATION_KEYS:
                summary["explainability_fields"].append(path)
            if isinstance(nested, dict):
                collect_explanation_keys(nested, path, depth + 1)

    collect_explanation_keys(payload)
    summary["explainability_fields"] = sorted(set(summary["explainability_fields"]))
    # Query metadata alone is not explainability.
    summary["explainability_present"] = (
        query_explainability is not None or bool(summary["explainability_fields"])
    )
    return summary



def serialize_bounded_result(result, limit=MAX_ARTIFACT_CHARS):
    """Serialize a result within the artifact cap, progressively dropping bulky fields."""
    def dump():
        return json.dumps(result, indent=2, ensure_ascii=False)

    serialized = dump()
    if len(serialized) <= limit:
        return serialized

    summary = result.get("response_summary")
    if isinstance(summary, dict):
        compact_entities = []
        for entity in summary.get("entities", []):
            if not isinstance(entity, dict):
                continue
            compact = {}
            for field in ("name", "title", "entity_id", "id", "type", "score", "affinity", "subtype"):
                if field in entity:
                    compact[field] = entity[field]
            if "description" in entity:
                compact["description"] = str(entity["description"])[:120]
            compact_entities.append(compact)
        summary["entities"] = compact_entities[:10]
        summary["top_level_keys"] = summary.get("top_level_keys", [])[:15]
        summary["results_keys"] = summary.get("results_keys", [])[:15]
        summary["explainability_fields"] = summary.get("explainability_fields", [])[:10]
        if summary.get("query_explainability") is not None:
            explanation = json.dumps(sanitize(summary["query_explainability"]), ensure_ascii=False)
            if len(explanation) > 1000:
                summary["query_explainability"] = "[omitted: explanation exceeded compact limit]"
    result["artifact_note"] = "Summary compacted to stay within artifact size limit."
    serialized = dump()
    if len(serialized) <= limit:
        return serialized

    if isinstance(summary, dict):
        summary["entities"] = [
            {key: entity[key] for key in ("name", "title", "entity_id", "id", "type", "score", "affinity")
             if key in entity}
            for entity in summary.get("entities", [])[:5] if isinstance(entity, dict)
        ]
        summary["query_explainability"] = None
        summary["explainability_fields"] = summary.get("explainability_fields", [])[:5]
        summary["top_level_keys"] = summary.get("top_level_keys", [])[:10]
        summary["results_keys"] = summary.get("results_keys", [])[:10]
    serialized = dump()
    if len(serialized) <= limit:
        return serialized

    compact_result = {
        key: result[key] for key in (
            "timestamp_utc", "test", "request_budget", "requests_attempted",
            "endpoint_host", "endpoint_path", "query", "http_status", "error",
            "artifact_note"
        ) if key in result
    }
    compact_result["artifact_note"] = "Payload omitted to enforce artifact size limit."
    serialized = json.dumps(compact_result, indent=2, ensure_ascii=False)
    if len(serialized) > limit:
        raise ValueError("Minimal result metadata exceeds artifact size limit")
    return serialized


def main():
    api_key = os.environ.get("QLOO_API_KEY", "")
    configured_budget = os.environ.get("MAX_REQUESTS", "")
    if not api_key:
        print("Missing QLOO_API_KEY; no request made.", file=sys.stderr)
        return 2
    if configured_budget != "1":
        print("Safety stop: MAX_REQUESTS must equal 1; no request made.", file=sys.stderr)
        return 2

    # Exactly one request: New York City places with a hip-hop tag signal.
    # No retries, loops, or fallback hosts.
    params = {
        "filter.type": "urn:entity:place",
        "filter.location.query": "New York City",
        "filter.location.radius": "0",
        "signal.interests.tags": "urn:tag:genre:music:hip_hop",
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
        "test": "hip_hop_tag_to_nyc_places",
        "request_budget": 1,
        "requests_attempted": 1,
        "endpoint_host": "hackathon.api.qloo.com",
        "endpoint_path": "/v2/insights",
        "query": params,
        "hypothesis": "Test whether a hip-hop music tag changes New York City place recommendations relative to the no-signal, Radiohead, and indie-tag conditions.",
        "seed_signal": {"type": "tag", "value": "urn:tag:genre:music:hip_hop"},
        "result_type": "urn:entity:place",
        "location": "New York City",
        "location_radius": 0,
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
                result["response_summary"] = summarize_response(parsed, api_key)
            except (UnicodeDecodeError, json.JSONDecodeError):
                result["response_text_preview"] = safe_preview(body, api_key)
    except urllib.error.HTTPError as exc:
        result["http_status"] = exc.code
        result["error"] = "HTTP error response; inspect status and sanitized body preview."
        try:
            body = exc.read(8000)
            parsed = json.loads(body.decode("utf-8"))
            result["error_response_summary"] = summarize_response(parsed, api_key)
        except Exception:
            result["response_text_preview"] = "[omitted: non-JSON or unreadable error body]"
    except urllib.error.URLError as exc:
        result["error"] = "Network/endpoint error: " + str(getattr(exc, "reason", "unknown"))[:300]
    except TimeoutError:
        result["error"] = "Request timed out after 20 seconds; no retry attempted."
    finally:
        api_key = None

    serialized = serialize_bounded_result(result)
    with open("results.json", "w", encoding="utf-8") as output:
        output.write(serialized + "\n")

    summary = result.get("response_summary", {})
    print(json.dumps({
        "test": result["test"],
        "http_status": result.get("http_status"),
        "requests_attempted": result["requests_attempted"],
        "result_count": summary.get("result_count") if isinstance(summary, dict) else None,
        "first_result_names": [
            entity.get("name", entity.get("title"))
            for entity in summary.get("entities", []) if isinstance(entity, dict)
        ] if isinstance(summary, dict) else [],
        "explainability_present": summary.get("explainability_present", False)
            if isinstance(summary, dict) else False,
        "query_explainability_captured": summary.get("query_explainability") is not None
            if isinstance(summary, dict) else False,
        "error": result.get("error"),
        "artifact": "results.json",
    }, ensure_ascii=False))
    return 0 if result.get("http_status") == 200 else 1


if __name__ == "__main__":
    raise SystemExit(main())
