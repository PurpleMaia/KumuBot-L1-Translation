#!/usr/bin/env python3
"""
Shared utilities for working with EPUB files and Hawaiian-English passage datasets.
"""

import csv
import hashlib
import re
import sys
from pathlib import Path
from typing import List, Tuple, Dict, Optional
import zipfile
import xml.etree.ElementTree as ET
from difflib import SequenceMatcher


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


def normalize_text_for_matching(text: str) -> str:
    """
    Normalize text for fuzzy matching.
    """
    # Remove extra whitespace, punctuation, and convert to lowercase
    normalized = re.sub(r'[^\w\s]', '', text.lower())
    normalized = ' '.join(normalized.split())
    return normalized


def find_substring_match(passage: str, full_text: str, threshold: float = 0.85) -> Tuple[bool, float]:
    """
    Check if a passage appears as a substring in the full text with fuzzy matching.
    Returns (is_found, similarity_score)
    """
    passage_norm = normalize_text_for_matching(passage)
    full_text_norm = normalize_text_for_matching(full_text)
    
    # Quick exact substring check first
    if passage_norm in full_text_norm:
        return True, 1.0
    
    # Try sliding window fuzzy matching for longer passages
    if len(passage_norm) > 100:  # Only for substantial passages
        passage_words = passage_norm.split()
        full_words = full_text_norm.split()
        
        # Use a sliding window of similar length
        window_size = len(passage_words)
        best_ratio = 0.0
        
        for i in range(len(full_words) - window_size + 1):
            window = ' '.join(full_words[i:i + window_size])
            ratio = SequenceMatcher(None, passage_norm, window).ratio()
            best_ratio = max(best_ratio, ratio)
            
            if best_ratio >= threshold:
                return True, best_ratio
    
    return False, 0.0


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