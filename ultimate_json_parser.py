import json
import re
import csv
import html
from collections import defaultdict

def extract_year(citation_text):
    """Extract year from citation - looks for (YYYY) format first."""
    # Try (YYYY) format first - most common in academic citations
    match = re.search(r'\((\d{4})\)', citation_text)
    if match:
        year = int(match.group(1))
        if 1950 <= year <= 2030:  # Valid range
            return year
    
    # Fallback: find any 4-digit number in valid range
    numbers = re.findall(r'\b(\d{4})\b', citation_text)
    for num in numbers:
        year = int(num)
        if 1950 <= year <= 2030:
            return year
    
    return None

def parse_citations(json_file):
    """Parse faculty JSON and organize citations by category and year."""
    with open(json_file, 'r', encoding='utf-8') as f:
        faculty_data = json.load(f)
    
    # Group citations by category and year
    organized = defaultdict(lambda: defaultdict(list))
    
    for faculty in faculty_data:
        if 'citations' not in faculty:
            continue
            
        faculty_name = faculty.get('name', 'Unknown')
        
        for category, citations in faculty['citations'].items():
            for citation in citations:
                year = extract_year(citation)
                if year:
                    organized[category][year].append({
                        'text': citation,
                        'author': faculty_name
                    })
    
    # Sort years (newest first)
    for category in organized:
        organized[category] = dict(sorted(
            organized[category].items(), 
            reverse=True
        ))
    
    return dict(organized)

def save_to_csv(organized_citations, filename):
    """Save citations to CSV file."""
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Category', 'Year', 'Author', 'Citation'])
        
        for category, years in organized_citations.items():
            for year, citations in years.items():
                for citation in citations:
                    writer.writerow([
                        category.replace('_', ' ').title(),
                        year,
                        citation['author'],
                        citation['text']
                    ])

def save_to_html(organized_citations, filename):
    """Save citations to HTML file."""
    with open(filename, 'w', encoding='utf-8') as f:
        for category, years in organized_citations.items():
            # Count total citations in this category
            total_count = sum(len(citations) for citations in years.values())
            
            # Category header
            category_name = category.replace('_', ' ').title()
            f.write(f'<h1><strong>{category_name} ({total_count} articles)</strong></h1>')
            
            # Years and citations
            for year, citations in years.items():
                f.write(f'<h2><strong>{year} </strong></h2>')
                f.write('<ol>')
                
                for citation in citations:
                    # Escape HTML entities
                    escaped_citation = html.escape(citation['text'])
                    f.write(f'<li>{escaped_citation}</li>')
                
                f.write('</ol>')

def print_metadata(organized_citations):
    """Print detailed metadata about citations."""
    print("\n=== CITATION METADATA ===")
    
    # Collect all years and count citations per year
    year_counts = defaultdict(int)
    category_year_counts = defaultdict(lambda: defaultdict(int))
    
    total_citations = 0
    
    for category, years in organized_citations.items():
        category_total = 0
        for year, citations in years.items():
            count = len(citations)
            year_counts[year] += count
            category_year_counts[category][year] = count
            category_total += count
            total_citations += count
        
        print(f"\n{category.replace('_', ' ').title()}: {category_total} total citations")
        # Show year breakdown for this category
        for year in sorted(years.keys(), reverse=True):
            print(f"  {year}: {len(years[year])} citations")
    
    print(f"\n=== OVERALL STATISTICS ===")
    print(f"Total citations: {total_citations}")
    print(f"Year range: {min(year_counts.keys())} - {max(year_counts.keys())}")
    print(f"Total years covered: {len(year_counts)}")
    
    print(f"\n=== CITATIONS PER YEAR (ALL CATEGORIES) ===")
    for year in sorted(year_counts.keys(), reverse=True):
        print(f"{year}: {year_counts[year]} citations")
    
    print(f"\n=== TOP PRODUCTIVE YEARS ===")
    top_years = sorted(year_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    for year, count in top_years:
        print(f"{year}: {count} citations")

def print_summary(organized_citations):
    """Print a simple summary."""
    total = 0
    for category, years in organized_citations.items():
        cat_total = sum(len(citations) for citations in years.values())
        total += cat_total
        print(f"{category.replace('_', ' ').title()}: {cat_total} citations")
    
    print(f"Total citations with years: {total}")

def main():
    input_file = "complete_faculty_data.json"
    
    try:
        print("Parsing citations...")
        organized = parse_citations(input_file)
        
        print("\n=== SUMMARY ===")
        print_summary(organized)
        
        # Print detailed metadata
        print_metadata(organized)
        
        # Save to CSV
        save_to_csv(organized, 'citations.csv')
        print("✓ Saved to citations.csv")
        
        # Save to HTML
        save_to_html(organized, 'citations.html')
        print("✓ Saved to citations.html")
        
        # Show example
        if organized:
            first_category = list(organized.keys())[0]
            first_year = list(organized[first_category].keys())[0]
            print(f"\nExample: {first_category} in {first_year}:")
            for i, citation in enumerate(organized[first_category][first_year][:2], 1):
                print(f"{i}. {citation['author']}: {citation['text'][:80]}...")
        
    except FileNotFoundError:
        print(f"Error: {input_file} not found. Run the first script first!")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()