import requests
import os
from urllib.parse import urlparse
import time
import logging
from typing import List

class URLScraper:
    def __init__(self, delay: float = 1.0):
        self.delay = delay
        self.session = requests.Session()
        
        # Set up logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Set up session headers
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9',
        })

    def clean_filename(self, url: str) -> str:
        """Convert URL to a safe filename"""
        parsed = urlparse(url)
        path = parsed.path.replace('/', '_')
        if not path:
            path = '_root'
        return f"{parsed.netloc}{path}.html"

    def save_html(self, html: str, filename: str, output_dir: str = 'scraped_pages'):
        """Save HTML content to file"""
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        filepath = os.path.join(output_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)
        self.logger.info(f"Saved: {filepath}")

    def scrape_urls(self, urls: List[str], output_dir: str = 'scraped_pages'):
        """Scrape multiple URLs and save their HTML content"""
        for url in urls:
            try:
                # Rate limiting
                time.sleep(self.delay)
                
                # Send request
                self.logger.info(f"Fetching: {url}")
                response = self.session.get(url)
                response.raise_for_status()
                
                # Save the response
                filename = self.clean_filename(url)
                self.save_html(response.text, filename, output_dir)
                
            except requests.exceptions.RequestException as e:
                self.logger.error(f"Failed to fetch {url}: {str(e)}")
            except Exception as e:
                self.logger.error(f"Error processing {url}: {str(e)}")

# Example usage
def read_urls_from_file(filepath: str) -> List[str]:
    """Read URLs from a text file, one URL per line"""
    with open(filepath, 'r', encoding='utf-8') as f:
        # Strip whitespace and filter out empty lines
        urls = [line.strip() for line in f if line.strip()]
    return urls

if __name__ == "__main__":
    # Read URLs from file
    urls_to_scrape = read_urls_from_file('data/urls/urls.txt')
    
    # Create and run scraper
    scraper = URLScraper(delay=1.0)  # 1 second delay between requests
    scraper.scrape_urls(urls_to_scrape, output_dir='html_output')