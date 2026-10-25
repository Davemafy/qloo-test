"""Read-only visual smoke checks against Igor's public homepage."""

import json
from pathlib import Path
from playwright.sync_api import sync_playwright

URL = "https://igor-production-243e.up.railway.app"
ARTIFACTS = Path("artifacts/igor-browser")


def check_page(browser, width, height, label, mobile=False):
    page = browser.new_page(viewport={"width": width, "height": height}, device_scale_factor=1, is_mobile=mobile, has_touch=mobile)
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)[:200]))
    response = page.goto(URL, wait_until="domcontentloaded", timeout=35000)
    page.locator("#ig-heading").wait_for(timeout=25000)
    page.wait_for_timeout(1100)
    data = page.evaluate("""() => ({
        documentWidth: document.documentElement.scrollWidth,
        windowWidth: window.innerWidth,
        title: document.querySelector('#ig-heading')?.textContent,
        mobileNavVisible: getComputedStyle(document.querySelector('.ig-mobile-nav')).display !== 'none',
        hasPrompt: Boolean(document.querySelector('#ig-home-prompt'))
    })""")
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(ARTIFACTS / f"{label}.png"), full_page=True)
    page.close()

    valid = (
        response is not None
        and response.status == 200
        and data["documentWidth"] <= data["windowWidth"] + 1
        and data["hasPrompt"]
        and data["mobileNavVisible"] == mobile
        and not errors
    )
    return {"passed": bool(valid), "status": response.status if response else None, **data, "errors": errors}


def main():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        results = {
            "desktop": check_page(browser, 1364, 900, "desktop"),
            "mobile": check_page(browser, 390, 844, "mobile", mobile=True),
        }
        browser.close()
    print(json.dumps(results, indent=2))
    return 0 if all(result["passed"] for result in results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())