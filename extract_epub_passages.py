#!/usr/bin/env python3
"""
Extract English-Hawaiian passage pairs from epub files.
"""

import sys
from pathlib import Path
from typing import List, Tuple, Optional

# Import shared utilities
from epub_utils import (
    extract_text_from_epub,
    identify_passage_pairs,
    compute_passage_hash,
    load_existing_passages,
    save_passages_to_csv,
    get_default_csv_paths
)


def extract_passages_from_epub(
    epub_path: str,
    num_passages: Optional[int] = None,
    skip_duplicates: bool = True
) -> List[Tuple[str, str]]:
    """
    Main function to extract passages from an epub file.
    
    Args:
        epub_path: Path to the epub file
        num_passages: Maximum number of passages to extract (None for all)
        skip_duplicates: Whether to skip passages already in the dataset
        
    Returns:
        List of (hawaiian, english) tuples
    """
    print(f"Extracting passages from {epub_path}...")
    
    # Extract pages from epub
    pages = extract_text_from_epub(epub_path)
    print(f"Found {len(pages)} pages in the epub")
    
    # Identify passage pairs
    pairs = identify_passage_pairs(pages)
    print(f"Identified {len(pairs)} potential passage pairs")
    
    # Load existing passages if checking for duplicates
    existing_hashes = set()
    if skip_duplicates:
        # Check both datasets for duplicates
        datasets_to_check = [Path(p) for p in get_default_csv_paths()]
        
        for dataset_path in datasets_to_check:
            if dataset_path.exists():
                existing = load_existing_passages(str(dataset_path))
                existing_hashes.update(existing.keys())
                print(f"Loaded {len(existing)} passages from {dataset_path.name}")
        
        print(f"Total: {len(existing_hashes)} unique existing passages for duplicate detection")
    
    # Filter out duplicates and limit number
    filtered_pairs = []
    for hawaiian, english in pairs:
        if skip_duplicates:
            hash_val = compute_passage_hash(hawaiian)
            if hash_val in existing_hashes:
                print(f"Skipping duplicate passage: {hawaiian[:50]}...")
                continue
        
        filtered_pairs.append((hawaiian, english))
        
        if num_passages and len(filtered_pairs) >= num_passages:
            break
    
    print(f"Extracted {len(filtered_pairs)} new passages")
    return filtered_pairs



def main():
    """
    Main entry point for the script.
    """
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Extract English-Hawaiian passage pairs from epub files',
        epilog='''
        Note: This script extracts passages and adds them to the finetuning dataset by default.
        To add passages to data/dataset.csv for benchmarking, you have two options:
        1. Use --to-main-dataset flag to add them directly (only Hawaiian and English columns)
        2. Run translation scripts afterwards to populate model translation columns
        '''
    )
    parser.add_argument('epub_path', help='Path to the epub file')
    parser.add_argument('-n', '--num-passages', type=int, help='Number of passages to extract')
    parser.add_argument('--no-dedup', action='store_true', help='Disable duplicate detection')
    parser.add_argument('-o', '--output', help='Output CSV file (default: append to finetuning_dataset.csv)')
    parser.add_argument('--preview', action='store_true', help='Preview passages without saving')
    parser.add_argument('--to-main-dataset', action='store_true', 
                       help='Add passages to data/dataset.csv (Hawaiian/English columns only)')
    parser.add_argument('--check-existing', action='store_true',
                       help='Check which existing CSV passages are in this epub (runs check_passages_in_epub.py)')
    
    args = parser.parse_args()
    
    # Check existing passages mode
    if args.check_existing:
        import subprocess
        import os
        
        check_script = Path(__file__).parent / 'check_passages_in_epub.py'
        if check_script.exists():
            print("Running check_passages_in_epub.py...")
            subprocess.run([sys.executable, str(check_script), args.epub_path, '--details'])
        else:
            print("Error: check_passages_in_epub.py not found")
        return
    
    # Extract passages
    passages = extract_passages_from_epub(
        args.epub_path,
        num_passages=args.num_passages,
        skip_duplicates=not args.no_dedup
    )
    
    if not passages:
        print("No new passages found to extract")
        return
    
    # Preview mode
    if args.preview:
        print("\nPreview of extracted passages:")
        print("-" * 80)
        for i, (hawaiian, english) in enumerate(passages[:3]):
            print(f"\nPassage {i+1}:")
            print(f"Hawaiian: {hawaiian[:200]}...")
            print(f"English: {english[:200]}...")
        if len(passages) > 3:
            print(f"\n... and {len(passages) - 3} more passages")
        return
    
    # Determine output path and save
    if args.output:
        # Custom output path
        output_path = args.output
        save_passages_to_csv(passages, output_path, append=True)
    elif args.to_main_dataset:
        # Add to main dataset (Hawaiian and English columns only)
        output_path = Path(__file__).parent / 'data' / 'dataset.csv'
        save_passages_to_csv(passages, str(output_path), append=True, is_finetuning=False)
        print("\nIMPORTANT: Added passages to data/dataset.csv with only Hawaiian and English columns.")
        print("To populate model translation columns, run the translation scripts in translations/")
    else:
        # Default: add to finetuning dataset
        output_path = Path(__file__).parent / 'finetuning' / 'finetuning_dataset.csv'
        save_passages_to_csv(passages, str(output_path), append=True, is_finetuning=True)


if __name__ == '__main__':
    main()