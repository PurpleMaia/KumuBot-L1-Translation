#!/usr/bin/env python3
"""
Optimized utilities for working with EPUB files and Hawaiian-English passage datasets.
Uses rapidfuzz for faster fuzzy matching and n-gram indexing for efficient search.
"""

import csv
import hashlib
import re
import sys
from pathlib import Path
from typing import List, Tuple, Dict, Optional, Set
import zipfile
import xml.etree.ElementTree as ET
from collections import defaultdict
from rapidfuzz import fuzz, process
import multiprocessing as mp
from functools import lru_cache


class NGramIndex:
    """N-gram index for fast approximate string matching."""
    
    def __init__(self, n=3):
        self.n = n
        self.index = defaultdict(set)
        self.word_positions = {}  # Maps word positions to original text positions
        
    def build(self, text: str, text_id: str = "main"):
        """Build n-gram index from text."""
        words = text.lower().split()
        
        # Store word positions for later retrieval
        self.word_positions[text_id] = []
        current_pos = 0
        for word in text.split():  # Use original text to preserve case
            self.word_positions[text_id].append((current_pos, current_pos + len(word)))
            current_pos += len(word) + 1
        
        # Index n-grams
        for i in range(len(words)):
            # Create n-grams of various sizes around this position
            for size in range(1, self.n + 1):
                if i + size <= len(words):
                    ngram = ' '.join(words[i:i+size])
                    self.index[ngram].add((text_id, i, size))
    
    def find_candidates(self, query: str, min_overlap=0.5) -> List[Tuple[str, int, int]]:
        """Find candidate positions for a query string."""
        query_words = query.lower().split()
        query_ngrams = set()
        
        # Generate all n-grams from query
        for i in range(len(query_words)):
            for size in range(1, min(self.n + 1, len(query_words) - i + 1)):
                ngram = ' '.join(query_words[i:i+size])
                query_ngrams.add(ngram)
        
        # Find positions containing query n-grams
        position_scores = defaultdict(float)
        for ngram in query_ngrams:
            if ngram in self.index:
                for text_id, pos, size in self.index[ngram]:
                    # Score based on n-gram size (larger n-grams are more specific)
                    position_scores[(text_id, pos)] += size
        
        # Filter candidates by minimum overlap
        min_score = len(query_words) * min_overlap
        candidates = []
        for (text_id, pos), score in position_scores.items():
            if score >= min_score:
                candidates.append((text_id, pos, int(score)))
        
        # Sort by score (descending)
        candidates.sort(key=lambda x: x[2], reverse=True)
        return candidates[:100]  # Return top 100 candidates


def extract_text_from_epub_html_aware(epub_path: str) -> List[Tuple[str, str]]:
    """
    Extract aligned Hawaiian-English pairs using HTML table structure.
    Returns list of (hawaiian, english) tuples.
    """
    from html.parser import HTMLParser
    
    class BilingualTableExtractor(HTMLParser):
        def __init__(self):
            super().__init__()
            self.in_table = False
            self.in_english_cell = False
            self.in_hawaiian_cell = False
            self.current_english = []
            self.current_hawaiian = []
            self.pairs = []
            self.current_text = []
            self.skip_tags = {'a', 'sup', 'sub'}
            self.in_skip_tag = False
            
        def handle_starttag(self, tag, attrs):
            attrs_dict = dict(attrs)
            
            if tag == 'table' and attrs_dict.get('class') == 'alignedText':
                self.in_table = True
                
            elif self.in_table and tag == 'td':
                if attrs_dict.get('class', '').startswith('first'):
                    self.in_english_cell = True
                    self.in_hawaiian_cell = False
                elif attrs_dict.get('class', '').startswith('second'):
                    self.in_hawaiian_cell = True
                    self.in_english_cell = False
                    
            elif tag in self.skip_tags:
                self.in_skip_tag = True
                
        def handle_endtag(self, tag):
            if tag == 'table' and self.in_table:
                self.in_table = False
                self._save_current_pair()
                
            elif tag == 'td':
                if self.in_english_cell:
                    self.current_english.extend(self.current_text)
                    self.in_english_cell = False
                elif self.in_hawaiian_cell:
                    self.current_hawaiian.extend(self.current_text)
                    self.in_hawaiian_cell = False
                self.current_text = []
                
            elif tag == 'tr' and self.in_table:
                self._save_current_pair()
                
            elif tag in self.skip_tags:
                self.in_skip_tag = False
                
        def handle_data(self, data):
            if self.in_skip_tag:
                return
                
            if self.in_english_cell or self.in_hawaiian_cell:
                cleaned = data.strip()
                if cleaned:
                    self.current_text.append(cleaned)
                    
        def _save_current_pair(self):
            english_text = ' '.join(self.current_english).strip()
            hawaiian_text = ' '.join(self.current_hawaiian).strip()
            
            if len(english_text) > 50 and len(hawaiian_text) > 50:
                if not any(skip in english_text.lower()[:100] for skip in [
                    'contents', 'volume', 'page', 'ebookmaker', 'chapter', 'mokuna'
                ]):
                    # Clean text
                    english_text = re.sub(r'\s+', ' ', english_text)
                    hawaiian_text = re.sub(r'\s+', ' ', hawaiian_text)
                    english_text = re.sub(r'\[\s*\d+\s*\]', '', english_text)
                    hawaiian_text = re.sub(r'\[\s*\d+\s*\]', '', hawaiian_text)
                    self.pairs.append((hawaiian_text, english_text))
                    
            self.current_english = []
            self.current_hawaiian = []
    
    all_pairs = []
    
    with zipfile.ZipFile(epub_path, 'r') as epub:
        html_files = [f for f in epub.namelist() if f.endswith('.html') or f.endswith('.xhtml')]
        
        for html_file in sorted(html_files):
            try:
                content = epub.read(html_file).decode('utf-8')
                parser = BilingualTableExtractor()
                parser.feed(content)
                all_pairs.extend(parser.pairs)
            except Exception as e:
                print(f"Error processing {html_file}: {e}")
                continue
    
    return all_pairs


def extract_text_from_epub(epub_path: str) -> List[Dict[str, str]]:
    """
    Extract text content from EPUB file, preserving page structure.
    Returns a list of pages with their content.
    """
    pages = []
    
    with zipfile.ZipFile(epub_path, 'r') as epub:
        # Find the content.opf file which contains the spine (reading order)
        container_xml = epub.read('META-INF/container.xml').decode('utf-8')
        container_root = ET.fromstring(container_xml)
        
        # Get the path to content.opf
        rootfile_path = container_root.find('.//{urn:oasis:names:tc:opendocument:xmlns:container}rootfile').get('full-path')
        
        # Read content.opf to get the spine order
        content_opf = epub.read(rootfile_path).decode('utf-8')
        opf_root = ET.fromstring(content_opf)
        
        # Get the base directory for content files
        base_dir = Path(rootfile_path).parent
        
        # Extract spine items in order
        spine = opf_root.find('.//{http://www.idpf.org/2007/opf}spine')
        manifest = opf_root.find('.//{http://www.idpf.org/2007/opf}manifest')
        
        # Create a mapping of id to href
        item_map = {}
        for item in manifest.findall('.//{http://www.idpf.org/2007/opf}item'):
            item_id = item.get('id')
            href = item.get('href')
            if item_id and href:
                item_map[item_id] = href
        
        # Process spine items in order
        for itemref in spine.findall('.//{http://www.idpf.org/2007/opf}itemref'):
            idref = itemref.get('idref')
            if idref in item_map:
                href = item_map[idref]
                if base_dir != Path('.'):
                    full_path = str(base_dir / href)
                else:
                    full_path = href
                
                try:
                    # Read the XHTML content
                    content = epub.read(full_path).decode('utf-8')
                    
                    # Parse the XHTML
                    # Remove namespace declarations for easier parsing
                    content = re.sub(r'xmlns[^=]*="[^"]*"', '', content)
                    
                    try:
                        root = ET.fromstring(content)
                    except ET.ParseError:
                        # If parsing fails, try to extract text with regex
                        text = re.sub(r'<[^>]+>', ' ', content)
                        text = ' '.join(text.split())
                        if text.strip():
                            pages.append({
                                'file': full_path,
                                'content': text.strip()
                            })
                        continue
                    
                    # Extract text from the page
                    page_text = []
                    
                    def extract_text_recursive(element, texts):
                        if element.text:
                            texts.append(element.text.strip())
                        for child in element:
                            extract_text_recursive(child, texts)
                            if child.tail:
                                texts.append(child.tail.strip())
                    
                    extract_text_recursive(root, page_text)
                    
                    # Join and clean the text
                    full_text = ' '.join(page_text)
                    full_text = ' '.join(full_text.split())  # Normalize whitespace
                    
                    if full_text.strip():
                        pages.append({
                            'file': full_path,
                            'content': full_text.strip()
                        })
                
                except Exception as e:
                    print(f"Error reading {full_path}: {e}", file=sys.stderr)
    
    return pages


def identify_passage_pairs(pages: List[Dict[str, str]], start_after_preface: bool = True) -> List[Tuple[str, str]]:
    """
    Identify English-Hawaiian passage pairs from the extracted pages.
    For Fornander collection, this contains bilingual parallel text within pages.
    """
    pairs = []
    
    # Find pages with substantial bilingual content
    for page in pages:
        content = page['content']
        
        # Skip short pages (likely headers, footers, TOC)
        if len(content) < 1000:
            continue
            
        # Skip if it doesn't contain both English and Hawaiian indicators
        content_lower = content.lower()
        has_hawaiian_indicators = any(word in content_lower for word in [
            'mokuna', 'moolelo', 'alii', 'aina', 'keiki', 'wahine', 'kane', 
            'kaua', 'laua', 'mau', 'nei', 'paha', 'kela', 'keia'
        ])
        has_english_indicators = any(word in content_lower for word in [
            'chapter', 'legend', 'king', 'queen', 'island', 'according', 
            'tradition', 'history', 'people', 'chief'
        ])
        
        if not (has_hawaiian_indicators and has_english_indicators):
            continue
            
        # Extract parallel passages from bilingual content
        page_pairs = extract_bilingual_pairs(content)
        pairs.extend(page_pairs)
    
    return pairs


def extract_bilingual_pairs(content: str) -> List[Tuple[str, str]]:
    """
    Extract English-Hawaiian passage pairs from bilingual text.
    The Fornander collection has English paragraphs followed by Hawaiian translations.
    """
    pairs = []
    
    # Use a more targeted approach based on the actual structure observed
    # Pattern: English sentence(s) followed by Hawaiian translation(s)
    
    # Look for specific patterns where English is followed by Hawaiian
    # Split content where we see transitions from English to Hawaiian
    
    # First, let's split the content into segments around sentence boundaries
    # but keep context together
    
    # Split on periods followed by capital letters, but be more careful
    segments = re.split(r'(?<=\.)\s+(?=[A-Z])', content)
    
    current_english = ""
    current_hawaiian = ""
    state = "unknown"  # Can be "english", "hawaiian", or "unknown"
    
    for segment in segments:
        segment = segment.strip()
        if len(segment) < 20:  # Skip very short segments
            continue
            
        # Score this segment
        eng_score = score_english_text(segment)
        haw_score = score_hawaiian_text(segment)
        
        # Determine what language this segment is
        if eng_score > haw_score and eng_score > 0.2:
            segment_lang = "english"
        elif haw_score > eng_score and haw_score > 0.2:
            segment_lang = "hawaiian"
        else:
            segment_lang = "unknown"
        
        # State machine to build pairs
        if state == "unknown":
            if segment_lang == "english":
                current_english = segment
                state = "english"
            elif segment_lang == "hawaiian":
                current_hawaiian = segment
                state = "hawaiian"
                
        elif state == "english":
            if segment_lang == "english":
                # Continue building English text
                current_english += " " + segment
            elif segment_lang == "hawaiian":
                # Found Hawaiian after English - this might be a pair
                current_hawaiian = segment
                state = "hawaiian"
            else:
                # Unknown segment - might be transition
                if len(current_english) > 100:
                    current_english += " " + segment
                    
        elif state == "hawaiian":
            if segment_lang == "hawaiian":
                # Continue building Hawaiian text
                current_hawaiian += " " + segment
            elif segment_lang == "english":
                # We have a complete pair: previous English + previous Hawaiian
                if (len(current_english) > 100 and len(current_hawaiian) > 100 and
                    not any(skip in current_english.lower()[:100] for skip in [
                        'contents', 'chapter', 'fornander collection'
                    ])):
                    pairs.append((current_hawaiian, current_english))
                
                # Start new English
                current_english = segment
                current_hawaiian = ""
                state = "english"
            else:
                # Unknown - might be continuing Hawaiian
                current_hawaiian += " " + segment
    
    # Don't forget the last pair if we ended in Hawaiian state
    if (state == "hawaiian" and len(current_english) > 100 and len(current_hawaiian) > 100 and
        not any(skip in current_english.lower()[:100] for skip in [
            'contents', 'chapter', 'fornander collection'
        ])):
        pairs.append((current_hawaiian, current_english))
    
    return pairs


def score_english_text(text: str) -> float:
    """
    Score how likely text is to be English (0-1 scale).
    """
    text_lower = text.lower()
    english_words = [
        'the', 'and', 'of', 'to', 'a', 'in', 'was', 'that', 'he', 'it',
        'with', 'for', 'as', 'his', 'on', 'be', 'at', 'by', 'this', 'had',
        'from', 'they', 'she', 'or', 'an', 'were', 'been', 'have', 'their',
        'said', 'each', 'which', 'do', 'how', 'if', 'will', 'up', 'other',
        'about', 'out', 'many', 'then', 'them', 'these', 'so', 'some', 'her',
        'would', 'make', 'like', 'into', 'time', 'has', 'two', 'more', 'very',
        'after', 'words', 'first', 'where', 'much', 'through', 'before', 'right',
        'good', 'here', 'better', 'every', 'those', 'came', 'came'
    ]
    
    words = text_lower.split()
    if not words:
        return 0.0
        
    english_count = sum(1 for word in words if word in english_words)
    return english_count / len(words)


def score_hawaiian_text(text: str) -> float:
    """
    Score how likely text is to be Hawaiian (0-1 scale).
    """
    text_lower = text.lower()
    
    # Hawaiian words and particles
    hawaiian_words = [
        'aloha', 'mahalo', 'ohana', 'keiki', 'wahine', 'kane', 'alii', 'aina',
        'kai', 'mauka', 'makai', 'pau', 'hale', 'wiki', 'nui', 'iki', 'mau',
        'keia', 'kela', 'nei', 'la', 'no', 'hoi', 'mai', 'aku', 'ae', 'ana',
        'ai', 'ia', 'oe', 'au', 'kaua', 'laua', 'lakou', 'oukou', 'maua',
        'ma', 'i', 'o', 'a', 'e', 'ke', 'ka', 'na', 'he', 'ua', 'ai',
        'moolelo', 'mokuna', 'hanau', 'make', 'ola', 'hele', 'hiki', 'ike',
        'lohe', 'olelo', 'pono', 'makai', 'hoolohe', 'kokoke', 'mamua',
        'mahope', 'manawa', 'wahi', 'ano', 'mea', 'hana', 'noho', 'komo'
    ]
    
    words = text_lower.split()
    if not words:
        return 0.0
        
    hawaiian_count = sum(1 for word in words if word in hawaiian_words)
    base_score = hawaiian_count / len(words)
    
    # Boost score based on Hawaiian linguistic features
    # High vowel ratio (Hawaiian has many vowels)
    vowel_count = sum(1 for char in text_lower if char in 'aeiou')
    vowel_ratio = vowel_count / len(text_lower) if text_lower else 0
    
    # Presence of doubled vowels (common in Hawaiian)
    double_vowels = len(re.findall(r'[aeiou]{2,}', text_lower))
    double_vowel_boost = min(double_vowels / len(words) * 2, 0.2) if words else 0
    
    # Presence of apostrophes (okina)
    apostrophe_count = text.count("'") + text.count("'")
    apostrophe_boost = min(apostrophe_count / len(words) * 0.5, 0.1) if words else 0
    
    # Combine scores
    final_score = base_score + (vowel_ratio - 0.4) * 0.3 + double_vowel_boost + apostrophe_boost
    return max(0.0, min(1.0, final_score))


def compute_passage_hash(text: str) -> str:
    """
    Compute a hash of the passage text for duplicate detection.
    Normalizes the text before hashing to catch near-duplicates.
    """
    # Normalize text: lowercase, remove extra whitespace, remove punctuation
    normalized = re.sub(r'[^\w\s]', '', text.lower())
    normalized = ' '.join(normalized.split())
    
    # Compute hash
    return hashlib.md5(normalized.encode('utf-8')).hexdigest()


@lru_cache(maxsize=1000)
def normalize_text_for_matching(text: str) -> str:
    """
    Normalize text for fuzzy matching. Cached for performance.
    """
    # Remove extra whitespace, punctuation, and convert to lowercase
    normalized = re.sub(r'[^\w\s]', '', text.lower())
    normalized = ' '.join(normalized.split())
    return normalized


def find_substring_match_optimized(
    passage: str, 
    full_text: str, 
    threshold: float = 0.85,
    ngram_index: Optional[NGramIndex] = None,
    early_termination_score: float = 0.95
) -> Tuple[bool, float]:
    """
    Optimized substring matching using rapidfuzz and n-gram indexing.
    Returns (is_found, similarity_score)
    """
    passage_norm = normalize_text_for_matching(passage)
    full_text_norm = normalize_text_for_matching(full_text)
    
    # Quick exact substring check first
    if passage_norm in full_text_norm:
        return True, 1.0
    
    # For short passages, use direct fuzzy search
    if len(passage_norm) < 50:
        # Use rapidfuzz's process.extractOne for short strings
        result = process.extractOne(
            passage_norm, 
            [full_text_norm], 
            scorer=fuzz.partial_ratio,
            score_cutoff=threshold * 100
        )
        if result:
            return True, result[1] / 100.0
        return False, 0.0
    
    # For longer passages, use n-gram indexing if available
    if ngram_index:
        candidates = ngram_index.find_candidates(passage_norm)
        if not candidates:
            # Fall back to sliding window if no candidates found
            return find_substring_match_sliding_window(
                passage_norm, full_text_norm, threshold, early_termination_score
            )
        
        # Check top candidates with rapidfuzz
        full_words = full_text_norm.split()
        best_score = 0.0
        
        for _, start_pos, _ in candidates[:20]:  # Check top 20 candidates
            # Extract window around candidate position
            window_start = max(0, start_pos - 5)
            window_end = min(len(full_words), start_pos + len(passage_norm.split()) + 5)
            window_text = ' '.join(full_words[window_start:window_end])
            
            # Use rapidfuzz for scoring
            score = fuzz.ratio(passage_norm, window_text) / 100.0
            best_score = max(best_score, score)
            
            # Early termination if we find a very good match
            if best_score >= early_termination_score:
                return True, best_score
        
        if best_score >= threshold:
            return True, best_score
    else:
        # Fall back to optimized sliding window
        return find_substring_match_sliding_window(
            passage_norm, full_text_norm, threshold, early_termination_score
        )
    
    return False, best_score if ngram_index else 0.0


def find_substring_match_sliding_window(
    passage_norm: str, 
    full_text_norm: str, 
    threshold: float = 0.85,
    early_termination_score: float = 0.95
) -> Tuple[bool, float]:
    """
    Optimized sliding window search using rapidfuzz.
    """
    passage_words = passage_norm.split()
    full_words = full_text_norm.split()
    
    if len(passage_words) > len(full_words):
        return False, 0.0
    
    # Use a sliding window with step size for faster search
    window_size = len(passage_words)
    step_size = max(1, window_size // 10)  # Skip some positions for speed
    best_ratio = 0.0
    
    for i in range(0, len(full_words) - window_size + 1, step_size):
        window = ' '.join(full_words[i:i + window_size])
        
        # Use rapidfuzz for faster comparison
        ratio = fuzz.ratio(passage_norm, window) / 100.0
        
        if ratio > best_ratio:
            best_ratio = ratio
            # If we skipped positions and found a good match, check nearby positions
            if step_size > 1 and ratio > threshold * 0.9:
                for j in range(max(0, i - step_size), min(i + step_size, len(full_words) - window_size + 1)):
                    if j != i:
                        nearby_window = ' '.join(full_words[j:j + window_size])
                        nearby_ratio = fuzz.ratio(passage_norm, nearby_window) / 100.0
                        best_ratio = max(best_ratio, nearby_ratio)
        
        # Early termination
        if best_ratio >= early_termination_score:
            return True, best_ratio
    
    return best_ratio >= threshold, best_ratio


# Keep the original function name for compatibility but use the optimized version
def find_substring_match(passage: str, full_text: str, threshold: float = 0.85) -> Tuple[bool, float]:
    """
    Check if a passage appears as a substring in the full text with fuzzy matching.
    Returns (is_found, similarity_score)
    """
    return find_substring_match_optimized(passage, full_text, threshold)


def load_existing_passages(dataset_path: str) -> Dict[str, Tuple[str, str]]:
    """
    Load existing passages from the dataset and compute their hashes.
    Returns a dict mapping hash -> (hawaiian, english) tuple.
    """
    existing = {}
    
    with open(dataset_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Handle both dataset formats
            # data/dataset.csv uses "Hawaiian" and "English"
            # finetuning/finetuning_dataset.csv uses "L1 Hawaiian_Text" and "Reference_Translation"
            hawaiian = row.get('Hawaiian', '') or row.get('L1 Hawaiian_Text', '')
            english = row.get('English', '') or row.get('Reference_Translation', '')
            
            hawaiian = hawaiian.strip()
            english = english.strip()
            
            if hawaiian and english:
                # Compute hash of Hawaiian text for deduplication
                hash_val = compute_passage_hash(hawaiian)
                existing[hash_val] = (hawaiian, english)
    
    return existing


def load_csv_passages(csv_path: str) -> List[Dict[str, str]]:
    """
    Load passages from a CSV file with full metadata.
    """
    passages = []
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            # Handle both dataset formats
            hawaiian = row.get('Hawaiian', '') or row.get('L1 Hawaiian_Text', '')
            english = row.get('English', '') or row.get('Reference_Translation', '')
            
            hawaiian = hawaiian.strip()
            english = english.strip()
            
            if hawaiian and english:
                passages.append({
                    'index': i + 1,  # 1-based index
                    'hawaiian': hawaiian,
                    'english': english,
                    'hawaiian_hash': compute_passage_hash(hawaiian),
                    'english_hash': compute_passage_hash(english)
                })
    
    return passages


def save_passages_to_csv(
    passages: List[Tuple[str, str]], 
    output_path: str,
    append: bool = True,
    is_finetuning: bool = None
):
    """
    Save passages to a CSV file.
    
    Args:
        passages: List of (hawaiian, english) tuples
        output_path: Path to the output CSV file
        append: Whether to append to existing file or overwrite
        is_finetuning: Whether this is for finetuning dataset (auto-detected if None)
    """
    # Auto-detect format based on path if not specified
    if is_finetuning is None:
        is_finetuning = 'finetuning' in output_path
    
    mode = 'a' if append and Path(output_path).exists() else 'w'
    
    # For data/dataset.csv, we need to handle all columns
    if not is_finetuning and mode == 'a' and Path(output_path).exists():
        # Read existing file to get all column headers
        with open(output_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            existing_headers = next(reader)
            num_columns = len(existing_headers)
    else:
        existing_headers = None
        num_columns = None
    
    with open(output_path, mode, encoding='utf-8', newline='') as f:
        if mode == 'w':
            # Write header for new file
            writer = csv.writer(f)
            if is_finetuning:
                writer.writerow(['L1 Hawaiian_Text', 'Reference_Translation'])
            else:
                writer.writerow(['Hawaiian', 'English'])
        else:
            # For appending, no header needed
            writer = csv.writer(f)
        
        for hawaiian, english in passages:
            if is_finetuning:
                # Simple case for finetuning dataset
                writer.writerow([hawaiian, english])
            else:
                # For data/dataset.csv, pad with empty columns for model translations
                if num_columns and num_columns > 2:
                    # Create row with hawaiian, english, and empty values for model columns
                    row = [hawaiian, english] + [''] * (num_columns - 2)
                    writer.writerow(row)
                else:
                    # If no existing columns or new file, just write the two columns
                    writer.writerow([hawaiian, english])
    
    print(f"Saved {len(passages)} passages to {output_path}")


def get_default_csv_paths() -> List[str]:
    """
    Get the default CSV file paths for the project.
    """
    project_root = Path(__file__).parent
    return [
        str(project_root / 'data' / 'dataset.csv'),
        str(project_root / 'finetuning' / 'finetuning_dataset.csv')
    ]