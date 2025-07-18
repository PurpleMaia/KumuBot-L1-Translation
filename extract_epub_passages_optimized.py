#!/usr/bin/env python3
"""
Optimized version: Extract English-Hawaiian passage pairs from epub files.
Uses optimized utilities for better performance on large epub files.
"""

import sys
import time
from pathlib import Path
from typing import List, Tuple, Optional
from tqdm import tqdm
import multiprocessing as mp
from functools import partial

# Import optimized utilities
from epub_utils_optimized import (
    extract_text_from_epub,
    identify_passage_pairs,
    compute_passage_hash,
    load_existing_passages,
    save_passages_to_csv,
    get_default_csv_paths,
    normalize_text_for_matching,
    find_substring_match_optimized,
    NGramIndex,
)


def validate_passage_pair(
    pair: Tuple[str, str], min_length: int = 50, max_length: int = 3000
) -> bool:
    """
    Validate if a passage pair is suitable for extraction.
    """
    hawaiian, english = pair

    # Check minimum length
    if len(hawaiian) < min_length or len(english) < min_length:
        return False

    # Check maximum length (skip extremely long passages like chants/genealogies)
    if max_length > 0 and (len(hawaiian) > max_length or len(english) > max_length):
        return False

    # Check if passages are too similar (might be same language)
    # This helps filter out pages where both sides are in the same language
    hawaiian_norm = normalize_text_for_matching(hawaiian)
    english_norm = normalize_text_for_matching(english)

    # If normalized texts are too similar, they might be the same language
    if hawaiian_norm == english_norm:
        return False

    # Quick heuristic: Hawaiian text typically has more vowels
    hawaiian_vowel_ratio = sum(1 for c in hawaiian.lower() if c in "aeiou") / len(
        hawaiian
    )
    english_vowel_ratio = sum(1 for c in english.lower() if c in "aeiou") / len(english)

    # If vowel ratios are too similar, might be same language
    if abs(hawaiian_vowel_ratio - english_vowel_ratio) < 0.05:
        return False

    return True


def process_passages_batch(
    pairs_batch: List[Tuple[str, str]],
    existing_hashes: set,
    skip_duplicates: bool,
    max_length: int = 3000,
) -> List[Tuple[str, str]]:
    """
    Process a batch of passage pairs in parallel.
    Note: This function cannot prevent internal duplicates across batches
    due to parallel processing. Internal deduplication happens at the end.
    """
    filtered_pairs = []

    for hawaiian, english in pairs_batch:
        # Validate the pair
        if not validate_passage_pair((hawaiian, english), max_length=max_length):
            continue

        # Check for duplicates against existing CSV data only
        # (internal duplicates will be handled after parallel processing)
        if skip_duplicates:
            hash_val = compute_passage_hash(hawaiian)
            if hash_val in existing_hashes:
                continue

        filtered_pairs.append((hawaiian, english))

    return filtered_pairs


def extract_passages_from_epub(
    epub_path: str,
    num_passages: Optional[int] = None,
    skip_duplicates: bool = True,
    num_processes: Optional[int] = None,
    use_html_structure: bool = True,
    max_length: int = 3000,
) -> List[Tuple[str, str]]:
    """
    Optimized function to extract passages from an epub file.

    Args:
        epub_path: Path to the epub file
        num_passages: Maximum number of passages to extract (None for all)
        skip_duplicates: Whether to skip passages already in the dataset
        num_processes: Number of processes for parallel processing
        use_html_structure: Whether to use HTML-aware extraction
        max_length: Maximum character length per passage (0 to disable limit)

    Returns:
        List of (hawaiian, english) tuples
    """
    print(f"Extracting passages from {epub_path}...")
    start_time = time.time()

    if use_html_structure:
        # Use HTML-aware extraction for properly aligned text
        from epub_utils_optimized import extract_text_from_epub_html_aware

        pairs = extract_text_from_epub_html_aware(epub_path)
        print(f"Extracted {len(pairs)} aligned passage pairs from HTML tables")
    else:
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

        print(
            f"Total: {len(existing_hashes)} unique existing passages for duplicate detection"
        )

    # Determine number of processes
    if num_processes is None:
        num_processes = min(mp.cpu_count(), 4)  # Cap at 4 processes

    # Process passages
    if use_html_structure:
        # For HTML-extracted pairs, we already have clean pairs
        # Just need to filter for duplicates, length, and limit
        filtered_pairs = []
        seen_hashes = (
            set()
        )  # Track hashes within this extraction to prevent internal duplicates

        for hawaiian, english in pairs:
            # Validate length
            if not validate_passage_pair((hawaiian, english), max_length=max_length):
                continue

            if skip_duplicates:
                hash_val = compute_passage_hash(hawaiian)
                # Check against existing CSV data
                if hash_val in existing_hashes:
                    continue
                # Check against already processed passages in this extraction
                if hash_val in seen_hashes:
                    continue
                seen_hashes.add(hash_val)

            filtered_pairs.append((hawaiian, english))

            if num_passages and len(filtered_pairs) >= num_passages:
                break
    elif num_processes > 1 and len(pairs) > 100:
        # Use multiprocessing for large datasets
        print(f"Using {num_processes} processes for parallel filtering...")

        # Split pairs into batches
        batch_size = max(1, len(pairs) // (num_processes * 4))
        batches = [pairs[i : i + batch_size] for i in range(0, len(pairs), batch_size)]

        # Create a pool of workers
        with mp.Pool(processes=num_processes) as pool:
            # Prepare the partial function
            process_func = partial(
                process_passages_batch,
                existing_hashes=existing_hashes,
                skip_duplicates=skip_duplicates,
                max_length=max_length,
            )

            # Process batches with progress bar
            all_filtered = []
            with tqdm(total=len(pairs), desc="Processing passages") as pbar:
                for i, batch_result in enumerate(pool.imap(process_func, batches)):
                    all_filtered.extend(batch_result)
                    # More accurate progress update
                    batch_len = (
                        len(batches[i]) if i < len(batches) else len(batches[-1])
                    )
                    pbar.update(batch_len)

                    # Stop if we have enough passages
                    if num_passages and len(all_filtered) >= num_passages:
                        pool.terminate()
                        break

        # Deduplicate internally within the extracted passages
        if skip_duplicates:
            print("Removing internal duplicates from parallel processing...")
            seen_hashes = set()
            deduped_pairs = []
            duplicates_removed = 0

            for hawaiian, english in all_filtered:
                hash_val = compute_passage_hash(hawaiian)
                if hash_val not in seen_hashes:
                    seen_hashes.add(hash_val)
                    deduped_pairs.append((hawaiian, english))
                else:
                    duplicates_removed += 1

            if duplicates_removed > 0:
                print(
                    f"Removed {duplicates_removed} internal duplicates from parallel processing"
                )

            all_filtered = deduped_pairs

        filtered_pairs = all_filtered[:num_passages] if num_passages else all_filtered
    else:
        # Use single process for small datasets
        print("Processing passages...")
        filtered_pairs = []

        seen_hashes = (
            set()
        )  # Track hashes within this extraction to prevent internal duplicates

        with tqdm(total=len(pairs), desc="Processing passages") as pbar:
            for hawaiian, english in pairs:
                # Validate the pair
                if not validate_passage_pair(
                    (hawaiian, english), max_length=max_length
                ):
                    pbar.update(1)
                    continue

                if skip_duplicates:
                    hash_val = compute_passage_hash(hawaiian)
                    # Check against existing CSV data
                    if hash_val in existing_hashes:
                        pbar.update(1)
                        continue
                    # Check against already processed passages in this extraction
                    if hash_val in seen_hashes:
                        pbar.update(1)
                        continue
                    seen_hashes.add(hash_val)

                filtered_pairs.append((hawaiian, english))
                pbar.update(1)

                if num_passages and len(filtered_pairs) >= num_passages:
                    break
    extracted_message = "new passages after filtering"
    if skip_duplicates:
        extracted_message += " duplicates"
        if max_length != 0:
            extracted_message += " and"
    if max_length != 0:
        extracted_message += " passages with length greater than " + str(max_length)
    print(f"\nExtracted {len(filtered_pairs)} " + extracted_message)
    print(f"Time taken: {time.time() - start_time:.2f} seconds")
    return filtered_pairs


def main():
    """
    Main entry point for the script.
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Optimized: Extract English-Hawaiian passage pairs from epub files",
        epilog="""
        This optimized version includes:
        - Parallel processing for large epub files
        - Better passage validation
        - Progress tracking
        - Performance improvements
        
        Note: This script extracts passages and adds them to the finetuning dataset by default.
        To add passages to data/dataset.csv for benchmarking, you have two options:
        1. Use --to-main-dataset flag to add them directly (only Hawaiian and English columns)
        2. Run translation scripts afterwards to populate model translation columns
        """,
    )
    parser.add_argument("epub_path", help="Path to the epub file")
    parser.add_argument(
        "-n", "--num-passages", type=int, help="Number of passages to extract"
    )
    parser.add_argument(
        "--no-dedup", action="store_true", help="Disable duplicate detection"
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Output CSV file (default: append to finetuning_dataset.csv)",
    )
    parser.add_argument(
        "--preview", action="store_true", help="Preview passages without saving"
    )
    parser.add_argument(
        "--to-main-dataset",
        action="store_true",
        help="Add passages to data/dataset.csv (Hawaiian/English columns only)",
    )
    parser.add_argument(
        "--check-existing",
        action="store_true",
        help="Check which existing CSV passages are in this epub (runs optimized checker)",
    )
    parser.add_argument(
        "--processes", type=int, help="Number of processes to use (default: auto)"
    )
    parser.add_argument(
        "--max-length",
        type=int,
        default=3000,
        help="Maximum character length per passage (default: 3000, use 0 to disable)",
    )

    args = parser.parse_args()

    # Check existing passages mode
    if args.check_existing:
        import subprocess
        import os

        # Try optimized version first
        check_script = Path(__file__).parent / "check_passages_in_epub_optimized.py"

        if check_script.exists():
            print(f"Running {check_script.name}...")
            cmd = [sys.executable, str(check_script), args.epub_path, "--details"]
            if "optimized" in check_script.name and args.processes:
                cmd.extend(["--processes", str(args.processes)])
            subprocess.run(cmd)
        else:
            print("Error: check_passages_in_epub script not found")
        return

    # Extract passages
    passages = extract_passages_from_epub(
        args.epub_path,
        num_passages=args.num_passages,
        skip_duplicates=not args.no_dedup,
        num_processes=args.processes,
        max_length=args.max_length,
    )

    if not passages:
        print("No new passages found to extract")
        return

    # Preview mode
    if args.preview:
        print("\nPreview of extracted passages:")
        print("-" * 80)
        for i, (hawaiian, english) in enumerate(passages[:5]):
            print(f"\nPassage {i + 1}:")
            print(f"Hawaiian: {hawaiian[:200]}...")
            print(f"English: {english[:200]}...")
        if len(passages) > 5:
            print(f"\n... and {len(passages) - 5} more passages")
        return

    # Determine output path and save
    if args.output:
        # Custom output path
        output_path = args.output
        save_passages_to_csv(passages, output_path, append=True)
    elif args.to_main_dataset:
        # Add to main dataset (Hawaiian and English columns only)
        output_path = Path(__file__).parent / "data" / "dataset.csv"
        save_passages_to_csv(
            passages, str(output_path), append=True, is_finetuning=False
        )
        print(
            "\nIMPORTANT: Added passages to data/dataset.csv with only Hawaiian and English columns."
        )
        print(
            "To populate model translation columns, run the translation scripts in translations/"
        )
    else:
        # Default: add to finetuning dataset
        output_path = Path(__file__).parent / "finetuning" / "finetuning_dataset.csv"
        save_passages_to_csv(
            passages, str(output_path), append=True, is_finetuning=True
        )


if __name__ == "__main__":
    main()
