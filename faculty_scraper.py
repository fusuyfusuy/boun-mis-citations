import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time
from typing import List, Dict, Any

class FacultyScraper:
    def __init__(self, base_url: str = "https://mis.bogazici.edu.tr"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
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
            print(f"Error fetching faculty page: {e}")
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
            print(f"Error scraping {profile_url}: {e}")
            return {'url': profile_url, 'error': str(e)}
    
    def scrape_faculty_citations_only(self, profile_url: str) -> Dict[str, Any]:
        """Extract only citation data from a faculty profile (faster than full profile)."""
        try:
            response = self.session.get(profile_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            return {
                'url': profile_url,
                'name': self._safe_extract(soup, 'h1.page-title'),
                'citations': {
                    'international_articles': self._extract_citations(soup, '.field-name-field-international-article'),
                    'international_book_chapters': self._extract_citations(soup, '.field-name-field-books-book-chapters'),
                    'national_articles': self._extract_citations(soup, '.field-name-field-national-articles'),
                    'international_conference_papers': self._extract_citations(soup, '.field-name-field-international-abstracts-'),
                    'national_conference_papers': self._extract_citations(soup, '.field-name-field-national-abstracts-')
                }
            }
            
        except requests.RequestException as e:
            print(f"Error scraping citations from {profile_url}: {e}")
            return {'url': profile_url, 'name': '', 'error': str(e), 'citations': {}}

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
    
    def scrape_all_citations(self, faculty_page_url: str, delay: float = 1.0) -> Dict[str, Any]:
        """Extract all citations from all faculty members and organize by type."""
        urls = self.get_faculty_urls(faculty_page_url)
        
        if not urls:
            return {'error': 'No faculty URLs found'}
        
        print(f"Extracting citations from {len(urls)} faculty members...")
        
        all_citations = {
            'international_articles': [],
            'international_book_chapters': [],
            'national_articles': [],
            'international_conference_papers': [],
            'national_conference_papers': []
        }
        
        faculty_list = []
        
        for i, url in enumerate(urls, 1):
            print(f"Processing {i}/{len(urls)}: {url.split('/')[-1]}")
            
            citation_data = self.scrape_faculty_citations_only(url)
            faculty_list.append({
                'name': citation_data['name'],
                'url': citation_data['url'],
                'publication_counts': {k: len(v) for k, v in citation_data['citations'].items()}
            })
            
            # Add citations to master lists
            for category, citations in citation_data['citations'].items():
                for citation in citations:
                    all_citations[category].append({
                        'citation': citation,
                        'author': citation_data['name'],
                        'author_url': citation_data['url']
                    })
            
            if i < len(urls):
                time.sleep(delay)
        
        return {
            'faculty_summary': faculty_list,
            'citations_by_type': all_citations,
            'statistics': {
                'total_faculty': len(faculty_list),
                'total_publications': sum(sum(f['publication_counts'].values()) for f in faculty_list),
                'by_type': {k: len(v) for k, v in all_citations.items()}
            }
        }

    def scrape_all_faculty(self, urls, delay: float = 1.0) -> List[Dict[str, Any]]:
        """Complete scraping workflow: get URLs then scrape each profile."""
        # print(f"Getting faculty URLs from: {faculty_page_url}")
        # urls = self.get_faculty_urls(faculty_page_url)
        
        if not urls:
            print("No faculty URLs found!")
            return []
        
        print(f"Found {len(urls)} faculty profiles. Starting scraping...")
        
        faculty_data = []
        for i, url in enumerate(urls, 1):
            print(f"Scraping {i}/{len(urls)}: {url}")
            data = self.scrape_faculty_profile(url)
            faculty_data.append(data)
            
            # Be respectful to the server
            if i < len(urls):
                time.sleep(delay)
        
        return faculty_data

def main():
    # Initialize scraper
    scraper = FacultyScraper()
    
    # Target page URL
    faculty_page = "https://mis.bogazici.edu.tr/full_time_faculty"
    part_time_page = "https://mis.bogazici.edu.tr/part_time_faculty"
    faculty_contributed = "https://mis.bogazici.edu.tr/faculty_members_contributing_to_department"
    assistants = "https://mis.bogazici.edu.tr/teaching_assistants"
    
    # Method 1: Just get the URLs
    print("=== Getting Faculty URLs ===")
    urls = scraper.get_faculty_urls(faculty_page)
    for url in urls:
        print(url)

    print("=== Getting Part Time URLs ===")
    part_time_urls = scraper.get_faculty_urls(part_time_page)
    for url in part_time_urls:
        print(url)

    print("=== Getting Contributed Faculty URLs ===")
    contributed_urls = scraper.get_faculty_urls(faculty_contributed)
    for url in contributed_urls:
        print(url)
    
    print("=== Getting Assistants URLs ===")
    assistants_urls = scraper.get_faculty_urls(assistants)
    for url in assistants_urls:
        print(url)

    urls.extend(part_time_urls)
    urls.extend(contributed_urls)
    urls.extend(assistants_urls)
    
    # Remove duplicates
    urls = list(set(urls))
    
    # Print total found URLs
    print(f"\n=== Found {len(urls)} profiles ===")
    
    # # Method 2: Scrape one faculty member as example
    # if urls:
    #     print(f"\n=== Example: Scraping first faculty member ===")
    #     example_data = scraper.scrape_faculty_profile(urls[0])
    #     print(f"Name: {example_data['name']}")
    #     print(f"Email: {example_data['email']}")
    #     print(f"Total International Articles: {len(example_data['citations']['international_articles'])}")
        
    #     # Show first few citations
    #     if example_data['citations']['international_articles']:
    #         print("\nFirst 3 International Articles:")
    #         for i, citation in enumerate(example_data['citations']['international_articles'][:3], 1):
    #             print(f"{i}. {citation[:100]}...")
    
    # Method 2a: Citations only (faster)
    # if urls:
    #     print(f"\n=== Citations only for first faculty member ===")
    #     citations_data = scraper.scrape_faculty_citations_only(urls[0])
    #     print(f"Name: {citations_data['name']}")
    #     total_pubs = sum(len(pubs) for pubs in citations_data['citations'].values())
    #     print(f"Total publications: {total_pubs}")
    
    # Method 3: All citations analysis (uncomment to run)
    # print(f"\n=== Extracting all citations for analysis ===")
    # citations_analysis = scraper.scrape_all_citations(faculty_page)
    # 
    # print(f"Statistics:")
    # print(f"- Total Faculty: {citations_analysis['statistics']['total_faculty']}")
    # print(f"- Total Publications: {citations_analysis['statistics']['total_publications']}")
    # for pub_type, count in citations_analysis['statistics']['by_type'].items():
    #     print(f"- {pub_type.replace('_', ' ').title()}: {count}")
    # 
    # # Save organized citation data
    # import json
    # with open('faculty_citations_analysis.json', 'w', encoding='utf-8') as f:
    #     json.dump(citations_analysis, f, indent=2, ensure_ascii=False)
    
    # Method 4: Complete faculty profiles (uncomment to run)
    # Method 4: Complete faculty profiles (uncomment to run)
    print(f"\n=== Scraping all {len(urls)} faculty members ===")
    # faculty_data = scraper.scrape_all_faculty(faculty_page)
    faculty_data = scraper.scrape_all_faculty(urls)
    
    # Save results
    import json
    with open('complete_faculty_data.json', 'w', encoding='utf-8') as f:
        json.dump(faculty_data, f, indent=2, ensure_ascii=False)
    
    # Summary statistics
    total_intl_articles = sum(len(f['citations']['international_articles']) for f in faculty_data if 'citations' in f)
    total_conf_papers = sum(len(f['citations']['international_conference_papers']) for f in faculty_data if 'citations' in f)
    print(f"Total International Articles: {total_intl_articles}")
    print(f"Total Conference Papers: {total_conf_papers}")
    print(f"Saved complete data for {len(faculty_data)} faculty members")

if __name__ == "__main__":
    main()