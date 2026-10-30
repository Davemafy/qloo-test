#!/usr/bin/env python3
"""Emit bounded, source-free diagnostics for private Ighor Actions checks."""
from __future__ import annotations
import pathlib
import re
import sys

label, filename = sys.argv[1:]
data = pathlib.Path(filename).read_text(errors="replace")
data = re.sub(r"\x1b\[[0-9;]*m", "", data)

if label == "Formatting":
    paths = []
    for path in re.findall(r"(?m)^\[warn\]\s+([^\n]+)", data):
        if path.startswith(("src/", "tests/", "docs/", "scripts/", "public/")) or path.endswith((".json", ".md", ".mts", ".mjs")):
            paths.append(path.strip())
    print("FORMATTING_FILE_COUNT", len(paths))
    for path in paths[:80]:
        print("FORMATTING_FILE", path[:160])
elif label == "ESLint":
    print("ESLINT_ERROR_LINES", len(re.findall(r"(?m)^\s*\d+:\d+\s+error\b", data)))
    print("ESLINT_WARNING_LINES", len(re.findall(r"(?m)^\s*\d+:\d+\s+warning\b", data)))
    paths = []
    for line in data.splitlines():
        stripped = line.strip()
        if re.fullmatch(r"(?:/[^\s]+/)?(?:src|tests|scripts)/[A-Za-z0-9_./-]+\.(?:ts|tsx|mts|mjs)", stripped):
            paths.append(stripped.split("private-ighor/")[-1])
    print("ESLINT_FILE_COUNT", len(paths))
    for path in paths[:65]:
        print("ESLINT_FILE", path[:150])
    rules = {}
    for rule in re.findall(r"(?m)^\s*\d+:\d+\s+(?:error|warning)\s+.*?\s+([a-z@][a-z0-9/_-]+)\s*$", data):
        rules[rule] = rules.get(rule, 0) + 1
    for rule, count in sorted(rules.items(), key=lambda p: -p[1])[:15]:
        print("ESLINT_RULE", rule, count)
elif label == "Home-Discover-mobile-browser":
    matches = re.findall(r"(?m)^\s*\d+\)\s+tests/browser/[^:\n]+:\d+:\d+\s+.+$", data)
    print("BROWSER_FAILURE_COUNT", len(matches))
    for match in matches[:20]:
        # Match only test source names, line numbers and assertion titles,
        # never screenshot diffs, DOM/body text, full URLs or provider bodies.
        print("BROWSER_FAIL", match.strip()[:185])
    print("BROWSER_TESTS_PASSED",
          (re.findall(r"(?m)^\s*(\d+)\s+passed\b", data) or ["unknown"])[-1])
    print("BROWSER_TESTS_FAILED",
          (re.findall(r"(?m)^\s*(\d+)\s+failed\b", data) or ["unknown"])[-1])
    sites = re.findall(r"at [^\n]*reference-integrated\.e2e\.ts:(\d+):(\d+)", data)
    for line,col in sites[:8]:
        print("BROWSER_ASSERTION_SITE", line, col)
    for token in ("visible", "hidden", "true", "false", "toHaveCount", "toBe", "toBeVisible"):
        if "Expected: " + token in data:
            print("BROWSER_EXPECTED", token)
        if "Received: " + token in data:
            print("BROWSER_RECEIVED", token)

else:
    print("CHECK_DIAGNOSTIC", label, "failure details withheld")
