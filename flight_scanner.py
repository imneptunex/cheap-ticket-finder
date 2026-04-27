#!/usr/bin/env python3

import asyncio
import subprocess
import logging
import re
import random
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

DESTINATIONS = [
    {"name": "Seoul",    "en": "Seoul"},
    {"name": "Tokyo",    "en": "Tokyo"},
    {"name": "Beijing",  "en": "Beijing"},
    {"name": "Shanghai", "en": "Shanghai"},
]

MAX_PRICE           = 29_000
CHECK_INTERVAL_MINS = 20

LOG_FILE = Path(__file__).parent / "flight_scanner.log"

log = logging.getLogger("flights")
log.setLevel(logging.INFO)
_fmt = logging.Formatter("%(asctime)s  %(levelname)-8s  %(message)s")
_fh  = logging.FileHandler(LOG_FILE, encoding="utf-8")
_fh.setFormatter(_fmt)
_sh  = logging.StreamHandler()
_sh.setFormatter(_fmt)
log.addHandler(_fh)
log.addHandler(_sh)


def notify(title: str, body: str) -> None:
    safe_title = title.replace('"', '\\"')
    safe_body  = body.replace('"', '\\"')
    subprocess.run(
        ["osascript", "-e",
         f'display notification "{safe_body}" with title "{safe_title}" sound name "Glass"'],
        check=False,
    )
    log.info("NOTIFICATION | %s | %s", title, body)


async def _dismiss_consent(page) -> None:
    for label in ("Accept all", "I agree", "Tümünü kabul et"):
        try:
            btn = page.get_by_role("button", name=re.compile(label, re.I))
            if await btn.count() and await btn.first.is_visible():
                await btn.first.click()
                await asyncio.sleep(1)
                return
        except Exception:
            pass


def _parse_date(aria: str) -> str:
    m = re.search(r'Leaves .+? on (\w+, \w+ \d+)', aria)
    return m.group(1) if m else "?"


def _parse_price(aria: str) -> int | None:
    m = re.search(r'(\d+)\s*Turkish Lira', aria, re.IGNORECASE)
    return int(m.group(1)) if m else None


async def scan_destination(browser, dest: dict) -> list[tuple[str, int]]:
    context = await browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        locale="en-US",
        timezone_id="Europe/Istanbul",
        viewport={"width": 1440, "height": 900},
    )
    page = await context.new_page()
    deals: list[tuple[str, int]] = []

    try:
        url = (
            "https://www.google.com/travel/flights"
            f"?q=Flights+from+Istanbul+to+{dest['en']}"
            "&hl=en&curr=TRY"
        )
        log.info("Scanning: Istanbul -> %s", dest["name"])
        await page.goto(url, wait_until="domcontentloaded", timeout=50_000)
        await asyncio.sleep(random.uniform(3, 5))
        await _dismiss_consent(page)
        await asyncio.sleep(1)

        cards = await page.query_selector_all('[aria-label*="Turkish Lira"]')

        seen: set[tuple[str, int]] = set()
        all_found: list[tuple[str, int]] = []

        for card in cards:
            aria = await card.get_attribute("aria-label") or ""
            if "Leaves" not in aria:
                continue

            price = _parse_price(aria)
            date  = _parse_date(aria)
            if price and (date, price) not in seen:
                seen.add((date, price))
                all_found.append((date, price))

        if all_found:
            cheapest = min(all_found, key=lambda x: x[1])
            log.info("  Cheapest: %s – TL %s", cheapest[0], f"{cheapest[1]:,}")
        else:
            html = await page.content()
            for raw in re.findall(r'₺(\d{1,3}(?:\.\d{3})+)', html):
                v = int(raw.replace('.', ''))
                if 5_000 < v <= MAX_PRICE:
                    all_found.append(("unknown date", v))
                    log.info("  Price (no date): TL %s", f"{v:,}")
            if not all_found:
                log.info("  No prices in target range")

        deals = [(d, p) for d, p in all_found if p <= MAX_PRICE]
        if deals:
            log.info("  IN RANGE: %s", [(d, f"TL {p:,}") for d, p in deals])

    except PlaywrightTimeout:
        log.warning("Timeout: Istanbul -> %s", dest["name"])
    except Exception as e:
        log.error("Error (%s): %s", dest["name"], e)
    finally:
        await context.close()

    return deals


async def run_scan(browser) -> None:
    log.info("=== Scan started: %s ===", datetime.now().strftime("%Y-%m-%d %H:%M"))
    all_deals: list[tuple[str, str, int]] = []

    for dest in DESTINATIONS:
        pairs = await scan_destination(browser, dest)
        for date, price in pairs:
            all_deals.append((dest["name"], date, price))
        await asyncio.sleep(random.uniform(5, 12))

    if all_deals:
        grouped: dict[str, tuple[str, int]] = {}
        for dest_name, date, price in all_deals:
            if dest_name not in grouped or price < grouped[dest_name][1]:
                grouped[dest_name] = (date, price)

        for dest_name, (date, price) in grouped.items():
            date_str = f"{date} - " if date != "unknown date" else ""
            notify(
                f"Cheap Flight: {dest_name}!",
                f"{date_str}TL {price:,}",
            )
        log.info("Deals found for %d destination(s), notifications sent.", len(grouped))
    else:
        log.info("No deals found. Next scan in %d minutes.", CHECK_INTERVAL_MINS)


async def main() -> None:
    log.info("Flight scanner started. Max price: TL %s | Interval: every %d minutes",
             f"{MAX_PRICE:,}", CHECK_INTERVAL_MINS)
    notify("Flight Scanner Started", f"Checking every {CHECK_INTERVAL_MINS} min. Max: TL {MAX_PRICE:,}")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            while True:
                await run_scan(browser)
                await asyncio.sleep(CHECK_INTERVAL_MINS * 60)
        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
