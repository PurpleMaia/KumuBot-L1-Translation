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
    Assumes alternating pages after the preface: English (left) then Hawaiian (right).
    """
    pairs = []
    
    # Find where main content starts (after preface)
    start_index = 0
    if start_after_preface:
        for i, page in enumerate(pages):
            content_lower = page['content'].lower()
            if 'preface' in content_lower or 'introduction' in content_lower:
                # Start after this page
                start_index = i + 1
                break
    
    # Process pages in pairs (English, Hawaiian)
    i = start_index
    while i < len(pages) - 1:
        english_page = pages[i]['content']
        hawaiian_page = pages[i + 1]['content']
        
        # Skip if either page is too short (likely not content)
        if len(english_page) < 50 or len(hawaiian_page) < 50:
            i += 1
            continue
        
        # Create the pair
        pairs.append((hawaiian_page, english_page))
        
        # Move to next pair
        i += 2
    
    return pairs


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