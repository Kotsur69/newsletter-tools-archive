# Newsletter Tools — Archive

My weekly **steel-market newsletter generator** (Jan 2026), built to support internal executive
reporting. It reads industry PDF/Excel reports and news links, summarizes them with an LLM
and renders a ready-to-send HTML newsletter.

The three generations were separate repos. They're merged here with their commit history,
oldest first:

| Folder | Generation |
|---|---|
| [`newsletter-v1-pdf-excel-urls`](newsletter-v1-pdf-excel-urls) | **v1**: three inputs (PDF reports, Excel files, manually added URLs) → LLM summaries → HTML email template. |
| [`newsletter-v2-v3-with-scraper`](newsletter-v2-v3-with-scraper) | **v2 / v3**: adds an RSS/web scraper (`rss_scraper.py`) and a configurable source list (`sources.json`), so news no longer has to be pasted in by hand. |
| [`steel-business-newsletter`](steel-business-newsletter) | **Final**: scrapes industry sites and parses the weekly PDF reports into a curated market-intelligence newsletter. |

Each folder includes the sample input reports (`data/reports/`) and, where available, a
generated newsletter (`output/newsletter.html`).

**Stack:** Python · web/RSS scraping · PDF & Excel parsing · LLM summarization (prompt
templates in `prompts/`) · Jinja-style HTML templates.

> Archived — not maintained.
