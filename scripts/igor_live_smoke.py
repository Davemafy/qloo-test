"""Check the deployed Igor app without importing its private source or credentials."""

import http.cookiejar
import json
import os
from pathlib import Path
import sys
import urllib.error
import urllib.request

BASE_URL = os.environ.get("IGOR_URL", "https://igor-production-243e.up.railway.app").rstrip("/")
REPORT_PATH = Path("artifacts/igor-live-smoke.json")
MAX_RESPONSE_BYTES = 2_000_000


def get_response(opener, path, *, payload=None, timeout=25):
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(
        BASE_URL + path,
        data=data,
        method="POST" if payload is not None else "GET",
        headers={
            "Accept": "application/json, text/event-stream, text/html",
            **({"Content-Type": "application/json", "Origin": BASE_URL} if data else {}),
        },
    )

    with opener.open(request, timeout=timeout) as response:
        content = response.read(MAX_RESPONSE_BYTES + 1)
        if len(content) > MAX_RESPONSE_BYTES:
            raise ValueError("response_too_large")

        return response.status, content.decode("utf-8", errors="replace")


def last_turn_event(response_text):
    events = []
    for line in response_text.splitlines():
        if line.startswith("data: "):
            event = json.loads(line[6:])
            if isinstance(event, dict) and event.get("type") in {"done", "error"}:
                events.append(event)

    if not events:
        raise ValueError("turn_completed_without_final_event")

    return events[-1]


def provider_summary(task, action_name):
    traces = [entry for entry in task.get("trace", []) if entry.get("action") == action_name]
    return {
        "successful_action": any(entry.get("requests", 0) > 0 for entry in traces),
        "requests": sum(entry.get("requests", 0) for entry in traces),
        "action_present": bool(traces),
    }


def check_model(task):
    result = provider_summary(task, "model.interpret")
    failures = provider_summary(task, "model.interpret.error")
    result["configured_adapter"] = task.get("modelMode") == "tool-calling"
    result["failed_interpretation"] = failures["action_present"]
    result["status"] = (
        "called" if result["configured_adapter"] and result["successful_action"]
        else "error" if failures["action_present"]
        else "scripted_or_unconfirmed"
    )
    return result


def check_qloo(task):
    cultural = [record for record in task.get("evidence", []) if record.get("kind") == "cultural"]
    live_count = sum(record.get("delivery") == "LIVE" for record in cultural)
    cached_count = sum(record.get("delivery") == "CACHED" for record in cultural)
    discovery = [entry for entry in task.get("trace", []) if entry.get("action", "").startswith("cultural.")]
    return {
        "status": "live" if live_count else "cached" if cached_count else "no_cultural_evidence",
        "live_evidence": live_count,
        "cached_evidence": cached_count,
        "discovery_requests": sum(entry.get("requests", 0) for entry in discovery),
        "task_status": task.get("status"),
        "has_error": bool(task.get("error")),
    }


def execute():
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()),
    )
    report = {"target": BASE_URL, "checks": {}, "conclusion": "incomplete"}

    try:
        status, page = get_response(opener, "/")
        report["checks"]["homepage"] = {
            "http_status": status,
            "igor_brand_visible": "igor" in page.lower(),
        }
        if status != 200 or "igor" not in page.lower():
            raise ValueError("homepage_missing_igor_brand")

        status, body = get_response(opener, "/api/tasks", payload={})
        task = json.loads(body)
        task_id = task.get("id")
        version = task.get("brief", {}).get("version")
        report["checks"]["workspace"] = {
            "http_status": status,
            "created": isinstance(task_id, str) and isinstance(version, int),
            "mode": task.get("mode"),
        }
        if not report["checks"]["workspace"]["created"]:
            raise ValueError("workspace_creation_failed")

        _, result = get_response(
            opener,
            f"/api/tasks/{task_id}/turn",
            payload={"type": "message", "text": "Budget $35.", "version": version},
            timeout=140,
        )
        model_event = last_turn_event(result)
        if model_event.get("type") != "done":
            raise ValueError("model_turn_error")
        task = model_event["task"]
        report["checks"]["model"] = check_model(task)

        _, result = get_response(
            opener,
            f"/api/tasks/{task_id}/turn",
            payload={
                "type": "personal-profile",
                "name": "Test profile",
                "artist": "Massive Attack",
                "version": task["brief"]["version"],
            },
            timeout=140,
        )
        qloo_event = last_turn_event(result)
        if qloo_event.get("type") != "done":
            raise ValueError("discovery_turn_error")
        task = qloo_event["task"]
        report["checks"]["qloo"] = check_qloo(task)
        # A completed SSE turn is not proof that the independent workspace
        # read is persisted. Reopen it using the original session cookie.
        read_status, saved_body = get_response(opener, f"/api/tasks/{task_id}")
        reopened = json.loads(saved_body)
        same_id = reopened.get("id") == task_id
        same_version = reopened.get("brief", {}).get("version") == task.get(
            "brief", {}
        ).get("version")
        original_evidence = {
            record.get("id") for record in task.get("evidence", [])
            if isinstance(record.get("id"), str)
        }
        reopened_evidence = {
            record.get("id") for record in reopened.get("evidence", [])
            if isinstance(record.get("id"), str)
        }
        persisted = (
            read_status == 200 and same_id and same_version
            and original_evidence.issubset(reopened_evidence)
        )
        report["checks"]["persistence"] = {
            "http_status": read_status,
            "same_workspace_id": same_id,
            "same_version": same_version,
            "evidence_preserved": original_evidence.issubset(reopened_evidence),
        }
        if not persisted:
            raise ValueError("workspace_reopen_not_persisted")
        report["conclusion"] = (
            "passed" if report["checks"]["model"]["status"] == "called"
            and report["checks"]["qloo"]["status"] == "live"
            else "provider_checks_incomplete"
        )
    except (ValueError, KeyError, OSError, urllib.error.URLError, json.JSONDecodeError) as error:
        report["conclusion"] = "incomplete"
        report["failure_type"] = type(error).__name__
        report["failure_step"] = (
            "qloo" if "model" in report["checks"]
            else "model" if "workspace" in report["checks"]
            else "workspace" if "homepage" in report["checks"]
            else "homepage"
        )
    finally:
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report, indent=2))

    return 0 if report["conclusion"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(execute())
