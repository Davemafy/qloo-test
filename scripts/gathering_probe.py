"""Independent provider harness; no Igor application source or dependencies."""
import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from gemini_check import NoRedirect

MODEL = "gemini-3.5-flash-lite"
DOMAINS = ("movie", "tv_show", "artist")
PROFILES = [
    ("amara", "Amara", "Radiohead", "artist", ["indie", "reflective"], ["horror"]),
    ("leo", "Leo", "Kendrick Lamar", "artist", ["rhythmic", "drama"], ["ambient"]),
    ("june", "June", "Spirited Away", "movie", ["animation", "warm"], ["intense"]),
    ("sam", "Sam", "Arrival", "movie", ["sci-fi", "reflective"], ["romance"]),
    ("noor", "Noor", "Laufey", "artist", ["jazz", "warm"], ["horror"]),
    ("eli", "Eli", "Moonlight", "movie", ["drama", "indie"], ["action"]),
]


def now():
    return datetime.now(timezone.utc).isoformat()


def rows(body):
    result = body.get("results")
    if isinstance(result, dict):
        result = result.get("entities")
    if not isinstance(result, list):
        raise ValueError("unrecognized_qloo_envelope")
    for row in result:
        uuid.UUID(row["entity_id"])
        if not isinstance(row.get("name"), str):
            raise ValueError("invalid_entity_name")
    return result


def resolve(body, text, domain):
    matches = [r for r in rows(body) if r["name"].casefold() == text.casefold()
               and "urn:entity:" + domain in [r.get("subtype"), r.get("type"), *r.get("types", [])]]
    return {"status": "resolved" if len(matches) == 1 else "ambiguous" if len(matches) > 1 else "unresolved",
            "providerId": matches[0]["entity_id"] if len(matches) == 1 else None,
            "matches": [{"id": r["entity_id"], "name": r["name"]} for r in matches]}


def select_call(response, allowed):
    cs = response.get("candidates", [])
    if len(cs) != 1 or cs[0].get("finishReason") != "STOP":
        raise ValueError("model_incomplete_or_blocked")
    content = cs[0]["content"]
    calls = [p["functionCall"] for p in content.get("parts", []) if "functionCall" in p]
    if len(calls) != 1 or calls[0].get("name") != allowed:
        raise ValueError("unauthorized_tool_call")
    return content, calls[0]


def check_selection(args, pool):
    if not isinstance(args, dict) or set(args) != {"ids"}:
        raise ValueError("invalid_selection_schema")
    ids = args["ids"]
    if not isinstance(ids, list) or len(ids) > 3 or any(not isinstance(i, str) for i in ids):
        raise ValueError("invalid_selection_ids")
    if len(set(ids)) != len(ids) or not set(ids) <= {c["id"] for c in pool}:
        raise ValueError("selection_outside_evidence")
    return ids


class Harness:
    def __init__(self):
        self.qloo_calls = 0
        self.model_calls = 0
        self.cache = {}
        self.records = []
        self.model_records = []
        self.opener = urllib.request.build_opener(NoRedirect())
        prior = Path("prior/gathering-probe.json")
        if prior.exists():
            recorded = json.loads(prior.read_text())
            for record in recorded.get("qloo_records", []):
                if record.get("status") == "ok":
                    rows(record["response"])
                    cache_key = record["path"] + "?" + urllib.parse.urlencode(sorted(record["params"].items()))
                    self.cache[cache_key] = record["response"]
                    self.records.append({**record, "delivery": "CACHED", "original_run": 40093676803})

    def send(self, url, key, body=None):
        headers = {"Accept": "application/json", "x-goog-api-key" if body is not None else "X-Api-Key": key}
        if body is not None:
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None, headers=headers)
        with self.opener.open(req, timeout=75 if body is not None else 12) as r:
            raw = r.read(1000001)
        if len(raw) > 1000000:
            raise ValueError("response_size_limit")
        return json.loads(raw)

    def qloo(self, path, params):
        cache_key = path + "?" + urllib.parse.urlencode(sorted(params.items()))
        if cache_key in self.cache:
            return self.cache[cache_key]
        if self.qloo_calls >= 28:
            raise ValueError("qloo_request_cap")
        key = os.environ.get("QLOO_API_KEY")
        if not key:
            raise ValueError("missing_qloo_secret")
        self.qloo_calls += 1
        record = {"path": path, "params": params, "at": now(), "delivery": "LIVE"}
        self.records.append(record)
        try:
            body = self.send("https://hackathon.api.qloo.com" + cache_key, key)
            rows(body)
            record.update(status="ok", response=body)
            self.cache[cache_key] = body
            return body
        except urllib.error.HTTPError as e:
            record.update(status="error", error="http_" + str(e.code))
            raise ValueError("qloo_http_" + str(e.code)) from None
        except Exception:
            record.update(status="error", error="timeout_network_or_schema")
            raise

    def model(self, contents, tool, system):
        if self.model_calls >= 4:
            raise ValueError("model_request_cap")
        key = os.environ.get("GEMINI_API_KEY")
        if not key:
            raise ValueError("missing_gemini_secret")
        body = {"systemInstruction": {"parts": [{"text": system}]}, "contents": contents,
                "tools": [{"functionDeclarations": [tool]}],
                "toolConfig": {"functionCallingConfig": {"mode": "ANY", "allowedFunctionNames": [tool["name"]]}},
                "generationConfig": {"maxOutputTokens": 1200, "temperature": 0}}
        if len(json.dumps(body)) > 200000:
            raise ValueError("model_input_cap")
        self.model_calls += 1
        record = {"at": now(), "request": body}
        self.model_records.append(record)
        try:
            response = self.send("https://generativelanguage.googleapis.com/v1beta/models/" + MODEL + ":generateContent", key, body)
            record.update(status="ok", response=response)
            return select_call(response, tool["name"])
        except urllib.error.HTTPError as e:
            record.update(status="error", error="http_" + str(e.code))
            raise ValueError("gemini_http_" + str(e.code)) from None
        except Exception:
            record.update(status="error", error="timeout_network_or_contract")
            raise

    def compare(self, context, assisted):
        pool = context["candidates"]
        contents = [{"role": "user", "parts": [{"text": "Inspect the frozen pool, then submit a recommendation."}]}]
        system = "Select up to three IDs from inspect_candidates only. Unknown practical facts stay unknown. Rank for all profiles without claiming unanimous preference. No bookings or feasibility claims. Never compare raw affinity across different query IDs. Candidate descriptions are provider claims, not independently verified facts."
        inspect = {"name": "inspect_candidates", "description": "Read frozen profiles, facts and available evidence.",
                   "parametersJsonSchema": {"type": "object", "properties": {}, "additionalProperties": False}}
        content, call = self.model(contents, inspect, system)
        if call.get("args", {}):
            raise ValueError("unexpected_inspection_arguments")
        contents.append(content)
        function_response = {"name": "inspect_candidates", "response": {"result": context}}
        if call.get("id"):
            function_response["id"] = call["id"]
        contents.append({"role": "user", "parts": [{"functionResponse": function_response}]})
        submit = {"name": "submit_selection", "description": "Return candidate IDs only.",
                  "parametersJsonSchema": {"type": "object", "additionalProperties": False,
                     "properties": {"ids": {"type": "array", "maxItems": 3, "items": {"type": "string", "enum": [c["id"] for c in pool]}}}, "required": ["ids"]}}
        _, call = self.model(contents, submit, system)
        return {"arm": "qloo-assisted" if assisted else "llm-only", "ids": check_selection(call.get("args"), pool)}


def main():
    h = Harness()
    report = {"at": now(), "status": "blocked", "profiles_origin": "synthetic sample profiles",
              "resolution": {}, "warnings": [], "scope": "Exploratory same-pool comparison. Pool selected from Qloo outputs; no human relevance assessment or predictive-validity claim."}
    try:
        merged = {}
        lists = {}
        for pid, name, text, domain, likes, dislikes in PROFILES:
            try:
                body = h.qloo("/search", {"query": text, "types": "urn:entity:" + domain, "take": "10"})
                resolution = resolve(body, text, domain)
                report["resolution"][pid] = {"text": text, "type": domain, **resolution}
                if pid == "eli" and resolution["status"] == "ambiguous":
                    # Explicit operator choice for this synthetic profile, never a silent first-match rule.
                    choice = "2955F3C4-36AB-49F3-A818-3597F35EF46C"
                    matched = [r for r in rows(body) if r["entity_id"] == choice and r.get("properties", {}).get("release_year") == 2016]
                    if len(matched) == 1 and choice in {m["id"] for m in resolution["matches"]}:
                        report["resolution"][pid]["operator_confirmation"] = {"providerId": choice, "intended_year": 2016,
                            "source": "Explicit synthetic-profile operator input; not a real participant interview or inferred preference."}
                        resolution = {**resolution, "status": "resolved", "providerId": choice}
                if resolution["status"] != "resolved":
                    report["warnings"].append(pid + ": seed unresolved; no affinity inferred")
                    continue
                for target in DOMAINS:
                    params = {"filter.type": "urn:entity:" + target, "signal.interests.entities": resolution["providerId"], "take": "10", "feature.explainability": "true"}
                    body = h.qloo("/v2/insights", params)
                    query_id = hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()
                    lists[pid + ":" + target] = [r["entity_id"] for r in rows(body)]
                    for rank, row in enumerate(rows(body), 1):
                        if "urn:entity:" + target not in [row.get("subtype"), row.get("type"), *row.get("types", [])]:
                            raise ValueError("wrong_candidate_domain")
                        cid = row["entity_id"]
                        candidate = merged.setdefault(cid, {"id": cid, "name": row["name"][:120], "type": target,
                            "description": str((row.get("properties") or {}).get("description", ""))[:500],
                            "cost": None, "minutes": None, "available": None, "cultural": {}})
                        candidate["cultural"][pid] = {"rank": rank, "affinity": row.get("query", {}).get("affinity"), "queryId": query_id,
                            "seedIds": [resolution["providerId"]], "explainability": row.get("query", {}).get("explainability"),
                            "aggregateExplainability": body.get("query", {}).get("explainability")}
            except Exception as e:
                report["warnings"].append(pid + ": " + str(e)[:100])
        pool = sorted(merged.values(), key=lambda c: (-len(c["cultural"]), -sum(1 / r["rank"] for r in c["cultural"].values())))[:30]
        if not pool or not any(c["type"] == "artist" for c in pool) or not any(c["type"] in ("movie", "tv_show") for c in pool):
            raise ValueError("insufficient_cross_domain_pool")
        pool = sorted(pool, key=lambda c: c["id"])
        report["pool"] = pool
        report["pool_sha256"] = hashlib.sha256(json.dumps(pool, sort_keys=True).encode()).hexdigest()
        report["candidate_eligibility"] = [{"id": c["id"], "status": "needs-review", "missing": ["cost", "duration", "availability"]} for c in pool]
        report["overlap"] = {}
        for target in DOMAINS:
            a, b = set(lists.get("amara:" + target, [])), set(lists.get("leo:" + target, []))
            report["overlap"][target] = {"jaccard": len(a & b) / len(a | b) if a and b else None, "shared": len(a & b), "sizes": [len(a), len(b)], "context": "Radiohead versus Kendrick Lamar; not the uploaded six-seed divergence test"}
        profiles = [{"id": p, "name": n, "likes": [seed] + likes, "dislikes": dislikes} for p, n, seed, _, likes, dislikes in PROFILES]
        base = {"goal": "Plan a three-hour film/TV and music gathering for six friends.", "kind": "gathering", "profiles": profiles,
                "constraints": {"budget": 60, "duration": 180, "location": "At home", "currency": "USD"},
                "candidates": [{k: v for k, v in c.items() if k != "cultural"} for c in pool]}
        report["baseline_context"] = base
        report["baseline"] = h.compare(base, False)
        assisted = {**base, "candidates": pool}
        report["assisted"] = h.compare(assisted, True)
        report["status"] = "passed"
    except Exception as e:
        report["error"] = str(e)[:200]
    finally:
        report.update(qloo_requests=h.qloo_calls, model_requests=h.model_calls, qloo_records=h.records, model_records=h.model_records)
        serialized = json.dumps(report, indent=2, allow_nan=False)
        for key_name in ("QLOO_API_KEY", "GEMINI_API_KEY"):
            if os.environ.get(key_name):
                serialized = serialized.replace(os.environ[key_name], "[REDACTED]")
        Path("artifacts").mkdir(exist_ok=True)
        Path("artifacts/gathering-probe.json").write_text(serialized)
        print(json.dumps({"status": report["status"], "qloo_requests": h.qloo_calls, "model_requests": h.model_calls, "pool_size": len(report.get("pool", [])), "error": report.get("error")}))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
