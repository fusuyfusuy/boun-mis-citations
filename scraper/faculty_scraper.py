import argparse
import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from tqdm import tqdm
from urllib3.util.retry import Retry

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class FacultyScraperV2:
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

    def get_faculty_urls_with_role(self, faculty_page_url: str, role_name: str) -> List[Dict[str, str]]:
        """Extract all faculty profile URLs and assign their role."""
        try:
            response = self.session.get(faculty_page_url)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Find all faculty profile links
            faculty_links = soup.select('.views-field-title a[href*="/content/"]')

            urls_with_role = []
            for link in faculty_links:
                href = link.get('href')
                if href:
                    full_url = urljoin(self.base_url, href)
                    urls_with_role.append({
                        'url': full_url,
                        'role': role_name
                    })

            return urls_with_role

        except requests.RequestException as e:
            logger.error(f"Error fetching index page {faculty_page_url}: {e}")
            return []

    def scrape_faculty_profile(self, profile_url: str, role: str) -> Dict[str, Any]:
        """Scrape individual faculty profile data including new fields and clean representation."""
        try:
            response = self.session.get(profile_url)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract email
            email_el = soup.select_one('.field-name-field-email a')
            email = ''
            if email_el:
                email = email_el.get('href', '').replace('mailto:', '').strip()
            if not email and email_el:
                email = email_el.get_text(strip=True)

            # Extract website
            web_el = soup.select_one('.field-name-field-website a')
            website = ''
            if web_el:
                website = web_el.get('href', '').strip()
            if not website and web_el:
                website = web_el.get_text(strip=True)

            # Extract profile picture
            img_el = soup.select_one('.field-name-field-picture img')
            picture_url = ''
            if img_el:
                src = img_el.get('src', '')
                if src:
                    picture_url = urljoin(self.base_url, src)

            # Extract title
            title = self._safe_extract(soup, '.field-name-field-body-computed')

            # Extract career sections (clean representation automatically using field-item text)
            education = self._safe_extract_field_items(soup, '.field-name-field-education')
            courses_taught = self._safe_extract_field_items(soup, '.field-name-field-courses-taught')
            research_interests = self._safe_extract_field_items(soup, '.field-name-field-research-interests')
            projects = self._safe_extract_field_items(soup, '.field-name-field-projects')

            # Extract newly discovered fields
            cv_el = soup.select_one('.field-name-field-cv1')
            cv_link = ''
            cv_text = ''
            if cv_el:
                link = cv_el.find('a')
                if link:
                    cv_link = urljoin(self.base_url, link.get('href', ''))
                cv_text = cv_el.get_text(strip=True)

            area = self._safe_extract_field_items(soup, '.field-name-field-area')
            recent_publications = self._safe_extract_field_items(soup, '.field-name-field-recent-publications')

            data = {
                'url': profile_url,
                'name': self._safe_extract(soup, 'h1.page-title'),
                'title': title,
                'role': role,
                'email': email,
                'phone': self._safe_extract(soup, '.field-name-field-phone-number'),
                'website': website,
                'picture_url': picture_url,
                'education': education,
                'courses_taught': courses_taught,
                'research_interests': research_interests,
                'projects': projects,
                'cv_link': cv_link,
                'cv_text': cv_text,
                'area': area,
                'recent_publications': recent_publications,
            }

            # Extract all publication sections
            data['citations'] = {
                'international_articles': self._extract_citations(soup, '.field-name-field-international-article'),
                'international_book_chapters': self._extract_citations(soup, '.field-name-field-books-book-chapters'),
                'national_books': self._extract_citations(soup, '.field-name-field-national-books'),
                'national_articles': self._extract_citations(soup, '.field-name-field-national-articles'),
                'international_conference_papers': self._extract_citations(soup, '.field-name-field-international-abstracts-'),
                'national_conference_papers': self._extract_citations(soup, '.field-name-field-national-abstracts-')
            }

            return data

        except requests.RequestException as e:
            logger.error(f"Error scraping {profile_url}: {e}")
            return {'url': profile_url, 'role': role, 'error': str(e)}

    def _extract_citations(self, soup, field_selector: str) -> List[str]:
        """Extract citations from a specific field section."""
        citations = []
        field = soup.select_one(field_selector)
        if field:
            # Replace all <br> tags in this element subtree with newlines
            for br in field.find_all('br'):
                br.replace_with('\n')
                
            # Find all list items within this field
            citation_items = field.select('li')
            for item in citation_items:
                citation_text = item.get_text().strip()
                if citation_text:
                    citations.append(citation_text)
            
            # If no li items but there is text inside, split by newline or keep as is
            if not citations:
                items = field.select('.field-item')
                if items:
                    text_content = ' \n '.join(item.get_text() for item in items)
                else:
                    text_content = field.get_text()
                
                if text_content:
                    lines = [line.strip() for line in text_content.split('\n') if line.strip()]
                    citations.extend(lines)
        return citations

    def _safe_extract(self, soup, selector: str, attr: str = None) -> str:
        """Safely extract text or attribute from soup."""
        element = soup.select_one(selector)
        if element:
            if attr:
                return element.get(attr, '').strip()
            return element.get_text(strip=True)
        return ''

    def _safe_extract_field_items(self, soup, selector: str) -> str:
        """Extract only field content items (which naturally avoids label prefixes) and preserves line breaks."""
        element = soup.select_one(selector)
        if not element:
            return ''
        
        # Replace all <br> tags in this element subtree with newlines first
        for br in element.find_all('br'):
            br.replace_with('\n')
            
        items = element.select('.field-item')
        if not items:
            items = [element]
            
        field_texts = []
        for item in items:
            p_tags = item.find_all('p')
            if p_tags:
                text = '\n'.join(p.get_text().strip() for p in p_tags if p.get_text().strip())
            else:
                li_tags = item.find_all('li')
                if li_tags:
                    text = '\n'.join(li.get_text().strip() for li in li_tags if li.get_text().strip())
                else:
                    text = item.get_text().strip()
            field_texts.append(text)
            
        full_text = '\n'.join(field_texts).strip()
        
        # If we fell back to the root element, we may need to strip the label prefix
        if not element.select('.field-item'):
            for prefix in ["Education", "Research Interests", "Courses Taught", "Projects", "Eğitim", "Araştırma Alanları", "Verilen Dersler", "Projeler"]:
                if full_text.lower().startswith(prefix.lower()):
                    full_text = full_text[len(prefix):].strip()
                    if full_text.startswith(':'):
                        full_text = full_text[1:].strip()
                        
        return full_text

    def scrape_all_faculty(self, items: List[Dict[str, str]], delay: float = 1.0, max_workers: int = 5) -> List[Dict[str, Any]]:
        """Complete scraping workflow: scrape each profile from given URLs."""
        if not items:
            logger.warning("No faculty URLs found!")
            return []

        total = len(items)
        logger.info(f"Found {total} faculty profiles. Starting scraping with {max_workers} workers...")

        results: Dict[str, Dict] = {}
        errors = 0

        # We first fetch one profile to establish cookies synchronously in the pool
        first_item = items[0]
        logger.info(f"Establishing session cookie by scraping first profile: {first_item['url']}")
        first_res = self.scrape_faculty_profile(first_item['url'], first_item['role'])
        results[first_item['url']] = first_res
        if 'error' in first_res:
            logger.warning(f"Error establishing session on first profile: {first_res['error']}. Visiting index first.")
            # Determine correct index prefix (EN or TR)
            prefix = "tr/" if "/tr/" in first_item['url'] else ""
            self.session.get(f"https://mis.bogazici.edu.tr/{prefix}full_time_faculty")

        # Now scrape the rest in parallel
        remaining_items = items[1:]
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {}
            for i, item in enumerate(remaining_items):
                futures[pool.submit(self.scrape_faculty_profile, item['url'], item['role'])] = item['url']
                if i < len(remaining_items) - 1:
                    time.sleep(delay)

            with tqdm(as_completed(futures), total=len(remaining_items), desc="Scraping faculty", unit="profile") as pbar:
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
        return [results[item['url']] for item in items]


def run_language_scraper(scraper, page_roles, lang_code, delay, max_workers):
    logger.info(f"=== Starting Scraper for Language: {lang_code.upper()} ===")
    
    # Pre-visit index page to establish cookies
    index_prefix = "tr/" if lang_code == "tr" else ""
    scraper.session.get(f"https://mis.bogazici.edu.tr/{index_prefix}full_time_faculty")

    # Fetch index pages
    faculty_items = []
    seen_urls = set()

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {
            pool.submit(scraper.get_faculty_urls_with_role, url, role): (url, role)
            for url, role in page_roles
        }
        for future in as_completed(futures):
            url, role = futures[future]
            items_found = future.result()
            logger.info(f"[{lang_code.upper()}] Role: '{role}' - Found {len(items_found)} profiles")
            
            for item in items_found:
                if item['url'] not in seen_urls:
                    seen_urls.add(item['url'])
                    faculty_items.append(item)
                else:
                    for existing_item in faculty_items:
                        if existing_item['url'] == item['url']:
                            if role not in existing_item['role']:
                                existing_item['role'] += f", {role}"
                            break

    logger.info(f"[{lang_code.upper()}] Found {len(faculty_items)} unique personnel profiles")
    if not faculty_items:
        return []

    # Scrape all
    return scraper.scrape_all_faculty(faculty_items, delay=delay, max_workers=max_workers)


def main():
    parser = argparse.ArgumentParser(description="Scrape faculty data v2 (Bilingual) from Bogazici MIS website")
    parser.add_argument("--lang", default="both", choices=["en", "tr", "both"], help="Language version to scrape")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay in seconds between requests")
    parser.add_argument("--workers", type=int, default=5, help="Number of concurrent workers for scraping")
    args = parser.parse_args()

    # Define listing pages
    en_pages = [
        ("https://mis.bogazici.edu.tr/full_time_faculty", "Full-Time Faculty"),
        ("https://mis.bogazici.edu.tr/part_time_faculty", "Part-Time Faculty"),
        ("https://mis.bogazici.edu.tr/faculty_members_contributing_to_department", "Contributing Faculty"),
        ("https://mis.bogazici.edu.tr/teaching_assistants", "Teaching Assistant"),
    ]

    tr_pages = [
        ("https://mis.bogazici.edu.tr/tr/full_time_faculty", "Tam Zamanlı Kadro"),
        ("https://mis.bogazici.edu.tr/tr/part_time_faculty", "Yarı Zamanlı Kadro"),
        ("https://mis.bogazici.edu.tr/tr/faculty_members_contributing_to_department", "Katkı Veren Akademisyenler"),
        ("https://mis.bogazici.edu.tr/tr/teaching_assistants", "Araştırma Görevlileri"),
    ]

    os.makedirs("outputs", exist_ok=True)

    with FacultyScraperV2() as scraper:
        # EN
        if args.lang in ["en", "both"]:
            en_data = run_language_scraper(scraper, en_pages, "en", args.delay, args.workers)
            output_en = "outputs/faculty_directory_en.json"
            with open(output_en, 'w', encoding='utf-8') as f:
                json.dump(en_data, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved English data for {len(en_data)} profiles to {output_en}")

        # TR
        if args.lang in ["tr", "both"]:
            tr_data = run_language_scraper(scraper, tr_pages, "tr", args.delay, args.workers)
            output_tr = "outputs/faculty_directory_tr.json"
            with open(output_tr, 'w', encoding='utf-8') as f:
                json.dump(tr_data, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved Turkish data for {len(tr_data)} profiles to {output_tr}")


if __name__ == "__main__":
    main()
