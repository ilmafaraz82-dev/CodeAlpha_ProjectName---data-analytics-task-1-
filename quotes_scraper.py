"""
quotes_scraper.py
─────────────────
Scrapes all quotes from https://quotes.toscrape.com/
across every paginated page, then saves results to quotes.csv.

Setup
-----
    pip install requests beautifulsoup4

Usage
-----
    python quotes_scraper.py                        # default output: quotes.csv
    python quotes_scraper.py --output my_file.csv   # custom output path
    python quotes_scraper.py --delay 3              # 3-second delay between pages

Author : FitTrack Engineer
Python : 3.8+
"""

import argparse
import csv
import logging
import time
import urllib.robotparser
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Generator

import requests
from bs4 import BeautifulSoup

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

BASE_URL    = "https://quotes.toscrape.com"
ROBOTS_URL  = f"{BASE_URL}/robots.txt"
START_PATH  = "/page/1/"
DEFAULT_OUT = "quotes.csv"
DEFAULT_DELAY = 2  # seconds between requests

# Realistic browser headers to avoid being blocked
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/webp,*/*;q=0.8"
    ),
    "Connection": "keep-alive",
}


# ─────────────────────────────────────────────────────────────────────────────
# Data model
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Quote:
    """Represents a single scraped quote."""
    text:   str
    author: str


# ─────────────────────────────────────────────────────────────────────────────
# Logging setup
# ─────────────────────────────────────────────────────────────────────────────

def setup_logging() -> logging.Logger:
    """
    Configure a named logger that writes to both the console and a log file.
    Returns the logger instance.
    """
    logger = logging.getLogger("quotes_scraper")
    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s  %(message)s",
        datefmt="%H:%M:%S",
    )

    # Console handler — INFO and above
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)

    # File handler — DEBUG and above (full detail)
    fh = logging.FileHandler("scraper.log", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)

    logger.addHandler(ch)
    logger.addHandler(fh)
    return logger


log = setup_logging()


# ─────────────────────────────────────────────────────────────────────────────
# robots.txt check
# ─────────────────────────────────────────────────────────────────────────────

def is_scraping_allowed(url: str) -> bool:
    """
    Parse the site's robots.txt and verify our User-Agent is permitted
    to fetch `url`.  Returns True if allowed (or if robots.txt is
    unreachable), False if explicitly disallowed.
    """
    rp = urllib.robotparser.RobotFileParser()
    rp.set_url(ROBOTS_URL)
    try:
        rp.read()
        allowed = rp.can_fetch(HEADERS["User-Agent"], url)
        log.debug("robots.txt check for %s → %s", url, "allowed" if allowed else "DENIED")
        return allowed
    except Exception as exc:
        # Can't reach robots.txt — proceed cautiously but don't block
        log.warning("Could not read robots.txt (%s). Proceeding anyway.", exc)
        return True


# ─────────────────────────────────────────────────────────────────────────────
# HTTP helper
# ─────────────────────────────────────────────────────────────────────────────

def fetch_page(session: requests.Session, url: str) -> BeautifulSoup | None:
    """
    Fetch a single page and return a BeautifulSoup object.
    Returns None on any network or HTTP error so the caller can skip gracefully.

    Args:
        session: shared requests.Session (reuses TCP connections + cookies)
        url:     absolute URL to fetch
    """
    try:
        log.debug("GET %s", url)
        response = session.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        log.debug("Response %s  (%d bytes)", response.status_code, len(response.content))
        return BeautifulSoup(response.text, "html.parser")

    except requests.exceptions.HTTPError as exc:
        log.error("HTTP error for %s: %s", url, exc)
    except requests.exceptions.ConnectionError:
        log.error("Connection error for %s — check your internet.", url)
    except requests.exceptions.Timeout:
        log.error("Request timed out for %s.", url)
    except requests.exceptions.RequestException as exc:
        log.error("Unexpected request error for %s: %s", url, exc)

    return None


# ─────────────────────────────────────────────────────────────────────────────
# Parsing
# ─────────────────────────────────────────────────────────────────────────────

def parse_quotes(soup: BeautifulSoup) -> list[Quote]:
    """
    Extract all Quote objects from a parsed page.
    Missing text or author fields are replaced with empty strings so a
    single bad quote never crashes the whole run.

    Args:
        soup: parsed HTML of one paginated page
    Returns:
        List of Quote dataclass instances (may be empty).
    """
    quotes: list[Quote] = []

    quote_divs = soup.select("div.quote")
    log.debug("Found %d quote blocks on this page.", len(quote_divs))

    for div in quote_divs:
        # ── Quote text ──────────────────────────────────────────────────────
        text_tag = div.select_one("span.text")
        if text_tag:
            # Strip the decorative curly-quote characters (U+201C / U+201D)
            text = text_tag.get_text(strip=True).strip("\u201c\u201d")
        else:
            log.warning("Quote block missing <span class='text'>. Skipping text.")
            text = ""

        # ── Author ──────────────────────────────────────────────────────────
        author_tag = div.select_one("small.author")
        if author_tag:
            author = author_tag.get_text(strip=True)
        else:
            log.warning("Quote block missing <small class='author'>. Skipping author.")
            author = ""

        # Only add if we have at least some data
        if text or author:
            quotes.append(Quote(text=text, author=author))

    return quotes


def get_next_page_url(soup: BeautifulSoup) -> str | None:
    """
    Look for a 'Next →' pagination link and return its absolute URL.
    Returns None when we're on the last page.

    Args:
        soup: parsed HTML of the current page
    """
    next_btn = soup.select_one("li.next > a")
    if next_btn and next_btn.get("href"):
        return BASE_URL + next_btn["href"]
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Pagination driver  (generator — yields one page's quotes at a time)
# ─────────────────────────────────────────────────────────────────────────────

def scrape_all_pages(
    delay: float = DEFAULT_DELAY,
) -> Generator[list[Quote], None, None]:
    """
    Walk every paginated page of quotes.toscrape.com and yield the list of
    Quote objects found on each page.

    Args:
        delay: seconds to sleep between consecutive HTTP requests
    Yields:
        list[Quote] — quotes from one page (can be empty on parse failure)
    """
    start_url = BASE_URL + START_PATH

    # ── robots.txt gate ─────────────────────────────────────────────────────
    if not is_scraping_allowed(start_url):
        log.error("robots.txt disallows scraping %s. Aborting.", start_url)
        return

    with requests.Session() as session:
        current_url: str | None = start_url
        page_num = 0

        while current_url:
            page_num += 1
            log.info("⏳  Fetching page %d  →  %s", page_num, current_url)

            soup = fetch_page(session, current_url)
            if soup is None:
                log.error("Failed to fetch page %d. Stopping pagination.", page_num)
                break

            quotes = parse_quotes(soup)
            log.info("✅  Page %d: extracted %d quote(s).", page_num, len(quotes))
            yield quotes

            # Advance to next page (None means we've reached the last page)
            current_url = get_next_page_url(soup)

            if current_url:
                log.debug("Sleeping %.1f s before next request…", delay)
                time.sleep(delay)

    log.info("🏁  Pagination complete. Total pages scraped: %d", page_num)


# ─────────────────────────────────────────────────────────────────────────────
# CSV writer
# ─────────────────────────────────────────────────────────────────────────────

def save_to_csv(quotes: list[Quote], output_path: str) -> None:
    """
    Write a list of Quote objects to a UTF-8 CSV file.
    Column order matches the dataclass field order: text, author.

    Args:
        quotes:      list of Quote instances to write
        output_path: destination file path (created/overwritten)
    """
    path = Path(output_path)
    column_names = [f.name for f in fields(Quote)]

    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=column_names)
        writer.writeheader()
        for quote in quotes:
            writer.writerow({"text": quote.text, "author": quote.author})

    log.info("💾  Saved %d quotes → %s", len(quotes), path.resolve())


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scrape all quotes from quotes.toscrape.com and save to CSV.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--output", "-o",
        default=DEFAULT_OUT,
        help="Path for the output CSV file.",
    )
    parser.add_argument(
        "--delay", "-d",
        type=float,
        default=DEFAULT_DELAY,
        help="Seconds to wait between page requests.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    log.info("=" * 55)
    log.info("  FitTrack Quotes Scraper")
    log.info("  Target  : %s", BASE_URL)
    log.info("  Output  : %s", args.output)
    log.info("  Delay   : %.1f s between pages", args.delay)
    log.info("=" * 55)

    all_quotes: list[Quote] = []

    # Stream quotes page-by-page (memory efficient for large sites)
    for page_quotes in scrape_all_pages(delay=args.delay):
        all_quotes.extend(page_quotes)

    if not all_quotes:
        log.warning("No quotes collected — CSV will not be written.")
        return

    log.info("📊  Total quotes collected: %d", len(all_quotes))
    save_to_csv(all_quotes, args.output)
    log.info("✨  Done!")


if __name__ == "__main__":
    main()
