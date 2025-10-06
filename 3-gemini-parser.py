import json
import re
import csv
import html
from collections import defaultdict
import logging

# Set up basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Translation mappings for citation categories
TRANSLATIONS = {
    'international_articles': {'en': 'International Articles', 'tr': 'Uluslararası Makaleler'},
    'international_book_chapters': {'en': 'International Book Chapters', 'tr': 'Uluslararası Kitap Bölümleri'},
    'international_conference_papers': {'en': 'International Conference Papers', 'tr': 'Uluslararası Bildiriler'},
    'national_conference_papers': {'en': 'National Conference Papers', 'tr': 'Ulusal Bildiriler'},
    'national_articles': {'en': 'National Articles', 'tr': 'Ulusal Makaleler'},
    'national_books': {'en': 'National Books', 'tr': 'Ulusal Kitaplar'},
    'national_conferences': {'en': 'National Conferences', 'tr': 'Ulusal Konferanslar'}
}

def get_category_name(category_key, language='en'):
    """
    Retrieves the translated name for a given category key.
    Falls back to a formatted version of the key if no translation is found.
    """
    return TRANSLATIONS.get(category_key, {}).get(language, category_key.replace('_', ' ').title())

def extract_year(citation_text):
    """
    Extracts the year from a citation string.
    Prioritizes years in parentheses (YYYY) and then looks for any valid 4-digit year.
    """
    # Regex for a 4-digit number within parentheses
    match = re.search(r'\((\d{4})\)', citation_text)
    if match:
        year = int(match.group(1))
        if 1950 <= year <= 2030:
            return year

    # Fallback: Find any 4-digit number that looks like a valid year
    numbers = re.findall(r'\b(\d{4})\b', citation_text)
    for num_str in numbers:
        year = int(num_str)
        if 1950 <= year <= 2030:
            return year

    logging.warning(f"Could not extract a valid year from citation: {citation_text[:100]}...")
    return None

def parse_citations(json_file):
    """
    Parses citation data from a JSON file, organizing it by category and year.
    This version includes deduplication logic.
    """
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            faculty_data = json.load(f)
    except FileNotFoundError:
        logging.error(f"Input file not found: {json_file}")
        return None
    except json.JSONDecodeError:
        logging.error(f"Error decoding JSON from {json_file}")
        return None

    organized_citations = defaultdict(lambda: defaultdict(list))
    # A set to store normalized citation text to detect and skip duplicates.
    seen_citations = set()

    for faculty in faculty_data:
        faculty_name = faculty.get('name', 'Unknown Author')
        if 'citations' not in faculty or not isinstance(faculty['citations'], dict):
            logging.warning(f"No 'citations' dictionary found for {faculty_name}. Skipping.")
            continue

        for category, citations in faculty['citations'].items():
            if not isinstance(citations, list):
                logging.warning(f"Citations for {faculty_name} in category '{category}' is not a list. Skipping.")
                continue
            
            for citation_text in citations:
                # Normalize the text for a reliable duplication check:
                # 1. Convert to lowercase.
                # 2. Remove all non-alphanumeric characters.
                normalized_text = re.sub(r'[^a-z0-9]', '', citation_text.lower())

                # If we've seen this normalized text before, skip it.
                if normalized_text in seen_citations:
                    logging.info(f"Duplicate citation found and skipped: {citation_text[:80]}...")
                    continue
                
                # If it's new, add its signature to the set and process it.
                seen_citations.add(normalized_text)

                year = extract_year(citation_text)
                if year:
                    organized_citations[category][year].append({
                        'text': citation_text.strip(),
                        'author': faculty_name
                    })

    # Sort years in descending order for each category
    for category in organized_citations:
        organized_citations[category] = dict(sorted(organized_citations[category].items(), reverse=True))

    return dict(organized_citations)

def save_to_csv(organized_citations, filename, language='en'):
    """
    Saves the organized citations to a CSV file.
    """
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Category', 'Year', 'Author', 'Citation'])

            for category, years in organized_citations.items():
                category_name = get_category_name(category, language)
                for year, citations in years.items():
                    for citation in citations:
                        writer.writerow([
                            category_name,
                            year,
                            citation['author'],
                            citation['text']
                        ])
        logging.info(f"Successfully saved CSV file: {filename}")
    except IOError as e:
        logging.error(f"Failed to write to CSV file {filename}: {e}")

def save_to_html(organized_citations, filename, language='en'):
    """
    Saves the organized citations to an HTML file with some basic styling.
    """
    html_content = """
    <!DOCTYPE html>
    <html lang="{lang}">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Department Citations</title>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 20px auto; padding: 0 15px; }
            h1 { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
            h2 { color: #34495e; margin-top: 30px; border-bottom: 1px solid #ccc; }
            ol { list-style-type: decimal; padding-left: 20px; }
            li { margin-bottom: 10px; }
            strong.count { font-weight: normal; color: #7f8c8d; }
        </style>
    </head>
    <body>
    """
    html_content = html_content.replace('{lang}', language)

    for category, years in organized_citations.items():
        total_count = sum(len(citations) for citations in years.values())
        category_name = get_category_name(category, language)
        
        html_content += f'<h1>{category_name} <strong class="count">({total_count})</strong></h1>\n'
        
        for year, citations in years.items():
            html_content += f'<h2>{year}</h2>\n<ol>\n'
            for citation in citations:
                escaped_citation = html.escape(citation['text'])
                html_content += f'    <li>{escaped_citation}</li>\n'
            html_content += '</ol>\n'

    html_content += "</body>\n</html>"

    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        logging.info(f"Successfully saved HTML file: {filename}")
    except IOError as e:
        logging.error(f"Failed to write to HTML file {filename}: {e}")

def print_statistics(organized_citations):
    """
    Calculates and prints detailed statistics about the citations.
    """
    if not organized_citations:
        logging.warning("No citation data available to generate statistics.")
        return

    print("\n" + "="*20 + " CITATION STATISTICS " + "="*20)
    
    year_counts = defaultdict(int)
    total_citations = 0

    for category, years in organized_citations.items():
        category_total = sum(len(c) for c in years.values())
        total_citations += category_total
        
        print(f"\n- {get_category_name(category, 'en')}: {category_total} citations")
        for year, citations in years.items():
            year_counts[year] += len(citations)
            print(f"  - {year}: {len(citations)} citations")

    if not year_counts:
        print("\nNo citations with valid years were found.")
        return

    print("\n" + "="*20 + " OVERALL SUMMARY " + "="*20)
    print(f"Total Unique Citations Analyzed: {total_citations}")
    
    min_year, max_year = min(year_counts.keys()), max(year_counts.keys())
    print(f"Year Range: {min_year} - {max_year}")
    print(f"Total Years with Publications: {len(year_counts)}")

    print("\n--- Citations Per Year (All Categories) ---")
    for year in sorted(year_counts.keys(), reverse=True):
        print(f"{year}: {year_counts[year]} citations")

    print("\n--- Top 5 Most Productive Years ---")
    top_years = sorted(year_counts.items(), key=lambda item: item[1], reverse=True)[:5]
    for i, (year, count) in enumerate(top_years, 1):
        print(f"{i}. {year}: {count} citations")
    print("="*59 + "\n")


def main():
    """
    Main function to execute the citation parsing and output generation.
    """
    input_file = "complete_faculty_data.json"
    
    organized_data = parse_citations(input_file)
    
    if organized_data:
        print_statistics(organized_data)
        
        # Generate outputs
        save_to_csv(organized_data, 'citations_en.csv', 'en')
        save_to_csv(organized_data, 'citations_tr.csv', 'tr')
        
        save_to_html(organized_data, 'citations_en.html', 'en')
        save_to_html(organized_data, 'citations_tr.html', 'tr')
        
        logging.info("Processing complete. All files have been generated.")
    else:
        logging.error("Could not parse citation data. Please check the input file and logs.")

if __name__ == "__main__":
    main()
