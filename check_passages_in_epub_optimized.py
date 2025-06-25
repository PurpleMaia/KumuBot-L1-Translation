#!/usr/bin/env python3
"""
Optimized version: Check which passages from the CSV datasets are found in a given epub file.
Uses multiprocessing, n-gram indexing, and rapidfuzz for much faster performance.
"""

import csv
import sys
import time
from pathlib import Path
from typing import List, Dict, Tuple
import multiprocessing as mp
from functools import partial
from tqdm import tqdm

# Import optimized utilities
from epub_utils_optimized import (
    extract_text_from_epub,
    compute_passage_hash,
    normalize_text_for_matching,
    find_substring_match_optimized,
    load_csv_passages,
    get_default_csv_paths,
    NGramIndex
)


def check_single_passage(
    passage: Dict[str, str],
    full_text: str,
    check_language: str,
    similarity_threshold: float,
    ngram_index: NGramIndex = None
) -> Dict:
    """
    Check a single passage against the full text.
    This function is designed to be used with multiprocessing.
    """
    hawaiian_found = False
    english_found = False
    hawaiian_score = 0.0
    english_score = 0.0
    
    if check_language in ['hawaiian', 'both']:
        hawaiian_found, hawaiian_score = find_substring_match_optimized(
            passage['hawaiian'], full_text, similarity_threshold, ngram_index
        )
    
    if check_language in ['english', 'both']:
        english_found, english_score = find_substring_match_optimized(
            passage['english'], full_text, similarity_threshold, ngram_index
        )
    
    # Determine if passage is found based on check_language setting
    if check_language == 'both':
        is_found = hawaiian_found or english_found
    elif check_language == 'hawaiian':
        is_found = hawaiian_found
    else:  # english
        is_found = english_found
    
    return {
        'index': passage['index'],
        'hawaiian_preview': passage['hawaiian'][:100] + '...' if len(passage['hawaiian']) > 100 else passage['hawaiian'],
        'english_preview': passage['english'][:100] + '...' if len(passage['english']) > 100 else passage['english'],
        'hawaiian_found': hawaiian_found,
        'english_found': english_found,
        'hawaiian_score': hawaiian_score,
        'english_score': english_score,
        'is_found': is_found
    }


def check_passages_batch(
    passages_batch: List[Dict[str, str]],
    full_text: str,
    check_language: str,
    similarity_threshold: float,
    use_ngram_index: bool = True
) -> List[Dict]:
    """
    Check a batch of passages. This function runs in a separate process.
    """
    # Build n-gram index for this process if requested
    ngram_index = None
    if use_ngram_index and len(full_text) > 10000:  # Only use index for large texts
        ngram_index = NGramIndex(n=5)  # Use 5-grams for better specificity
        ngram_index.build(normalize_text_for_matching(full_text))
    
    results = []
    for passage in passages_batch:
        result = check_single_passage(
            passage, full_text, check_language, similarity_threshold, ngram_index
        )
        results.append(result)
    
    return results


def check_passages_in_epub(
    epub_path: str,
    csv_paths: List[str],
    check_language: str = 'both',
    similarity_threshold: float = 0.85,
    show_details: bool = False,
    num_processes: int = None,
    use_ngram_index: bool = True
) -> Dict[str, Dict]:
    """
    Optimized version: Check which passages from CSV files are found in the epub.
    
    Args:
        epub_path: Path to the epub file
        csv_paths: List of CSV files to check
        check_language: 'hawaiian', 'english', or 'both'
        similarity_threshold: Minimum similarity score to consider a match
        show_details: Whether to show detailed match information
        num_processes: Number of processes to use (None for auto)
        use_ngram_index: Whether to use n-gram indexing for faster search
        
    Returns:
        Dictionary with results for each CSV file
    """
    print(f"Extracting text from {epub_path}...")
    start_time = time.time()
    
    # Extract all text from epub
    pages = extract_text_from_epub(epub_path)
    
    # Combine all pages into one text for searching
    full_text = ' '.join(page['content'] for page in pages)
    
    print(f"Extracted {len(full_text)} characters from {len(pages)} pages")
    print(f"Time taken: {time.time() - start_time:.2f} seconds")
    
    # Pre-build n-gram index for the main process if using single process
    main_ngram_index = None
    if use_ngram_index and (num_processes == 1 or num_processes is None):
        print("Building n-gram index for fast searching...")
        index_start = time.time()
        main_ngram_index = NGramIndex(n=5)
        main_ngram_index.build(normalize_text_for_matching(full_text))
        print(f"Index built in {time.time() - index_start:.2f} seconds")
    
    print("-" * 80)
    
    results = {}
    
    for csv_path in csv_paths:
        if not Path(csv_path).exists():
            print(f"Warning: {csv_path} not found, skipping...")
            continue
            
        print(f"\nChecking passages from {Path(csv_path).name}...")
        csv_start_time = time.time()
        
        # Load passages from CSV
        passages = load_csv_passages(csv_path)
        print(f"Loaded {len(passages)} passages")
        
        # Determine number of processes
        if num_processes is None:
            num_processes = min(mp.cpu_count(), 8)  # Cap at 8 processes
        
        if num_processes > 1 and len(passages) > 10:
            # Use multiprocessing for larger datasets
            print(f"Using {num_processes} processes for parallel search...")
            
            # Split passages into batches
            batch_size = max(1, len(passages) // (num_processes * 4))  # More batches than processes
            batches = [passages[i:i+batch_size] for i in range(0, len(passages), batch_size)]
            
            # Create a pool of workers
            with mp.Pool(processes=num_processes) as pool:
                # Prepare the partial function with fixed arguments
                check_func = partial(
                    check_passages_batch,
                    full_text=full_text,
                    check_language=check_language,
                    similarity_threshold=similarity_threshold,
                    use_ngram_index=use_ngram_index
                )
                
                # Process batches with progress bar
                batch_results = []
                with tqdm(total=len(passages), desc="Checking passages") as pbar:
                    for batch_result in pool.imap(check_func, batches):
                        batch_results.extend(batch_result)
                        pbar.update(len(batch_result))
            
            # Organize results
            all_results = batch_results
        else:
            # Use single process for small datasets
            print("Using single process...")
            all_results = []
            
            with tqdm(total=len(passages), desc="Checking passages") as pbar:
                for passage in passages:
                    result = check_single_passage(
                        passage, full_text, check_language, 
                        similarity_threshold, main_ngram_index
                    )
                    all_results.append(result)
                    pbar.update(1)
        
        # Separate found and not found passages
        found_passages = [r for r in all_results if r['is_found']]
        not_found_passages = [r for r in all_results if not r['is_found']]
        
        # Store results
        results[csv_path] = {
            'total_passages': len(passages),
            'found_count': len(found_passages),
            'not_found_count': len(not_found_passages),
            'found_passages': found_passages,
            'not_found_passages': not_found_passages
        }
        
        # Print summary
        print(f"\nFound: {len(found_passages)}/{len(passages)} passages ({len(found_passages)/len(passages)*100:.1f}%)")
        print(f"Time taken: {time.time() - csv_start_time:.2f} seconds")
        
        if show_details and found_passages:
            print("\nFound passages:")
            for p in found_passages[:5]:  # Show first 5
                print(f"  - Row {p['index']}: ", end='')
                if p['hawaiian_found'] and p['english_found']:
                    print(f"Both found (H: {p['hawaiian_score']:.2f}, E: {p['english_score']:.2f})")
                elif p['hawaiian_found']:
                    print(f"Hawaiian found ({p['hawaiian_score']:.2f})")
                else:
                    print(f"English found ({p['english_score']:.2f})")
                print(f"    Hawaiian: {p['hawaiian_preview']}")
            
            if len(found_passages) > 5:
                print(f"  ... and {len(found_passages) - 5} more")
        
        if show_details and not_found_passages:
            print(f"\nNot found passages (first 5 of {len(not_found_passages)}):")
            for p in not_found_passages[:5]:
                print(f"  - Row {p['index']}: {p['hawaiian_preview']}")
    
    print(f"\nTotal time: {time.time() - start_time:.2f} seconds")
    return results


def main():
    """
    Main entry point for the script.
    """
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Optimized: Check which passages from CSV datasets are found in an epub file',
        epilog='''
        This optimized version uses:
        - rapidfuzz for 10-100x faster fuzzy matching
        - n-gram indexing for efficient candidate selection
        - multiprocessing for parallel passage checking
        - progress bars to track execution
        '''
    )
    parser.add_argument('epub_path', help='Path to the epub file')
    parser.add_argument(
        '--csv', 
        nargs='+', 
        help='CSV files to check (default: both dataset.csv and finetuning_dataset.csv)'
    )
    parser.add_argument(
        '--language', 
        choices=['hawaiian', 'english', 'both'],
        default='both',
        help='Which language to check (default: both)'
    )
    parser.add_argument(
        '--threshold',
        type=float,
        default=0.85,
        help='Similarity threshold for fuzzy matching (0-1, default: 0.85)'
    )
    parser.add_argument(
        '--details',
        action='store_true',
        help='Show detailed information about matches'
    )
    parser.add_argument(
        '--export',
        help='Export results to a CSV file'
    )
    parser.add_argument(
        '--processes',
        type=int,
        help='Number of processes to use (default: auto)'
    )
    parser.add_argument(
        '--no-index',
        action='store_true',
        help='Disable n-gram indexing (slower but uses less memory)'
    )
    
    args = parser.parse_args()
    
    # Default CSV files if not specified
    if not args.csv:
        args.csv = get_default_csv_paths()
    
    # Check passages
    results = check_passages_in_epub(
        args.epub_path,
        args.csv,
        check_language=args.language,
        similarity_threshold=args.threshold,
        show_details=args.details,
        num_processes=args.processes,
        use_ngram_index=not args.no_index
    )
    
    # Export results if requested
    if args.export:
        with open(args.export, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Source_CSV', 'Row_Index', 'Found_In_Epub', 'Hawaiian_Found', 
                           'English_Found', 'Hawaiian_Score', 'English_Score', 
                           'Hawaiian_Preview', 'English_Preview'])
            
            for csv_path, result in results.items():
                csv_name = Path(csv_path).name
                
                # Write found passages
                for p in result['found_passages']:
                    writer.writerow([
                        csv_name,
                        p['index'],
                        'Yes',
                        'Yes' if p['hawaiian_found'] else 'No',
                        'Yes' if p['english_found'] else 'No',
                        f"{p['hawaiian_score']:.3f}",
                        f"{p['english_score']:.3f}",
                        p['hawaiian_preview'],
                        p['english_preview']
                    ])
                
                # Write not found passages
                for p in result['not_found_passages']:
                    writer.writerow([
                        csv_name,
                        p['index'],
                        'No',
                        'No',
                        'No',
                        '0.000',
                        '0.000',
                        p['hawaiian_preview'],
                        p['english_preview']
                    ])
        
        print(f"\nResults exported to {args.export}")
    
    # Print final summary
    print("\n" + "=" * 80)
    print("SUMMARY:")
    total_found = sum(r['found_count'] for r in results.values())
    total_passages = sum(r['total_passages'] for r in results.values())
    print(f"Total passages found across all CSVs: {total_found}/{total_passages} ({total_found/total_passages*100:.1f}%)")


if __name__ == '__main__':
    main()