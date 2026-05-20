import argparse
import csv
import functools
import hashlib
import html
import json
import logging
import re
from tqdm import tqdm
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class Citation:
    """Represents a single citation with metadata and duplicate detection."""

    # Pre-compiled regex patterns (class-level)
    _RE_YEAR_PAREN = re.compile(r'\((\d{4})\)')
    _RE_YEAR_BARE = re.compile(r'\b(\d{4})\b')
    _RE_REMOVE_ALL = re.compile(
        r'https?://[^\s]+'        # URLs
        r'|doi:\s*'               # DOI prefix
        r'|\([^)]*\)'             # Parenthetical
        r'|vol\.\s*\d+'           # Volume
        r"|pp?\.\s*\d+[-\u2013]\d+"  # Pages
    )
    _RE_NORMALIZE = re.compile(r'[&.,;:!?"\s]+')
    _RE_DOI_PATTERNS = [
        re.compile(r'doi:\s*([0-9.]+/[^\s,)]+)', re.IGNORECASE),
        re.compile(r'https?://doi\.org/([0-9.]+/[^\s,)]+)', re.IGNORECASE),
        re.compile(r'https?://dx\.doi\.org/([0-9.]+/[^\s,)]+)', re.IGNORECASE),
        re.compile(r'\b(10\.[0-9]+/[^\s,)]+)', re.IGNORECASE),
    ]
    _RE_QUOTED_TITLE = re.compile(r'"([^"]+)"')
    _RE_TITLE_PATTERNS = [
        re.compile(r'(?:\.|\))\s+([^.]+?)\.\s+[A-Z][^.]+(?:Journal|Conference|Proceedings)'),
        re.compile(r'(?:\.|\))\s+([^.]+?)\s+\(\d{4}\)'),
    ]
    _RE_NON_ALNUM = re.compile(r'[^\w\s]')

    text: str
    author: str
    year: Optional[int] = None
    category: str = ""
    normalized_text: str = field(init=False)
    fingerprint: str = field(init=False)
    doi: Optional[str] = field(init=False, default=None)
    title: Optional[str] = field(init=False, default=None)

    def __post_init__(self):
        if self.year is None:
            self.year = self._extract_year()
        self.normalized_text = self._normalize_text()
        self.doi = self._extract_doi()
        self.title = self._extract_title()
        self.fingerprint = self._generate_fingerprint()

    def _extract_year(self) -> Optional[int]:
        """Extract year from citation text."""
        match = self._RE_YEAR_PAREN.search(self.text)
        if match:
            year = int(match.group(1))
            if 1950 <= year <= 2030:
                return year

        for m in self._RE_YEAR_BARE.finditer(self.text):
            year = int(m.group(1))
            if 1950 <= year <= 2030:
                return year

        return None

    def _normalize_text(self) -> str:
        """Normalize citation text for comparison."""
        text = self._RE_REMOVE_ALL.sub(' ', self.text.lower())
        text = self._RE_NORMALIZE.sub(' ', text)
        return text.strip()

    def _extract_doi(self) -> Optional[str]:
        """Extract DOI from citation text."""
        for pattern in self._RE_DOI_PATTERNS:
            match = pattern.search(self.text)
            if match:
                doi = match.group(1).rstrip('.,;)')
                return doi.lower()
        return None

    def _extract_title(self) -> Optional[str]:
        """Extract title from citation text."""
        quoted_match = self._RE_QUOTED_TITLE.search(self.text)
        if quoted_match:
            return quoted_match.group(1).strip()

        for pattern in self._RE_TITLE_PATTERNS:
            match = pattern.search(self.text)
            if match:
                title = match.group(1).strip()
                if len(title) > 10:
                    return title

        return None
    
    @functools.cached_property
    def _word_tokens(self) -> frozenset:
        """Pre-computed word token set for Jaccard similarity."""
        return frozenset(self.normalized_text.split())

    def _generate_fingerprint(self) -> str:
        """Generate a unique fingerprint for duplicate detection."""
        # Use DOI as primary identifier
        if self.doi:
            return hashlib.md5(f"doi:{self.doi}".encode()).hexdigest()

        # Fallback to normalized text + year
        fingerprint_text = f"{self.normalized_text}:{self.year or 'no_year'}"
        return hashlib.md5(fingerprint_text.encode()).hexdigest()

    def similarity_score(self, other: 'Citation') -> float:
        """Calculate similarity score with another citation (0-1)."""
        if not isinstance(other, Citation):
            return 0.0

        # DOI match is definitive
        if self.doi and other.doi and self.doi == other.doi:
            return 1.0

        # Title match with same year is very strong
        if (self.title and other.title and self.year == other.year and
            self._normalize_string(self.title) == self._normalize_string(other.title)):
            return 0.95

        # Token-set Jaccard similarity (O(n+m) vs SequenceMatcher O(n*m))
        self_tokens = self._word_tokens
        other_tokens = other._word_tokens
        if not self_tokens or not other_tokens:
            return 0.0
        intersection = len(self_tokens & other_tokens)
        union = len(self_tokens | other_tokens)
        similarity = intersection / union

        # Boost similarity if years match
        if self.year and other.year and self.year == other.year:
            similarity = min(1.0, similarity + 0.1)

        return similarity
    
    def _normalize_string(self, text: str) -> str:
        """Normalize string for comparison."""
        return self._RE_NON_ALNUM.sub('', text.lower()).strip()
    
    def is_duplicate_of(self, other: 'Citation', threshold: float = 0.85) -> bool:
        """Check if this citation is a duplicate of another."""
        return self.similarity_score(other) >= threshold

@dataclass
class AnalysisConfig:
    """Configuration for citation analysis."""
    input_file: str = "complete_faculty_data.json"
    output_dir: str = "output"
    languages: List[str] = field(default_factory=lambda: ['en', 'tr'])
    year_range: tuple = (1950, 2030)
    output_formats: List[str] = field(default_factory=lambda: ['csv', 'html', 'json'])
    
    # Category display order (categories not listed here appear at the end)
    category_order: List[str] = field(default_factory=lambda: [
        'international_articles',
        'international_conference_papers',
        'international_book_chapters',
        'national_articles',
        'national_conference_papers',
        'national_books',
        'national_conferences',
    ])

    # HTML anchor names per category
    category_anchors: Dict[str, str] = field(default_factory=lambda: {
        'international_articles': 'international-paper',
        'national_articles': 'national-paper',
        'international_conference_papers': 'international-conference',
        'international_book_chapters': 'international-book',
        'national_conference_papers': 'national-conference',
    })

    # Duplicate detection settings
    enable_duplicate_detection: bool = True
    similarity_threshold: float = 0.85
    duplicate_strategy: str = "keep_first"  # Options: "keep_first", "keep_longest", "keep_most_complete"
    report_duplicates: bool = True
    
    # Translation mappings
    translations: Dict[str, Dict[str, str]] = field(default_factory=lambda: {
        'international_articles': {
            'en': 'International Articles',
            'tr': 'Uluslararası Makaleler'
        },
        'international_book_chapters': {
            'en': 'International Book Chapters', 
            'tr': 'Uluslararası Kitap Bölümleri'
        },
        'international_conference_papers': {
            'en': 'International Conference Papers',
            'tr': 'Uluslararası Bildiriler'
        },
        'national_conference_papers': {
            'en': 'National Conference Papers',
            'tr': 'Ulusal Bildiriler'  
        },
        'national_articles': {
            'en': 'National Articles',
            'tr': 'Ulusal Makaleler'
        },
        'national_books': {
            'en': 'National Books',
            'tr': 'Ulusal Kitaplar'
        },
        'national_conferences': {
            'en': 'National Conferences', 
            'tr': 'Ulusal Konferanslar'
        }
    })

class CitationAnalyzer:
    """Main class for analyzing faculty citations."""
    
    def __init__(self, config: AnalysisConfig):
        self.config = config
        self.citations: List[Citation] = []
        self.duplicates_removed: List[Tuple[Citation, Citation]] = []  # (original, duplicate)
        self.organized_data: Dict[str, Dict[int, List[Citation]]] = defaultdict(lambda: defaultdict(list))
        
        # Ensure output directory exists
        Path(self.config.output_dir).mkdir(exist_ok=True)
    
    def load_data(self) -> None:
        """Load faculty data from JSON file."""
        try:
            with open(self.config.input_file, 'r', encoding='utf-8') as f:
                faculty_data = json.load(f)
            
            logger.info(f"Loaded data for {len(faculty_data)} faculty members")
            self._parse_citations(faculty_data)
            
            if self.config.enable_duplicate_detection:
                self._remove_duplicates()
            
        except FileNotFoundError:
            logger.error(f"Input file {self.config.input_file} not found")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {self.config.input_file}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            raise
    
    def _parse_citations(self, faculty_data: List[Dict]) -> None:
        """Parse citations from faculty data."""
        for faculty in tqdm(faculty_data, desc="Parsing citations", unit="faculty"):
            if 'citations' not in faculty:
                logger.warning(f"No citations found for faculty: {faculty.get('name', 'Unknown')}")
                continue
                
            faculty_name = faculty.get('name', 'Unknown')
            
            for category, citation_texts in faculty['citations'].items():
                for text in citation_texts:
                    citation = Citation(
                        text=text,
                        author=faculty_name,
                        category=category
                    )
                    self.citations.append(citation)
        
        logger.info(f"Parsed {len(self.citations)} total citations")
    
    def _remove_duplicates(self) -> None:
        """Remove duplicate citations based on configuration."""
        logger.info("Starting duplicate detection...")
        
        original_count = len(self.citations)
        unique_citations = []
        seen_fingerprints = set()
        
        # Group citations for detailed comparison
        fingerprint_groups = defaultdict(list)
        for citation in self.citations:
            fingerprint_groups[citation.fingerprint].append(citation)
        
        for fingerprint, group in tqdm(fingerprint_groups.items(), desc="Deduplicating (fingerprint)", unit="group"):
            if len(group) == 1:
                # No duplicates for this fingerprint
                unique_citations.extend(group)
            else:
                # Handle duplicates within this group
                kept, removed = self._resolve_duplicate_group(group)
                unique_citations.extend(kept)
                self.duplicates_removed.extend(removed)
        
        # Additional similarity-based detection for different fingerprints
        if self.config.similarity_threshold < 1.0:
            unique_citations = self._remove_similar_duplicates(unique_citations)
        
        self.citations = unique_citations

        # Invalidate cached statistics
        if hasattr(self, '_cached_stats'):
            del self._cached_stats

        # Organize the deduplicated citations
        self._organize_citations()
        
        removed_count = original_count - len(self.citations)
        logger.info(f"Removed {removed_count} duplicate citations")
        logger.info(f"Remaining citations: {len(self.citations)}")
        
        if self.config.report_duplicates and removed_count > 0:
            self._save_duplicate_report()
    
    def _resolve_duplicate_group(self, group: List[Citation]) -> Tuple[List[Citation], List[Tuple[Citation, Citation]]]:
        """Resolve duplicates within a group of citations with same fingerprint."""
        if len(group) <= 1:
            return group, []
        
        kept_citations = []
        removed_pairs = []
        
        if self.config.duplicate_strategy == "keep_first":
            kept_citations = [group[0]]
            removed_pairs = [(group[0], dup) for dup in group[1:]]
            
        elif self.config.duplicate_strategy == "keep_longest":
            longest = max(group, key=lambda c: len(c.text))
            kept_citations = [longest]
            removed_pairs = [(longest, dup) for dup in group if dup != longest]
            
        elif self.config.duplicate_strategy == "keep_most_complete":
            # Keep the one with DOI, or longest if no DOI
            with_doi = [c for c in group if c.doi]
            if with_doi:
                best = max(with_doi, key=lambda c: len(c.text))
            else:
                best = max(group, key=lambda c: len(c.text))
            
            kept_citations = [best]
            removed_pairs = [(best, dup) for dup in group if dup != best]
        
        return kept_citations, removed_pairs
    
    def _remove_similar_duplicates(self, citations: List[Citation]) -> List[Citation]:
        """Remove similar duplicates using similarity threshold, pre-filtered by year."""
        # Group by year to reduce pairwise comparisons
        by_year: Dict[Optional[int], List[Citation]] = {}
        for c in citations:
            by_year.setdefault(c.year, []).append(c)

        unique_citations = []
        for year, group in tqdm(by_year.items(), desc="Deduplicating (similarity)", unit="year-group"):
            for citation in group:
                is_duplicate = False
                for idx, u in enumerate(unique_citations):
                    if u.year != citation.year:
                        continue
                    if citation.is_duplicate_of(u, self.config.similarity_threshold):
                        if self._should_replace(u, citation):
                            unique_citations[idx] = citation
                            self.duplicates_removed.append((citation, u))
                        else:
                            self.duplicates_removed.append((u, citation))
                        is_duplicate = True
                        break
                if not is_duplicate:
                    unique_citations.append(citation)

        return unique_citations
    
    def _should_replace(self, existing: Citation, new: Citation) -> bool:
        """Determine if new citation should replace existing one."""
        if self.config.duplicate_strategy == "keep_first":
            return False  # Always keep existing
        
        elif self.config.duplicate_strategy == "keep_longest":
            return len(new.text) > len(existing.text)
        
        elif self.config.duplicate_strategy == "keep_most_complete":
            # Prefer citation with DOI
            if new.doi and not existing.doi:
                return True
            if existing.doi and not new.doi:
                return False
            # If both have DOI or neither, prefer longer
            return len(new.text) > len(existing.text)
        
        return False
    
    def _organize_citations(self) -> None:
        """Organize citations by category and year."""
        self.organized_data = defaultdict(lambda: defaultdict(list))
        
        for citation in self.citations:
            if citation.year:
                self.organized_data[citation.category][citation.year].append(citation)
            else:
                logger.warning(f"Could not extract year from: {citation.text[:50]}...")
        
        # Sort years (newest first), citations within each year alphabetically
        for category in self.organized_data:
            self.organized_data[category] = dict(sorted(
                self.organized_data[category].items(),
                reverse=True
            ))
            for year in self.organized_data[category]:
                self.organized_data[category][year].sort(key=lambda c: c.text.lower())
    
    def _ordered_categories(self):
        """Yield (category, years_dict) in configured display order."""
        seen = set()
        for cat in self.config.category_order:
            if cat in self.organized_data:
                seen.add(cat)
                yield cat, self.organized_data[cat]
        for cat, years in self.organized_data.items():
            if cat not in seen:
                yield cat, years

    def _save_duplicate_report(self) -> None:
        """Save detailed duplicate report."""
        if not self.duplicates_removed:
            return
        
        report_file = Path(self.config.output_dir) / 'duplicate_report.txt'
        
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write("DUPLICATE CITATIONS REPORT\n")
                f.write("=" * 50 + "\n\n")
                f.write(f"Total duplicates removed: {len(self.duplicates_removed)}\n")
                f.write(f"Similarity threshold: {self.config.similarity_threshold}\n")
                f.write(f"Strategy: {self.config.duplicate_strategy}\n\n")
                
                for i, (kept, removed) in enumerate(self.duplicates_removed, 1):
                    f.write(f"DUPLICATE SET #{i}\n")
                    f.write("-" * 30 + "\n")
                    f.write(f"KEPT: {kept.text}\n")
                    f.write(f"REMOVED: {removed.text}\n")
                    f.write(f"Similarity: {kept.similarity_score(removed):.3f}\n")
                    if kept.doi and removed.doi:
                        f.write(f"DOI Match: {kept.doi == removed.doi}\n")
                    f.write("\n")
            
            logger.info(f"Saved duplicate report to {report_file}")
            
        except Exception as e:
            logger.error(f"Error saving duplicate report: {e}")
    
    def get_duplicate_statistics(self) -> Dict:
        """Get statistics about duplicates found."""
        if not self.config.enable_duplicate_detection:
            return {"duplicate_detection_enabled": False}
        
        stats = {
            "duplicate_detection_enabled": True,
            "duplicates_removed": len(self.duplicates_removed),
            "similarity_threshold": self.config.similarity_threshold,
            "strategy": self.config.duplicate_strategy
        }
        
        # Analyze duplicate patterns
        doi_duplicates = sum(1 for kept, removed in self.duplicates_removed 
                           if kept.doi and removed.doi and kept.doi == removed.doi)
        
        stats["doi_based_duplicates"] = doi_duplicates
        stats["similarity_based_duplicates"] = len(self.duplicates_removed) - doi_duplicates
        
        return stats
    
    def get_category_name(self, category_key: str, language: str = 'en') -> str:
        """Get translated category name."""
        if category_key in self.config.translations:
            return self.config.translations[category_key].get(language, category_key)
        # Fallback: clean up the key
        return category_key.replace('_', ' ').title()
    
    def generate_statistics(self) -> Dict:
        """Generate comprehensive statistics (cached)."""
        if hasattr(self, '_cached_stats'):
            return self._cached_stats

        years_count: Dict[int, int] = {}
        authors_count: Dict[str, int] = {}

        for citation in self.citations:
            if citation.year:
                years_count[citation.year] = years_count.get(citation.year, 0) + 1
            authors_count[citation.author] = authors_count.get(citation.author, 0) + 1

        stats = {
            'total_citations': len(self.citations),
            'citations_with_years': len([c for c in self.citations if c.year]),
            'citations_without_years': len([c for c in self.citations if not c.year]),
            'categories': {},
            'years': years_count,
            'authors': authors_count,
            'duplicate_info': self.get_duplicate_statistics()
        }

        # Category statistics
        for category, years in self.organized_data.items():
            category_total = sum(len(citations) for citations in years.values())
            stats['categories'][category] = {
                'total': category_total,
                'years': list(years.keys()) if years else [],
                'year_range': (min(years.keys()), max(years.keys())) if years else None
            }

        self._cached_stats = stats
        return stats

    def save_to_csv(self, language: str = 'en') -> None:
        """Save citations to CSV file."""
        filename = Path(self.config.output_dir) / f'citations_{language}.csv'
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Category', 'Year', 'Author', 'Citation'])
                
                for category, years in tqdm(self._ordered_categories(), desc=f"Saving csv ({language})", unit="category"):
                    category_name = self.get_category_name(category, language)
                    for year, citations in years.items():
                        for citation in citations:
                            writer.writerow([
                                category_name,
                                year,
                                citation.author,
                                citation.text
                            ])
            
            logger.info(f"Saved CSV to {filename}")
            
        except Exception as e:
            logger.error(f"Error saving CSV: {e}")
            raise
    
    def save_to_html(self, language: str = 'en') -> None:
        """Save citations to plain HTML file (no CSS, meant for embedding)."""
        filename = Path(self.config.output_dir) / f'citations_{language}.html'

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                for category, years in tqdm(self._ordered_categories(), desc=f"Saving html ({language})", unit="category"):
                    total_count = sum(len(citations) for citations in years.values())
                    category_name = self.get_category_name(category, language)

                    anchor = self.config.category_anchors.get(category, '')
                    if anchor:
                        f.write(f'<h1><a name="{anchor}">{category_name} <strong class="count">({total_count})</strong></a></h1>\n')
                    else:
                        f.write(f'<h1>{category_name} <strong class="count">({total_count})</strong></h1>\n')

                    for year, citations in years.items():
                        f.write(f'<h3>{year} ({len(citations)})</h3>\n')
                        f.write('<ol>\n')
                        for citation in citations:
                            f.write(f'  <li>{html.escape(citation.text)}</li>\n')
                        f.write('</ol>\n')

            logger.info(f"Saved HTML to {filename}")

        except Exception as e:
            logger.error(f"Error saving HTML: {e}")
    
    def save_to_json(self) -> None:
        """Save organized data and statistics to JSON."""
        filename = Path(self.config.output_dir) / 'citations_data.json'
        
        # Convert data to JSON-serializable format
        data = {
            'statistics': self.generate_statistics(),
            'organized_data': {},
            'metadata': {
                'total_citations': len(self.citations),
                'generation_time': datetime.now(timezone.utc).isoformat()
            }
        }
        
        # Convert citations to dict format
        for category, years in self._ordered_categories():
            data['organized_data'][category] = {}
            for year, citations in years.items():
                data['organized_data'][category][str(year)] = [
                    {
                        'text': c.text,
                        'author': c.author,
                        'year': c.year
                    } for c in citations
                ]
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved JSON to {filename}")
            
        except Exception as e:
            logger.error(f"Error saving JSON: {e}")
            raise
    
    def print_summary(self) -> None:
        """Print analysis summary."""
        stats = self.generate_statistics()
        
        print("\n" + "="*50)
        print("CITATION ANALYSIS SUMMARY")
        print("="*50)
        
        print(f"Total citations: {stats['total_citations']}")
        print(f"Citations with years: {stats['citations_with_years']}")
        print(f"Citations without years: {stats['citations_without_years']}")
        
        # Duplicate detection summary
        if stats['duplicate_info']['duplicate_detection_enabled']:
            print(f"\nDuplicate Detection:")
            print(f"  Duplicates removed: {stats['duplicate_info']['duplicates_removed']}")
            print(f"  Similarity threshold: {stats['duplicate_info']['similarity_threshold']}")
            print(f"  Strategy: {stats['duplicate_info']['strategy']}")
            if stats['duplicate_info']['duplicates_removed'] > 0:
                print(f"  DOI-based duplicates: {stats['duplicate_info']['doi_based_duplicates']}")
                print(f"  Similarity-based duplicates: {stats['duplicate_info']['similarity_based_duplicates']}")
        else:
            print("\nDuplicate Detection: Disabled")
        
        print(f"\nCategories ({len(stats['categories'])}):")
        for category, data in stats['categories'].items():
            category_name = self.get_category_name(category, 'en')
            print(f"  {category_name}: {data['total']} citations")
            if data['year_range']:
                print(f"    Year range: {data['year_range'][0]} - {data['year_range'][1]}")
        
        print(f"\nTop 5 productive years:")
        top_years = sorted(stats['years'].items(), key=lambda x: x[1], reverse=True)[:5]
        for year, count in top_years:
            print(f"  {year}: {count} citations")
        
        print(f"\nTop 5 productive authors:")
        top_authors = sorted(stats['authors'].items(), key=lambda x: x[1], reverse=True)[:5]
        for author, count in top_authors:
            print(f"  {author}: {count} citations")
    
    def analyze(self) -> None:
        """Run complete analysis pipeline."""
        logger.info("Starting citation analysis...")
        
        self.load_data()
        
        # Generate outputs in all requested formats
        for language in self.config.languages:
            if 'csv' in self.config.output_formats:
                self.save_to_csv(language)
            if 'html' in self.config.output_formats:
                self.save_to_html(language)
        
        if 'json' in self.config.output_formats:
            self.save_to_json()
        
        self.print_summary()
        
        logger.info("Analysis complete!")

def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(description="Parse and analyze faculty citation data")
    parser.add_argument("--input", default="complete_faculty_data.json", help="Input JSON file from faculty_scraper.py")
    parser.add_argument("--output-dir", default="citation_analysis_output", help="Directory for output files")
    parser.add_argument("--threshold", type=float, default=0.85, help="Similarity threshold for duplicate detection (0.0-1.0)")
    args = parser.parse_args()

    config = AnalysisConfig(
        input_file=args.input,
        output_dir=args.output_dir,
        languages=['en', 'tr'],
        output_formats=['csv', 'html', 'json'],
        enable_duplicate_detection=True,
        similarity_threshold=args.threshold,
        duplicate_strategy="keep_most_complete",
        report_duplicates=True,
    )

    try:
        analyzer = CitationAnalyzer(config)
        analyzer.analyze()
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        return 1

    return 0

if __name__ == "__main__":
    exit(main())