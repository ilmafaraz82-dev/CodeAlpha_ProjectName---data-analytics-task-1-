# 🕷️ Quotes Scraper

A production-quality Python scraper for [quotes.toscrape.com](https://quotes.toscrape.com/).  
Extracts **quote text** and **author name** across all paginated pages and saves to CSV.

---

## 📁 Project Structure

```
quotes-scraper/
├── quotes_scraper.py   # Main scraper script
├── requirements.txt    # Python dependencies
└── README.md           # This file
```

**Generated at runtime:**
```
quotes-scraper/
├── quotes.csv          # Scraped output
└── scraper.log         # Full debug log
```

---

## ⚙️ Setup

### 1. (Optional) Create a virtual environment
```bash
python -m venv venv

# macOS / Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

---

## 🚀 Usage

```bash
# Default — outputs to quotes.csv with a 2-second delay
python quotes_scraper.py

# Custom output file
python quotes_scraper.py --output my_quotes.csv

# Custom delay between requests (seconds)
python quotes_scraper.py --delay 3

# Both options together
python quotes_scraper.py --output data.csv --delay 1.5
```

### CLI flags

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--output` | `-o` | `quotes.csv` | Path for the output CSV file |
| `--delay` | `-d` | `2.0` | Seconds to wait between page requests |

---

## 📄 Output

### quotes.csv
```
text,author
"Life is what happens when you are busy making other plans.",John Lennon
"The world is a book and those who do not travel read only one page.",Saint Augustine
...
```

### scraper.log
```
[10:23:01] INFO      ═══════════════════════════════════════════
[10:23:01] INFO        Quotes Scraper
[10:23:01] INFO        Target  : https://quotes.toscrape.com
[10:23:01] INFO        Output  : quotes.csv
[10:23:01] INFO      ═══════════════════════════════════════════
[10:23:01] INFO      ⏳  Fetching page 1  →  https://quotes.toscrape.com/page/1/
[10:23:02] INFO      ✅  Page 1: extracted 10 quote(s).
...
[10:23:22] INFO      💾  Saved 100 quotes → /path/to/quotes.csv
```

---

## 🏗️ Architecture

| Function | Purpose |
|---|---|
| `setup_logging()` | Dual-handler logger — INFO to console, DEBUG to file |
| `is_scraping_allowed()` | Reads `robots.txt` via `urllib.robotparser` before any request |
| `fetch_page()` | HTTP GET with error handling; returns `BeautifulSoup` or `None` |
| `parse_quotes()` | Extracts quotes from one page; handles missing fields gracefully |
| `get_next_page_url()` | Detects pagination `Next →` link; returns `None` on last page |
| `scrape_all_pages()` | Generator that drives pagination with configurable delay |
| `save_to_csv()` | Writes all `Quote` objects to UTF-8 CSV |

---

## ✅ Features

- **Pagination** — follows every page until no "Next" link is found
- **Browser headers** — mimics Chrome to avoid bot detection
- **Polite delay** — configurable sleep between requests (default 2 s)
- **robots.txt** — checked before scraping starts; aborts if disallowed
- **Graceful errors** — missing fields logged as warnings, not crashes
- **Dual logging** — console progress + full debug log file
- **Modular** — each concern isolated in its own function
- **Type-annotated** — full type hints throughout
- **Dataclass model** — `Quote(text, author)` is clean and extensible

---

## 🐍 Python Version

Requires **Python 3.10+** (uses `X | Y` union type hints).  
For Python 3.8–3.9, replace `str | None` with `Optional[str]` from `typing`.


Key Learnings
Understanding website structure (HTML, tags, classes)
Data extraction using Python
Handling real-world data collection
Version control using Git
