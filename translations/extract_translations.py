#!/usr/bin/env python3
import json
import os
import csv
import re
import pandas as pd

# Default list of model folders
DEFAULT_MODEL_FOLDERS = [
    "gemini-2.0-flash-thinking",
    "gpt4o",
    "o1",
    "llama-3.3",
    "gpt-4o-mini",
    "gpt-4.5-preview",
    "deepseek-r1-distill-llama-70b",
    "gpt-4o-mini-finetuned",
]


def discover_folders() -> list[str]:
    """Return subdirectories that contain translation_0.json"""
    folders = []
    for entry in os.listdir("."):
        if os.path.isdir(entry) and os.path.isfile(os.path.join(entry, "translation_0.json")):
            folders.append(entry)
    return folders


# Determine which folders to use
folders_env = os.getenv("MODEL_FOLDERS")
discover_env = os.getenv("DISCOVER_FOLDERS", "false").lower() in {"1", "true", "yes"}

if folders_env:
    model_folders = [f.strip() for f in folders_env.split(",") if f.strip()]
elif discover_env:
    model_folders = discover_folders()
else:
    model_folders = DEFAULT_MODEL_FOLDERS


def extract_translation(text):
    """
    Extract text between the last set of <translation> and </translation> tags.
    If no tags are found, return None to indicate the original text should be used.
    """
    pattern = r'<translation>(.*?)</translation>'
    matches = re.findall(pattern, text, re.DOTALL)
    
    if matches:
        # Return the last match (from the last set of translation tags)
        return matches[-1].strip()
    # Return None to indicate no translation tags were found
    return None

def main():
    # Read the original dataset.csv
    try:
        df = pd.read_csv('../data/dataset.csv')
        print(f"Read original dataset.csv with {len(df)} rows")
    except FileNotFoundError:
        print("Error: Original dataset.csv not found")
        return
    except Exception as e:
        print(f"Error reading dataset.csv: {str(e)}")
        return
    
    # Initialize columns for each model
    for folder in model_folders:
        df[folder] = ""
    
    # Process each folder
    for folder in model_folders:
        print(f"Processing folder: {folder}")
        
        # Process each JSON file in the folder
        for i in range(10):  # translation_0.json to translation_9.json
            json_file = os.path.join(folder, f"translation_{i}.json")
            
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                row_id = data['row_id']
                model_translation = data[f'{folder}_translation']
                
                # Extract translation if tags exist, otherwise use the original text
                extracted_translation = extract_translation(model_translation)
                if extracted_translation is None:
                    # If no translation tags found, use the original model_translation
                    extracted_translation = model_translation
                
                # Add the translation to the dataframe
                if 0 <= row_id < len(df):
                    df.at[row_id, folder] = extracted_translation
                    print(f"  Added translation from {json_file} to row {row_id}")
                else:
                    print(f"  Warning: row_id {row_id} out of range for dataset")
                
            except FileNotFoundError:
                print(f"  Warning: File not found: {json_file}")
            except json.JSONDecodeError:
                print(f"  Error: Invalid JSON in file: {json_file}")
            except Exception as e:
                print(f"  Error processing {json_file}: {str(e)}")
    
    # Save the updated dataframe back to dataset.csv
    df.to_csv('../data/dataset.csv', index=False)
    print(f"Successfully updated dataset.csv with {len(model_folders)} new columns")

if __name__ == "__main__":
    main()