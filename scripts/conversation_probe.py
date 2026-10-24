"""Public-safe natural correction contract check. Does not import Igor or call Qloo."""
import json
import os
from pathlib import Path
from gathering_probe import Harness, now


def object_schema(properties, required):
    return {"type": "object", "properties": properties, "required": required, "additionalProperties": False}


def main():
    h = Harness()
    report = {"at": now(), "status": "blocked", "scope": "Fresh Gemini extraction of four synthetic corrections. Not execution of the private application.", "cases": []}
    try:
        prior = json.loads(Path("prior/gathering-probe.json").read_text())
        candidates = [{"id": c["id"], "name": c["name"], "type": c["type"]} for c in prior["pool"]]
        s = {"type": "string"}
        actions = [
            object_schema({"kind": {"const": "resolve"}, "entity": s, "choice": s}, ["kind", "entity", "choice"]),
            object_schema({"kind": {"const": "facts"}, "candidate": s, "cost": {"type": ["number", "null"]}, "duration": {"type": ["integer", "null"]}, "available": {"type": ["boolean", "null"]}}, ["kind", "candidate"]),
            object_schema({"kind": {"const": "preference"}, "participant": s, "value": s, "polarity": {"enum": ["like", "dislike", "unknown", "not-now"]}, "entityType": {"enum": ["movie", "artist", "tv_show"]}}, ["kind", "participant", "value", "polarity"]),
            object_schema({"kind": {"const": "artifact"}, "artifactId": {"enum": ["main", "invitation"]}, "content": s}, ["kind", "artifactId", "content"]),
        ]
        schema = object_schema({"supported": {"type": "boolean"}, "intent": {"enum": ["goal", "revision", "unsupported"]}, "kind": {"enum": ["gathering", "creative", "discovery"]}, "goal": s,
            "budget": {"type": ["number", "null"]}, "duration": {"type": ["integer", "null"]}, "wording": {"type": ["string", "null"]},
            "actions": {"type": ["array", "null"], "maxItems": 8, "items": {"anyOf": actions}}}, ["supported", "intent", "kind", "goal"])
        tool = {"name": "update_brief", "description": "Extract supported goal or explicit correction without inventing facts.", "parametersJsonSchema": schema}
        profiles = prior["baseline_context"]["profiles"]
        context = {"goal": "Film and music gathering", "kind": "gathering", "participants": profiles, "candidates": candidates,
            "entities": [{"original": "Moonlight", "choices": [{"id": "2955F3C4-36AB-49F3-A818-3597F35EF46C", "name": "Moonlight", "releaseYear": 2016}, {"id": "75AC4FBE-D773-4604-AB08-A637D50BCFDC", "name": "Moonlight", "releaseYear": 2002}]}],
            "artifacts": [{"id": "invitation", "content": "Join the gathering."}]}
        system = "Use update_brief only. Extract corrections using allowed actions and supplied context. Do not invent practical facts. Keep all other state unchanged. A replaced like becomes unknown, not dislike. Unknown, not-now and dislike differ. Preserve participant attribution. Refer to candidate names exactly as supplied. A year may identify a unique offered film. Invitation wording goes in wording or an artifact action. Context: " + json.dumps(context)
        for text in ["Use Moonlight from 2016.", "For Children of Men: cost $5, duration 80 minutes, access confirmed.", "Replace Amara's Radiohead with Kendrick Lamar.", "Invitation: Bring your curiosity."]:
            _, call = h.model([{"role": "user", "parts": [{"text": text}]}], tool, system)
            args = call.get("args", {})
            if args.get("supported") is not True or args.get("intent") != "revision":
                raise ValueError("invalid_revision_classification")
            report["cases"].append({"text": text, "interpretation": args})
        report["status"] = "passed"
    except Exception as e:
        report["error"] = str(e)[:180]
    report.update(qloo_requests=h.qloo_calls, model_requests=h.model_calls, model_records=h.model_records)
    serialized = json.dumps(report, indent=2)
    for key in ("GEMINI_API_KEY", "QLOO_API_KEY"):
        if os.environ.get(key): serialized = serialized.replace(os.environ[key], "[REDACTED]")
    Path("artifacts").mkdir(exist_ok=True)
    Path("artifacts/conversation-probe.json").write_text(serialized)
    print(json.dumps({"status": report["status"], "model_requests": h.model_calls, "qloo_requests": h.qloo_calls, "completed_cases": len(report["cases"])}))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
