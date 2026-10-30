#!/usr/bin/env python3
"""Ephemeral sanitization of Igor's real history; NEVER pushes or uploads source."""
from __future__ import annotations
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

BRANCH = "design/reference-contract-foundation-20261030"
REMOVED = [
    "docs/intelligence/", "docs/evidence/", "docs/product-intelligence.md",
    "docs/flagship-live-browser-results.json", "tests/fixtures/",
    "tests/recorded/", "tests/recordings/", "artifacts/", "reports/",
    ".igor/", ".github/workflows/", "test-results/", "playwright-report/",
    ".env", ".env.local", ".env.development", ".env.production",
]
REMOVED_REGEX = [
    r"(^|/)\.env\.(?!example$)[^/]+$",
    r"(^|/)[^/]+\.(pem|p12|pfx|key|sqlite|db|bak)$",
    r"(^|/)id_(rsa|ed25519)(\.pub)?$",
    r"(^|/)[^/]+\.(log|zip|tgz)$",
]

def call(args: list[str], cwd: Path | None = None) -> str:
    proc = subprocess.run(args, cwd=cwd, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, text=True)
    if proc.returncode:
        raise RuntimeError(f"Command failed: {args[0]} (exit {proc.returncode})")
    return proc.stdout.strip()

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--expected-sha", required=True)
    ap.add_argument("--report", required=True)
    args = ap.parse_args()
    source, target, report = (Path(v).resolve() for v in
                              (args.source, args.output, args.report))
    if not re.fullmatch(r"[a-f0-9]{40}", args.expected_sha):
        raise RuntimeError("Invalid expected source commit SHA")
    if not (source / ".git").exists() or target.exists() or report.exists():
        raise RuntimeError("Missing source or nonempty output destination")
    if source in target.parents or source in report.parents or target in report.parents:
        raise RuntimeError("Source/output/report directories overlap")
    original = call(["git", "rev-parse", "HEAD"], source)
    if original != args.expected_sha:
        raise RuntimeError("The private branch has moved; review before rerunning")
    # Construct a temporary branch at the PINNED commit in this disposable
    # runner checkout. Never follow a live branch head that can move mid-run.
    pinned_branch = "igor-sanitization-pinned"
    call(["git", "branch", "-f", pinned_branch, original], source)
    # file:// avoids --local copying; --single-branch retains this commit's
    # genuine ancestry but excludes unrelated private branch tips and tags.
    call(["git", "clone", "--no-tags", "--single-branch", "--branch",
          pinned_branch, source.as_uri(), str(target)])
    if call(["git", "rev-parse", "HEAD"], target) != original:
        raise RuntimeError("Local copied branch does not match pinned commit")
    count_before = int(call(["git", "rev-list", "--count", "HEAD"], target))
    filter_args = ["git", "filter-repo", "--force", "--invert-paths"]
    for path in REMOVED:
        filter_args.extend(["--path", path])
    for pattern in REMOVED_REGEX:
        filter_args.extend(["--path-regex", pattern])
    call(filter_args, target)
    call(["git", "branch", "-M", "main"], target)
    if call(["git", "remote"], target):
        call(["git", "remote", "remove", "origin"], target)
    if call(["git", "remote"], target):
        raise RuntimeError("Sanitized repository must have no Git remotes")
    for path in REMOVED:
        if call(["git", "log", "--all", "--format=", "--name-only", "--", path], target):
            raise RuntimeError("A prohibited historical path remains")
    names = call(["git", "log", "--all", "--format=", "--name-only"], target)
    for name in names.splitlines():
        if any(re.search(pattern, name) for pattern in REMOVED_REGEX):
            raise RuntimeError("A prohibited filename pattern remains")
    count_after = int(call(["git", "rev-list", "--count", "HEAD"], target))
    if count_after < 2:
        raise RuntimeError("The history unexpectedly collapsed to one commit")
    authors = call(["git", "log", "--format=%ae", "HEAD"], target)
    summary = {
        "source_revision": original,
        "sanitized_revision": call(["git", "rev-parse", "HEAD"], target),
        "original_commit_count": count_before,
        "sanitized_commit_count": count_after,
        "commit_dates_preserved": True,
        "unique_author_email_count": len(set(authors.splitlines())),
        "publishing_authorized": False,
        "private_source_uploaded": False,
    }
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"ORIGINAL_COMMITS={count_before}")
    print(f"SANITIZED_COMMITS={count_after}")
    print("EPHEMERAL_CLEAN_HISTORY_CREATED=true")
    print("NO_PUBLIC_SOURCE_ARTIFACT=true")

if __name__ == "__main__":
    try:
        main()
    except RuntimeError as error:
        print(f"::error::{error}", file=sys.stderr)
        raise SystemExit(1)
