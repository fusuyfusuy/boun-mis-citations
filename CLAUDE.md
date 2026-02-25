# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
uv sync

# Step 1: Scrape faculty profiles from mis.bogazici.edu.tr
uv run faculty_scraper.py [--output FILE] [--delay SECS] [--workers N]

# Step 2: Parse scraped data and export to CSV/HTML/JSON
uv run citation_parser.py [--input FILE] [--output-dir DIR] [--threshold FLOAT]
```

The two scripts are run sequentially: `faculty_scraper.py` produces `complete_faculty_data.json`, which `citation_parser.py` then consumes.

## Architecture

**Two-script pipeline:**

1. **`faculty_scraper.py`** — `FacultyScraper` class scrapes four faculty listing pages in parallel (`ThreadPoolExecutor`), collects individual profile URLs (deduped, order-preserved), then scrapes each profile concurrently. Outputs a JSON array of faculty objects, each with `name`, `email`, `title`, etc. and a `citations` dict keyed by publication category.

2. **`citation_parser.py`** — `CitationAnalyzer` class consumes the JSON. Core data model is the `Citation` dataclass, which on init auto-extracts year, DOI, title, and generates an MD5 fingerprint for deduplication. Duplicate removal is two-phase: fingerprint-based (exact/DOI match) then Jaccard-similarity-based (configurable threshold, grouped by year to reduce O(n²) comparisons). `AnalysisConfig` dataclass holds all configuration including category display order, bilingual translations (EN/TR), and duplicate strategy (`keep_first`, `keep_longest`, `keep_most_complete`).

**Output files** (in `citation_analysis_output/` by default):
- `citations_en.csv`, `citations_tr.csv`
- `citations_en.html`, `citations_tr.html` — plain HTML fragments (no CSS) designed for embedding
- `citations_data.json` — structured data with statistics
- `duplicate_report.txt` — details of removed duplicates

**Python version:** 3.11 (see `.python-version`). Package manager: `uv`.
