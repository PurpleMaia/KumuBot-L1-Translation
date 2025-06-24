#!/usr/bin/env python3
"""
Convert existing Hawaiian-English JSONL file to MLX-LM format.
MLX-LM expects train.jsonl, valid.jsonl, and test.jsonl files in the data directory.
"""

import json
import os
from pathlib import Path

def load_jsonl(file_path):
    """Load JSONL file and return list of entries."""
    entries = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            entries.append(json.loads(line.strip()))
    return entries

def save_jsonl(entries, file_path):
    """Save entries to JSONL file."""
    with open(file_path, 'w', encoding='utf-8') as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')

def split_data(entries, train_ratio=0.8, valid_ratio=0.1):
    """Split data into train, validation, and test sets."""
    n = len(entries)
    train_size = int(n * train_ratio)
    valid_size = int(n * valid_ratio)
    
    train_data = entries[:train_size]
    valid_data = entries[train_size:train_size + valid_size]
    test_data = entries[train_size + valid_size:]
    
    return train_data, valid_data, test_data

def main():
    # Paths
    input_file = Path("hawaiian_english_training.jsonl")
    
    if not input_file.exists():
        print(f"Error: {input_file} not found. Please run convert_to_jsonl.py first.")
        return
    
    # Load data
    print(f"Loading data from {input_file}...")
    entries = load_jsonl(input_file)
    print(f"Total entries: {len(entries)}")
    
    # Split data (80% train, 10% validation, 10% test)
    train_data, valid_data, test_data = split_data(entries)
    
    print(f"Train set: {len(train_data)} entries")
    print(f"Validation set: {len(valid_data)} entries")
    print(f"Test set: {len(test_data)} entries")
    
    # Save split files
    save_jsonl(train_data, "train.jsonl")
    save_jsonl(valid_data, "valid.jsonl")
    save_jsonl(test_data, "test.jsonl")
    
    print("\nFiles created:")
    print("  - train.jsonl")
    print("  - valid.jsonl")
    print("  - test.jsonl")
    print("\nYou can now run MLX-LM with:")
    print("  mlx_lm.lora --model <model_name> --train --data finetuning/ --iters 600")

if __name__ == "__main__":
    main()