import argparse
from typing import Optional

from playwright.sync_api import sync_playwright


def run_scraper(is_headed: bool) -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=not is_headed)
        page = browser.new_page()
        page.goto("https://example.com", wait_until="domcontentloaded")
        print(f"Page title: {page.title()}")
        browser.close()


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Playwright scraper for Maui deals (placeholder)")
    parser.add_argument("--headed", action="store_true", help="Run browser in headed mode")
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = parse_args()
    run_scraper(is_headed=args.headed)