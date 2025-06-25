#!/usr/bin/env python3
"""
Check which passages from the CSV datasets are found in a given epub file.
"""

import csv
import sys
from pathlib import Path
from typing import List, Dict

# Import shared utilities
from epub_utils import (
    extract_text_from_epub,
    compute_passage_hash,
    normalize_text_for_matching,
    find_substring_match,
    load_csv_passages,
    get_default_csv_paths
)


def check_passages_in_epub(
    epub_path: str,
    csv_paths: List[str],
    check_language: str = 'both',
    similarity_threshold: float = 0.85,
    show_details: bool = False
) -> Dict[str, Dict]:
    """
    Check which passages from CSV files are found in the epub.
    
    Args:
        epub_path: Path to the epub file
        csv_paths: List of CSV files to check
        check_language: 'hawaiian', 'english', or 'both'
        similarity_threshold: Minimum similarity score to consider a match
        show_details: Whether to show detailed match information
        
    Returns:
        Dictionary with results for each CSV file
    """
    print(f"Extracting text from {epub_path}...")
    
    # Extract all text from epub
    pages = extract_text_from_epub(epub_path)
    
    # Combine all pages into one text for searching
    full_text = ' '.join(page['content'] for page in pages)
    
    print(f"Extracted {len(full_text)} characters from {len(pages)} pages")
    print("-" * 80)
    
    results = {}
    
    for csv_path in csv_paths:
        if not Path(csv_path).exists():
            print(f"Warning: {csv_path} not found, skipping...")
            continue
            
        print(f"\nChecking passages from {Path(csv_path).name}...")
        
        # Load passages from CSV
        passages = load_csv_passages(csv_path)
        print(f"Loaded {len(passages)} passages")
        
        # Check each passage
        found_passages = []
        not_found_passages = []

        passage_count = 1
        
        for passage in passages:
            hawaiian_found = False
            english_found = False
            hawaiian_score = 0.0
            english_score = 0.0
            
            if check_language in ['hawaiian', 'both']:
                hawaiian_found, hawaiian_score = find_substring_match(
                    passage['hawaiian'], full_text, similarity_threshold
                )
            
            if check_language in ['english', 'both']:
                english_found, english_score = find_substring_match(
                    passage['english'], full_text, similarity_threshold
                )
            
            # Determine if passage is found based on check_language setting
            if check_language == 'both':
                is_found = hawaiian_found or english_found
            elif check_language == 'hawaiian':
                is_found = hawaiian_found
            else:  # english
                is_found = english_found
            
            passage_info = {
                'index': passage['index'],
                'hawaiian_preview': passage['hawaiian'][:100] + '...' if len(passage['hawaiian']) > 100 else passage['hawaiian'],
                'english_preview': passage['english'][:100] + '...' if len(passage['english']) > 100 else passage['english'],
                'hawaiian_found': hawaiian_found,
                'english_found': english_found,
                'hawaiian_score': hawaiian_score,
                'english_score': english_score
            }
            
            if is_found:
                found_passages.append(passage_info)
            else:
                not_found_passages.append(passage_info)
            print('finished passage '+str(passage_count))
            passage_count += 1
        
        # Store results
        results[csv_path] = {
            'total_passages': len(passages),
            'found_count': len(found_passages),
            'not_found_count': len(not_found_passages),
            'found_passages': found_passages,
            'not_found_passages': not_found_passages
        }
        
        # Print summary
        print(f"Found: {len(found_passages)}/{len(passages)} passages ({len(found_passages)/len(passages)*100:.1f}%)")
        
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
    
    return results


def main():
    """
    Main entry point for the script.
    """
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Check which passages from CSV datasets are found in an epub file',
        epilog='''
        This tool helps identify which passages in your datasets come from a specific epub.
        It uses fuzzy matching to handle minor differences in formatting or OCR errors.
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
        show_details=args.details
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