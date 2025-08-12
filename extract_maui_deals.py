import argparse
import json
import re
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

import pandas as pd
from playwright.sync_api import Playwright, TimeoutError as PlaywrightTimeoutError, sync_playwright


DEFAULT_URL = "https://www.costcotravel.com/Vacation-Packages/Hawaii/Maui"
DEFAULT_TIMEOUT_MS = 30_000
REALISTIC_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)


@dataclass
class Deal:
    title: str
    price: Optional[str]
    href: Optional[str]


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Playwright scraper for Maui featured deals")
    parser.add_argument(
        "--url",
        default=DEFAULT_URL,
        help="Page URL to scrape (defaults to Costco Travel Maui Vacation Packages)",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Run browser in headed mode",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT_MS,
        help="Default timeout for operations in milliseconds (default: 30000)",
    )
    parser.add_argument(
        "--debug-selectors",
        action="store_true",
        help=(
            "Pause after navigation to use the Playwright inspector to refine selectors. "
            "Useful when the site changes its DOM."
        ),
    )
    return parser.parse_args(argv)


def launch(playwright: Playwright, headed: bool, timeout_ms: int):
    browser = playwright.chromium.launch(headless=not headed)
    context = browser.new_context(user_agent=REALISTIC_USER_AGENT)
    context.set_default_timeout(timeout_ms)
    page = context.new_page()
    return browser, context, page


def goto_page(page, url: str) -> None:
    page.goto(url, wait_until="networkidle")


def find_featured_section_with_fallback(page) -> Optional[Tuple[object, str]]:
    """
    Try to find the Featured Deals section via robust selectors first.
    Fallback to a text-based heading search and nearest parent container if needed.

    Returns (section_locator, strategy_used) or (None, reason)
    """
    # NOTE: If the site changes, refine the selectors below.
    # Primary robust locator targeting a section with a Featured Deals heading.
    primary_selector = (
        "section:has(h2:has-text('Featured Deals')), "
        "section:has(h3:has-text('Featured Deals'))"
    )
    primary_selector = "".join(primary_selector)
    section = page.locator(primary_selector).first
    try:
        if section.count() > 0:
            return section, "primary-section"
    except PlaywrightTimeoutError:
        pass

    # Fallback: search for any heading containing Featured Deals and climb to a parent container.
    heading = page.locator(
        "h1:has-text('Featured Deals'), h2:has-text('Featured Deals'), "
        "h3:has-text('Featured Deals'), h4:has-text('Featured Deals')"
    )
    heading = page.locator(
        "".join(
            [
                "h1:has-text('Featured Deals'), ",
                "h2:has-text('Featured Deals'), ",
                "h3:has-text('Featured Deals'), ",
                "h4:has-text('Featured Deals')",
            ]
        )
    )

    if heading.count() > 0:
        candidate = heading.first
        # Try nearest section ancestor, then div
        container = candidate.locator("xpath=ancestor::section[1]")
        if container.count() == 0:
            container = candidate.locator("xpath=ancestor::div[1]")
        if container.count() > 0:
            return container.first, "fallback-ancestor"

    return None, "not-found"


def get_cards_from_section(page, section) -> List[object]:
    # Tolerant card selector; prefer items with some heading inside.
    # NOTE: If the site changes, prefer to refine this locator first.
    base_cards = section.locator("article, li, div").filter(has=page.locator("h3, h2"))
    try:
        count = base_cards.count()
    except PlaywrightTimeoutError:
        count = 0
    if count == 0:
        return []
    return [base_cards.nth(i) for i in range(count)]


def extract_deal_from_card(page, card) -> Deal:
    # Title: prefer h3, h2, or something with 'title' in class name
    title_locator = card.locator("h3, h2, [class*='title' i]").first
    title_text = None
    try:
        if title_locator.count() > 0:
            candidate = title_locator.inner_text().strip()
            title_text = re.sub(r"\s+", " ", candidate)
    except Exception:
        title_text = None

    if not title_text:
        # Fallback to trimming the card text if no specific title found
        try:
            raw = card.inner_text()
            title_text = re.sub(r"\s+", " ", raw).strip()
        except Exception:
            title_text = ""

    # Price: search the card inner text for currency-like pattern
    price_text = None
    try:
        inner = card.inner_text()
        match = re.search(r"\$\s?[\d,]+", inner)
        if match:
            price_text = match.group(0)
    except Exception:
        price_text = None

    # Link: first anchor inside the card
    href_value = None
    try:
        anchor = card.locator("a").first
        if anchor.count() > 0:
            href_value = anchor.get_attribute("href")
    except Exception:
        href_value = None

    return Deal(title=title_text or "", price=price_text, href=href_value)


def truncate(text: Optional[str], width: int) -> str:
    if text is None:
        return ""
    if len(text) <= width:
        return text
    if width <= 1:
        return text[:width]
    return text[: width - 1] + "…"


def print_table(deals: List[Deal]) -> None:
    # Pretty console printout
    idx_w = 3
    title_w = 60
    price_w = 12
    link_w = 60

    header = f"{'#':<{idx_w}}  {'Title':<{title_w}}  {'Price':<{price_w}}  {'Link':<{link_w}}"
    sep = "-" * len(header)
    print(header)
    print(sep)
    for i, deal in enumerate(deals, start=1):
        title = truncate(deal.title, title_w)
        price = truncate(deal.price or "", price_w)
        link = truncate(deal.href or "", link_w)
        print(f"{i:<{idx_w}}  {title:<{title_w}}  {price:<{price_w}}  {link:<{link_w}}")


def save_outputs(deals: List[Deal]) -> Tuple[Path, Path]:
    json_path = Path("featured_deals.json")
    csv_path = Path("featured_deals.csv")

    with json_path.open("w", encoding="utf-8") as f:
        json.dump([asdict(d) for d in deals], f, ensure_ascii=False, indent=2)

    df = pd.DataFrame([asdict(d) for d in deals])
    df.to_csv(csv_path, index=False)

    return json_path, csv_path


def scrape(url: str, headed: bool, timeout_ms: int, debug_selectors: bool) -> List[Deal]:
    with sync_playwright() as playwright:
        browser = context = page = None
        try:
            browser, context, page = launch(playwright, headed=headed, timeout_ms=timeout_ms)
            goto_page(page, url)

            if debug_selectors:
                # Allow interactive inspection to refine selectors if the site changes
                page.pause()

            # Retry featured deals extraction up to 3 attempts total
            last_reason = ""
            for attempt in range(3):
                try:
                    found = False
                    section, reason = find_featured_section_with_fallback(page)
                    last_reason = reason
                    if section is not None:
                        # Wait for section to be attached/visible-ish
                        try:
                            section.wait_for(state="attached")
                        except Exception:
                            pass

                        cards = get_cards_from_section(page, section)

                        print(f"Found {len(cards)} potential cards (attempt {attempt + 1}/3)")
                        if len(cards) == 0:
                            if attempt == 0:
                                print(
                                    "No cards detected. Hint: try --headed and scroll. "
                                    "Attempting to scroll and re-check..."
                                )
                                try:
                                    page.mouse.wheel(0, 1500)
                                except Exception:
                                    pass
                                # Re-evaluate after scroll
                                cards = get_cards_from_section(page, section)
                                print(f"After scroll, found {len(cards)} cards")

                        if len(cards) > 0:
                            deals = [extract_deal_from_card(page, c) for c in cards]
                            return deals

                    # If we did not return yet, give it a brief pause and retry
                    page.wait_for_timeout(800)
                except Exception as e:
                    last_reason = f"exception: {e}"
                    page.wait_for_timeout(800)

            # If we exhausted retries, consider as failure
            raise RuntimeError(
                f"Failed to locate Featured Deals section or cards after retries (last_reason={last_reason})."
            )
        except Exception:
            # On failure, capture a screenshot for troubleshooting
            try:
                error_path = "error.png"
                if page is not None:
                    page.screenshot(path=error_path, full_page=True)
                print(f"Saved error screenshot to {error_path}")
            except Exception:
                pass
            raise
        finally:
            try:
                if context is not None:
                    context.close()
            except Exception:
                pass
            try:
                if browser is not None:
                    browser.close()
            except Exception:
                pass


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    try:
        deals = scrape(
            url=args.url,
            headed=args.headed,
            timeout_ms=args.timeout,
            debug_selectors=args.debug_selectors,
        )
        if not deals:
            print("No deals found.")
            return 1

        print_table(deals)
        json_path, csv_path = save_outputs(deals)
        print(f"Saved {len(deals)} deals to {json_path} and {csv_path}")
        return 0
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())