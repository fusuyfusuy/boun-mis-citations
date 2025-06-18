# Bogazici University MIS Department Citation Scraper

A comprehensive web scraping and analysis tool for extracting faculty publications and citations from the Bogazici University Management Information Systems (MIS) department website.

## 🎯 Project Overview

This project consists of two main components:
1. **Faculty Scraper** (`faculty_scraper.py`) - Extracts faculty profiles and publications from the MIS website
2. **Citation Analyzer** (`citation_analyzer.py`) - Processes and organizes the scraped data into structured formats

## 📊 Features

### Web Scraping Capabilities
- ✅ Extracts faculty data from multiple department pages (full-time, part-time, contributing faculty, teaching assistants)
- ✅ Comprehensive profile scraping (contact info, education, research interests)
- ✅ Citation-only extraction mode for faster processing
- ✅ Automatic URL deduplication
- ✅ Respectful rate limiting (configurable delays)
- ✅ Robust error handling and retry mechanisms

### Data Processing & Analysis
- 📈 Year-based citation organization (1950-2030 range)
- 🌍 Bilingual support (English/Turkish)
- 📋 Multiple export formats (JSON, CSV, HTML)
- 📊 Statistical analysis and metadata generation
- 🏷️ Citation categorization by publication type

## 🚀 Quick Start

### Prerequisites

```bash
pip install requests beautifulsoup4 lxml
```

### Basic Usage

```bash
# Step 1: Scrape faculty data
python faculty_scraper.py

# Step 2: Process and analyze citations
python citation_analyzer.py
```

## 📁 File Structure

```
├── faculty_scraper.py          # Main scraping engine
├── citation_analyzer.py        # Data processing and export
├── complete_faculty_data.json  # Raw scraped data (generated)
├── citations_en.csv           # English CSV export (generated)
├── citations_tr.csv           # Turkish CSV export (generated)
├── citations_en.html          # English HTML export (generated)
├── citations_tr.html          # Turkish HTML export (generated)
└── README.md                  # This file
```

## 🔧 Configuration Options

### Scraping Parameters

```python
# Adjust delay between requests (seconds)
delay = 1.0  # Default: 1 second

# Target URLs (customizable)
faculty_pages = [
    "https://mis.bogazici.edu.tr/full_time_faculty",
    "https://mis.bogazici.edu.tr/part_time_faculty", 
    "https://mis.bogazici.edu.tr/faculty_members_contributing_to_department",
    "https://mis.bogazici.edu.tr/teaching_assistants"
]
```

### Processing Options

```python
# Year extraction range
YEAR_RANGE = (1950, 2030)

# Supported languages
LANGUAGES = ['en', 'tr']

# Publication categories
CATEGORIES = [
    'international_articles',
    'international_book_chapters', 
    'national_articles',
    'international_conference_papers',
    'national_conference_papers'
]
```

## 📈 Output Formats

### JSON Structure
```json
{
  "name": "Faculty Name",
  "email": "email@example.com",
  "citations": {
    "international_articles": ["Citation 1", "Citation 2"],
    "international_conference_papers": ["Paper 1", "Paper 2"]
  }
}
```

### CSV Columns
| Column | Description |
|--------|-------------|
| Category | Publication type (localized) |
| Year | Publication year |
| Author | Faculty member name |
| Citation | Full citation text |

### HTML Format
- Organized by publication category
- Chronologically sorted (newest first)
- Citation counts per category/year
- Clean, readable formatting

## ⚡ Performance Optimizations

### Algorithm Complexity
- **URL Extraction**: O(n) where n = number of faculty links
- **Data Processing**: O(m) where m = total citations
- **Year Extraction**: O(1) per citation using regex optimization
- **Memory Usage**: O(k) where k = total scraped data size

### Built-in Optimizations
- ✅ Single-pass citation processing
- ✅ Hash-based URL deduplication: `O(1)` lookup
- ✅ Lazy loading with generators for large datasets
- ✅ In-place text processing to minimize memory allocation
- ✅ Early termination on invalid year ranges
- ✅ Session reuse for HTTP connection pooling

### Best Practices Implemented
```python
# Input validation with bounds checking
if not (1950 <= year <= 2030):
    return None

# Hash map for O(1) category lookups
TRANSLATIONS = {...}  # Pre-computed translations

# Single regex compilation for performance
YEAR_PATTERN = re.compile(r'\((\d{4})\)')
```

## 🛡️ Error Handling

### Network Resilience
- HTTP timeout handling
- Connection retry mechanisms
- Graceful degradation on failed requests
- Status code validation

### Data Validation
- Empty input checking
- Null value handling
- Duplicate detection and removal
- Year range validation
- Character encoding safeguards

## 📊 Statistical Output

The analyzer provides comprehensive statistics:

```
=== CITATION METADATA ===
International Articles: 245 total citations
International Conference Papers: 189 total citations
...

=== OVERALL STATISTICS ===
Total citations: 1,234
Year range: 1995 - 2024
Top productive years: 2023 (89), 2022 (76), 2021 (68)
```

## ⚠️ Legal & Ethical Considerations

### Compliance Features
- ✅ Respectful crawling with configurable delays
- ✅ User-Agent headers for transparency
- ✅ No authentication bypass attempts
- ✅ Public data only (no private content access)
- ✅ Rate limiting to prevent server overload

### Usage Guidelines
- Use responsibly and within reasonable limits
- Respect the website's robots.txt if present
- Consider reaching out to the institution for bulk data needs
- Ensure compliance with local data protection regulations

## 🔄 Development Workflow

### Adding New Faculty Pages
```python
# Extend the URL list in main()
new_urls = scraper.get_faculty_urls("https://mis.bogazici.edu.tr/new_page")
urls.extend(new_urls)
```

### Adding Publication Categories
```python
# Update TRANSLATIONS dictionary
TRANSLATIONS['new_category'] = {
    'en': 'New Category',
    'tr': 'Yeni Kategori'
}
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Follow the existing code style and optimization patterns
4. Add appropriate error handling and input validation
5. Test with small datasets before full runs
6. Submit a pull request with clear documentation

## 📝 Changelog

### v1.0.0
- Initial release
- Basic faculty scraping functionality
- Citation extraction and organization
- Multi-language support
- Statistical analysis features

## 🆘 Troubleshooting

### Common Issues

**"No faculty URLs found"**
- Check if the target website structure has changed
- Verify CSS selectors in `get_faculty_urls()`
- Ensure network connectivity

**"Error scraping profile"**
- Website may be temporarily unavailable
- Check if profile page structure has changed
- Increase delay between requests

**"Year extraction failing"**
- Citations may use non-standard date formats
- Update regex patterns in `extract_year()`
- Check citation text encoding

### Performance Issues
- Reduce concurrent requests (increase delay)
- Process data in smaller batches
- Use citation-only mode for faster extraction
- Check available memory for large datasets

## 📧 Support

For questions, issues, or contributions, please create an issue in the repository or contact the development team.

---

**Note**: This tool is designed for academic and research purposes. Please use responsibly and in accordance with the target website's terms of service.