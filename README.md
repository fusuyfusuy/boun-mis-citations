# Bogazici University MIS Department Citation Scraper

A web scraping and analysis tool for extracting faculty publications and citations from the Bogazici University Management Information Systems (MIS) department website.

## Overview

This project consists of two scripts:
1. **`faculty_scraper.py`** - Scrapes faculty profiles and publications from the MIS website
2. **`citation_parser.py`** - Parses, deduplicates, and exports the scraped data into structured formats (CSV, HTML, JSON)

## Quick Start

### Prerequisites

Install [uv](https://docs.astral.sh/uv/):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Install dependencies

```bash
uv sync
```

### Usage

```bash
# Step 1: Scrape faculty data
uv run faculty_scraper.py

# Step 2: Parse and analyze citations
uv run citation_parser.py
```

### CLI Options

**`faculty_scraper.py`**

```
--output FILE   Output JSON file path (default: complete_faculty_data.json)
--delay SECS    Delay in seconds between requests (default: 1.0)
```

**`citation_parser.py`**

```
--input FILE        Input JSON file from faculty_scraper.py (default: complete_faculty_data.json)
--output-dir DIR    Directory for output files (default: citation_analysis_output)
--threshold FLOAT   Similarity threshold for duplicate detection, 0.0-1.0 (default: 0.85)
```

## File Structure

```
faculty_scraper.py      # Web scraper
citation_parser.py      # Citation parser and exporter
pyproject.toml          # Project dependencies
uv.lock                 # Locked dependency versions
.python-version         # Python version (3.11)
README.md
LICENSE.md
```

## Features

- Extracts faculty data from multiple department pages (full-time, part-time, contributing faculty, teaching assistants)
- Automatic URL deduplication (order-preserving)
- HTTP retry with exponential backoff
- Bilingual output (English/Turkish)
- Multiple export formats (JSON, CSV, styled HTML)
- Duplicate citation detection (DOI-based and similarity-based)
- Configurable similarity threshold and deduplication strategy

## Legal & Ethical Considerations

- Respectful crawling with configurable delays
- User-Agent headers for transparency
- Public data only (no private content access)
- Rate limiting to prevent server overload

## License

See [LICENSE.md](LICENSE.md).
