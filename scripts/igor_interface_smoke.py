"""Read-only production interface smoke test. No application API calls."""

import html
import json
import os
import sys
import urllib.request

BASE_URL = os.environ.get("IGOR_URL", "https://igor-production-243e.up.railway.app")
HEADINGS = ("One thing you", "A world it", "A few ways in", "What are you curious about")


def verify(page_source):
    text = html.unescape(page_source)
    return {heading: heading in text for heading in HEADINGS}


def main():
    request = urllib.request.Request(
        BASE_URL,
        headers={"Accept": "text/html", "User-Agent": "Igor-readonly-smoke/1.0"},
    )
    with urllib.request.urlopen(request, timeout=25) as response:
        if response.status != 200:
            raise RuntimeError(f"homepage_http_{response.status}")
        page = response.read(1_500_001)
        if len(page) > 1_500_000:
            raise RuntimeError("page_too_large")
        body = page.decode("utf-8", errors="replace")

    checks = verify(body)
    print(json.dumps({"status": "passed" if all(checks.values()) else "failed", "checks": checks}))
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
