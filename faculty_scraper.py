import argparse
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
from requests.adapters import HTTPAdapter
from urllib.parse import urljoin
from urllib3.util.retry import Retry

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class FacultyScraper:
    def __init__(self, base_url: str = "https://mis.bogazici.edu.tr"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        retry = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.session.close()

    def get_faculty_urls(self, faculty_page_url: str) -> List[str]:
        """Extract all faculty profile URLs from the main faculty page."""
        try:
            response = self.session.get(faculty_page_url)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Find all faculty profile links - they're in the title field of each faculty card
            faculty_links = soup.select('.views-field-title a[href^="/content/"]')

            urls = []
            for link in faculty_links:
                href = link.get('href')
                if href:
                    full_url = urljoin(self.base_url, href)
                    urls.append(full_url)

            return urls

        except requests.RequestException as e:
            logger.error(f"Error fetching faculty page: {e}")
            return []

    def scrape_faculty_profile(self, profile_url: str) -> Dict[str, Any]:
        """Scrape individual faculty profile data including all citations."""
        try:
            response = self.session.get(profile_url)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Basic faculty info
            data = {
                'url': profile_url,
                'name': self._safe_extract(soup, 'h1.page-title'),
                'title': self._safe_extract(soup, '.field-name-field-body-computed'),
                'email': self._safe_extract(soup, '.field-name-field-email a', 'href'),
                'phone': self._safe_extract(soup, '.field-name-field-phone-number'),
                'website': self._safe_extract(soup, '.field-name-field-website a', 'href'),
                'education': self._safe_extract(soup, '.field-name-field-education'),
                'courses_taught': self._safe_extract(soup, '.field-name-field-courses-taught'),
                'research_interests': self._safe_extract(soup, '.field-name-field-research-interests')
            }

            # Extract all publication sections
            data['citations'] = {
                'international_articles': self._extract_citations(soup, '.field-name-field-international-article'),
                'international_book_chapters': self._extract_citations(soup, '.field-name-field-books-book-chapters'),
                'national_articles': self._extract_citations(soup, '.field-name-field-national-articles'),
                'international_conference_papers': self._extract_citations(soup, '.field-name-field-international-abstracts-'),
                'national_conference_papers': self._extract_citations(soup, '.field-name-field-national-abstracts-')
            }

            return data

        except requests.RequestException as e:
            logger.error(f"Error scraping {profile_url}: {e}")
            return {'url': profile_url, 'error': str(e)}

    def _extract_citations(self, soup, field_selector: str) -> List[str]:
        """Extract citations from a specific field section."""
        citations = []
        field = soup.select_one(field_selector)
        if field:
            # Find all list items within this field
            citation_items = field.select('li')
            for item in citation_items:
                citation_text = item.get_text(strip=True)
                if citation_text:
                    citations.append(citation_text)
        return citations

    def _safe_extract(self, soup, selector: str, attr: str = None) -> str:
        """Safely extract text or attribute from soup."""
        element = soup.select_one(selector)
        if element:
            if attr:
                return element.get(attr, '').strip()
            return element.get_text(strip=True)
        return ''

    def scrape_all_faculty(self, urls: List[str], delay: float = 1.0, max_workers: int = 5) -> List[Dict[str, Any]]:
        """Complete scraping workflow: scrape each profile from given URLs."""
        if not urls:
            logger.warning("No faculty URLs found!")
            return []

        total = len(urls)
        logger.info(f"Found {total} faculty profiles. Starting scraping with {max_workers} workers...")

        results: Dict[str, Dict] = {}
        errors = 0

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {}
            for i, url in enumerate(urls):
                futures[pool.submit(self.scrape_faculty_profile, url)] = url
                if i < len(urls) - 1:
                    time.sleep(delay)

            with tqdm(as_completed(futures), total=total, desc="Scraping faculty", unit="profile") as pbar:
                for future in pbar:
                    url = futures[future]
                    result = future.result()
                    results[url] = result

                    if 'error' in result:
                        errors += 1
                    name = result.get('name', url.split('/')[-1])
                    pbar.set_postfix(name=name[:30])

        if errors:
            logger.warning(f"Completed with {errors} error(s) out of {total}")

        # Preserve original URL order
        return [results[url] for url in urls]


def main():
    parser = argparse.ArgumentParser(description="Scrape faculty data from Bogazici MIS website")
    parser.add_argument("--output", default="complete_faculty_data.json", help="Output JSON file path")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay in seconds between requests")
    parser.add_argument("--workers", type=int, default=5, help="Number of concurrent workers for scraping")
    args = parser.parse_args()

    # Target page URLs
    page_urls = [
        "https://mis.bogazici.edu.tr/full_time_faculty",
        "https://mis.bogazici.edu.tr/part_time_faculty",
        "https://mis.bogazici.edu.tr/faculty_members_contributing_to_department",
        "https://mis.bogazici.edu.tr/teaching_assistants",
    ]

    with FacultyScraper() as scraper:
        # Fetch all index pages in parallel
        urls = []
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = {pool.submit(scraper.get_faculty_urls, url): url for url in page_urls}
            with tqdm(as_completed(futures), total=len(page_urls), desc="Fetching index pages", unit="page") as pbar:
                for future in pbar:
                    page_url = futures[future]
                    label = page_url.split("/")[-1].replace("_", " ").title()
                    page_urls_found = future.result()
                    logger.info(f"Getting URLs from: {label} ({len(page_urls_found)} found)")
                    urls.extend(page_urls_found)

        # Remove duplicates while preserving order
        urls = list(dict.fromkeys(urls))

        logger.info(f"Found {len(urls)} unique profiles")

        # Scrape all faculty
        logger.info(f"Scraping all {len(urls)} faculty members...")
        faculty_data = scraper.scrape_all_faculty(urls, delay=args.delay, max_workers=args.workers)

    # Save results
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(faculty_data, f, indent=2, ensure_ascii=False)

    # Summary statistics
    total_intl_articles = sum(len(f['citations']['international_articles']) for f in faculty_data if 'citations' in f)
    total_conf_papers = sum(len(f['citations']['international_conference_papers']) for f in faculty_data if 'citations' in f)
    logger.info(f"Total International Articles: {total_intl_articles}")
    logger.info(f"Total Conference Papers: {total_conf_papers}")
    logger.info(f"Saved complete data for {len(faculty_data)} faculty members to {args.output}")


if __name__ == "__main__":
    main()
