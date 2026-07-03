# Bogazici University MIS Department Citation Scraper

A web scraping and analysis tool for extracting faculty publications and citations from the Bogazici University Management Information Systems (MIS) department website.

## Overview

This project scrapes faculty profiles and publications from the MIS website, processes the data, and exports it into various formats (Excel, HTML). The new unified workflow is handled by a single `main.py` script.

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

To run the entire scraping and exporting process:

```bash
python main.py
```

This will:
1.  Scrape the faculty data for both English and Turkish.
2.  Save the raw data to `outputs/faculty_directory_en.json` and `outputs/faculty_directory_tr.json`.
3.  Export the data to styled Excel files (`.xlsx`) and interactive HTML reports in the `outputs` directory.

### CLI Options

You can customize the behavior with the following options:

*   `--skip-scrape`: Skip the scraping step and only run the exporter on existing JSON files.
*   `--lang [en|tr|both]`: Specify the language to scrape and export (default: `both`).
*   `--delay SECS`: Set the delay in seconds between requests for the scraper (default: `1.0`).
*   `--workers INT`: Set the number of concurrent workers for scraping (default: `5`).

**Example:**

```bash
# Scrape only the English data with a 2-second delay
python main.py --lang en --delay 2
```

## File Structure

```
main.py                 # Main entry point for the scraper and exporter
scraper/
├── faculty_scraper.py  # The core web scraping logic
└── exporter.py         # Exports data to Excel and HTML
outputs/                # Directory for all generated output files
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
- **Bilingual scraping and output (English/Turkish)**
- **Multiple export formats (JSON, styled Excel, interactive HTML)**
- Robust data extraction and cleaning

## Legal & Ethical Considerations

- Respectful crawling with configurable delays
- User-Agent headers for transparency
- Public data only (no private content access)
- Rate limiting to prevent server overload

## License

See [LICENSE.md](LICENSE.md).
