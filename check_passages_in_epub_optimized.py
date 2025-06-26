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
from rapidfuzz import fuzz


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
        description='Optimized: Check which passages from CSV datasets are found in an epub file, or compare CSV files',
        epilog='''
        This optimized version uses:
        - rapidfuzz for 10-100x faster fuzzy matching
        - n-gram indexing for efficient candidate selection
        - multiprocessing for parallel passage checking
        - progress bars to track execution
        '''
    )
    parser.add_argument('epub_path', nargs='?', help='Path to the epub file (not needed for --compare-csv)')
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
    parser.add_argument(
        '--compare-csv',
        action='store_true',
        help='Compare passages between CSV files instead of checking against epub'
    )
    parser.add_argument(
        '--show-all',
        action='store_true',
        help='Show all passages when comparing CSVs (not just differences)'
    )
    
    args = parser.parse_args()
    
    # If comparing CSVs, handle that separately
    if args.compare_csv:
        csv_paths = args.csv if args.csv else get_default_csv_paths()
        compare_csv_files(
            csv_paths=csv_paths,
            similarity_threshold=args.threshold,
            show_all=args.show_all
        )
        return
    
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


def compare_csv_files(
    csv_paths: List[str] = None,
    similarity_threshold: float = 0.95,
    show_all: bool = False,
    save_file: bool = False
) -> None:
    """
    Compare passages between CSV files to find which are the same and which are different.
    
    Args:
        csv_paths: List of CSV files to compare (default: both datasets)
        similarity_threshold: Minimum similarity to consider passages the same
        show_all: Show all passages, not just differences
    """
    if not csv_paths:
        csv_paths = get_default_csv_paths()
    
    # Ensure we have exactly 2 CSV files
    existing_paths = [p for p in csv_paths if Path(p).exists()]
    if len(existing_paths) != 2:
        print(f"Error: Need exactly 2 CSV files to compare, found {len(existing_paths)}")
        return
    
    print(f"Comparing passages between:")
    print(f"  1. {Path(existing_paths[0]).name}")
    print(f"  2. {Path(existing_paths[1]).name}")
    print(f"Similarity threshold: {similarity_threshold:.2f}")
    print("-" * 80)
    
    # Load passages from both files
    passages1 = load_csv_passages(existing_paths[0])
    passages2 = load_csv_passages(existing_paths[1])
    
    print(f"\nLoaded {len(passages1)} passages from {Path(existing_paths[0]).name}")
    print(f"Loaded {len(passages2)} passages from {Path(existing_paths[1]).name}")
    
    # Create hash maps for quick lookup
    hash_to_passage1 = {p['hawaiian_hash']: p for p in passages1}
    hash_to_passage2 = {p['hawaiian_hash']: p for p in passages2}
    
    # Find exact matches by hash
    common_hashes = set(hash_to_passage1.keys()) & set(hash_to_passage2.keys())
    unique_to_file1 = set(hash_to_passage1.keys()) - set(hash_to_passage2.keys())
    unique_to_file2 = set(hash_to_passage2.keys()) - set(hash_to_passage1.keys())
    
    print(f"\nExact matches (by hash): {len(common_hashes)} passages")
    print(f"Unique to {Path(existing_paths[0]).name}: {len(unique_to_file1)} passages")
    print(f"Unique to {Path(existing_paths[1]).name}: {len(unique_to_file2)} passages")
    
    # For non-exact matches, use fuzzy matching to find similar passages
    print("\nSearching for similar passages (not exact matches)...")
    similar_pairs = []
    
    # Check passages unique to file1 against all passages in file2
    with tqdm(total=len(unique_to_file1), desc="Checking fuzzy matches") as pbar:
        for hash1 in unique_to_file1:
            p1 = hash_to_passage1[hash1]
            best_match = None
            best_score = 0.0
            
            for p2 in passages2:
                if p2['hawaiian_hash'] not in common_hashes:
                    # Compare Hawaiian text
                    score = fuzz.ratio(p1['hawaiian'], p2['hawaiian']) / 100.0
                    if score > best_score and score >= similarity_threshold:
                        best_score = score
                        best_match = p2
            
            if best_match:
                similar_pairs.append((p1, best_match, best_score))
            pbar.update(1)
    
    print(f"\nFound {len(similar_pairs)} similar passage pairs (>= {similarity_threshold:.2f} similarity)")
    
    # Display results
    print("\n" + "=" * 80)
    print("DETAILED COMPARISON RESULTS:")
    print("=" * 80)
    
    if show_all or len(common_hashes) <= 10:
        print(f"\n1. EXACT MATCHES ({len(common_hashes)} passages):")
        for i, hash_val in enumerate(sorted(common_hashes)[:10]):
            p1 = hash_to_passage1[hash_val]
            p2 = hash_to_passage2[hash_val]
            print(f"\n   Match {i+1}:")
            hawaiian_preview1 = p1['hawaiian'][:100] + '...' if len(p1['hawaiian']) > 100 else p1['hawaiian']
            hawaiian_preview2 = p2['hawaiian'][:100] + '...' if len(p2['hawaiian']) > 100 else p2['hawaiian']
            print(f"   - {Path(existing_paths[0]).name} Row {p1['index']}: {hawaiian_preview1}")
            print(f"   - {Path(existing_paths[1]).name} Row {p2['index']}: {hawaiian_preview2}")
        if len(common_hashes) > 10 and not show_all:
            print(f"\n   ... and {len(common_hashes) - 10} more exact matches")
    else:
        print(f"\n1. EXACT MATCHES: {len(common_hashes)} passages (use --show-all to see details)")
    
    if similar_pairs:
        print(f"\n2. SIMILAR PASSAGES (not exact, but >= {similarity_threshold:.2f} similarity):")
        for i, (p1, p2, score) in enumerate(similar_pairs[:5]):
            print(f"\n   Similar pair {i+1} (similarity: {score:.3f}):")
            hawaiian_preview1 = p1['hawaiian'][:100] + '...' if len(p1['hawaiian']) > 100 else p1['hawaiian']
            hawaiian_preview2 = p2['hawaiian'][:100] + '...' if len(p2['hawaiian']) > 100 else p2['hawaiian']
            print(f"   - {Path(existing_paths[0]).name} Row {p1['index']}: {hawaiian_preview1}")
            print(f"   - {Path(existing_paths[1]).name} Row {p2['index']}: {hawaiian_preview2}")
        if len(similar_pairs) > 5:
            print(f"\n   ... and {len(similar_pairs) - 5} more similar pairs")
    
    if unique_to_file1:
        print(f"\n3. UNIQUE TO {Path(existing_paths[0]).name.upper()} ({len(unique_to_file1)} passages):")
        for i, hash_val in enumerate(sorted(unique_to_file1)[:5]):
            p = hash_to_passage1[hash_val]
            hawaiian_preview = p['hawaiian'][:100] + '...' if len(p['hawaiian']) > 100 else p['hawaiian']
            print(f"   - Row {p['index']}: {hawaiian_preview}")
        if len(unique_to_file1) > 5:
            print(f"   ... and {len(unique_to_file1) - 5} more")
    
    if unique_to_file2:
        print(f"\n4. UNIQUE TO {Path(existing_paths[1]).name.upper()} ({len(unique_to_file2)} passages):")
        for i, hash_val in enumerate(sorted(unique_to_file2)[:5]):
            p = hash_to_passage2[hash_val]
            hawaiian_preview = p['hawaiian'][:100] + '...' if len(p['hawaiian']) > 100 else p['hawaiian']
            print(f"   - Row {p['index']}: {hawaiian_preview}")
        if len(unique_to_file2) > 5:
            print(f"   ... and {len(unique_to_file2) - 5} more")
    
    # Summary statistics
    print("\n" + "=" * 80)
    print("SUMMARY STATISTICS:")
    print("=" * 80)
    total_unique = len(passages1) + len(passages2) - len(common_hashes)
    print(f"Total unique passages across both files: {total_unique}")
    print(f"Overlap percentage: {len(common_hashes) / total_unique * 100:.1f}%")
    
    # Export comparison results if requested
    if save_file:
        export_path = "passage_comparison.csv"
        print(f"\nExporting detailed comparison to {export_path}...")
        
        with open(export_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Status', 'File1_Row', 'File2_Row', 'Similarity', 
                            'Hawaiian_Text', 'English_Text', 'Source_File'])
            
            # Write exact matches
            for hash_val in common_hashes:
                p1 = hash_to_passage1[hash_val]
                p2 = hash_to_passage2[hash_val]
                writer.writerow([
                    'Exact Match',
                    p1['index'],
                    p2['index'],
                    '1.000',
                    p1['hawaiian'],
                    p1['english'],
                    'Both'
                ])
            
            # Write similar matches
            for p1, p2, score in similar_pairs:
                writer.writerow([
                    'Similar',
                    p1['index'],
                    p2['index'],
                    f'{score:.3f}',
                    p1['hawaiian'],
                    p1['english'],
                    'Both (fuzzy)'
                ])
            
            # Write unique to file1
            for hash_val in unique_to_file1:
                p = hash_to_passage1[hash_val]
                writer.writerow([
                    'Unique',
                    p['index'],
                    '-',
                    '0.000',
                    p['hawaiian'],
                    p['english'],
                    Path(existing_paths[0]).name
                ])
            
            # Write unique to file2
            for hash_val in unique_to_file2:
                p = hash_to_passage2[hash_val]
                writer.writerow([
                    'Unique',
                    '-',
                    p['index'],
                    '0.000',
                    p['hawaiian'],
                    p['english'],
                    Path(existing_paths[1]).name
                ])
        
        print(f"Comparison results exported to {export_path}")


if __name__ == '__main__':
    main()