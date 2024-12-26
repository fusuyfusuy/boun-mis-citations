from bs4 import BeautifulSoup
import os
import json
from typing import Dict, List
import logging

class HTMLParser:
    def __init__(self, input_dir: str = 'scraped_pages'):
        self.input_dir = input_dir
        
        # Set up logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def read_html_file(self, filepath: str) -> BeautifulSoup:
        """Read and parse HTML file"""
        with open(filepath, 'r', encoding='utf-8') as f:
            return BeautifulSoup(f.read(), 'html.parser')

    def extract_data(self, soup: BeautifulSoup, selectors: Dict[str, str]) -> Dict:
        """
        Extract data using provided CSS selectors, handling lists specially
        
        Args:
            soup: BeautifulSoup object
            selectors: Dict mapping data keys to CSS selectors
            
        Returns:
            Dict with extracted data
        """
        data = {}
        
        for key, selector in selectors.items():
            element = soup.select_one(selector)
            if not element:
                self.logger.warning(f"Selector '{selector}' not found")
                data[key] = None
                continue
                
            # Check if element contains list items
            list_items = element.find_all('li')
            if list_items:
                # Process each list item
                items = []
                for li in list_items:
                    # Save both text and any links
                    items.append({
                        'text': li.get_text(strip=True),
                        'html': str(li),  # Save original HTML
                        'links': [a.get('href') for a in li.find_all('a') if a.get('href')]
                    })
                data[key] = items
            else:
                # Regular element, just get text
                data[key] = element.get_text(strip=True)
                
        return data

    def process_files(self, selectors: Dict[str, str]) -> List[Dict]:
        """Process all HTML files in the input directory"""
        all_data = []
        
        # Get list of HTML files
        html_files = [f for f in os.listdir(self.input_dir) if f.endswith('.html')]
        
        for filename in html_files:
            filepath = os.path.join(self.input_dir, filename)
            self.logger.info(f"Processing: {filename}")
            
            try:
                # Parse file and extract data
                soup = self.read_html_file(filepath)
                data = self.extract_data(soup, selectors)
                
                # Add filename/source info
                data['source_file'] = filename
                all_data.append(data)
                
            except Exception as e:
                self.logger.error(f"Error processing {filename}: {str(e)}")
        
        return all_data

    def save_results(self, data: List[Dict], output_file: str = 'parsed_data.json'):
        """Save extracted data to JSON file"""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        self.logger.info(f"Saved data to: {output_file}")

# Example usage
def read_class_names(filepath: str) -> Dict[str, str]:
    """Read class names from file and convert to selectors"""
    selectors = {}
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            class_name = line.strip()
            if class_name:
                # Use the class name as both key and selector
                # Adding dot prefix for class selector
                selectors[class_name] = f'.{class_name}'
    return selectors

if __name__ == "__main__":
    # Read selectors from file
    selectors = read_class_names('scope/field-names.txt')
    
    parser = HTMLParser('html_output')
    data = parser.process_files(selectors)
    parser.save_results(data)