#!/usr/bin/env python3
import os
import pandas as pd
import re
import time
import csv
from openai import OpenAI
from dotenv import load_dotenv
from tqdm import tqdm

# Load environment variables from .env file (if any)
load_dotenv()

# Get API key from environment variable
api_key = os.getenv("OPENAI_API_KEY_KOA")
if not api_key:
    raise ValueError("Please set the OPENAI_API_KEY environment variable")

# Initialize OpenAI client
client = OpenAI(api_key=api_key)

# Define the judge model
JUDGE_MODEL = "gpt-4o-mini"
# JUDGE_MODEL = "o1"

# Define the existing models to compare against
existing_models = [
    "gemini-2.0-flash-thinking",
    "gpt4o",
    "o1",
    "llama-3.3",
    "gpt-4o-mini",
    "gpt-4.5-preview",
    "deepseek-r1-distill-llama-70b"
]

# Define the new model to add
NEW_MODEL = "gpt-4o-mini-finetuned"

# Define which rows to use for judging
ROW_INDICES = [0,1,2,3,4,5,6,7,8,9]  # Default: use all 10 examples

def create_comparison_prompt(reference, translation1, translation2):
    prompt = (
        f"Compare these two translations to the reference. Which one is more accurate and natural? Give an explanation and write your final answer in <answer> </answer> tags. This means your final answer needs to either be <answer>first</answer> representing that the first translation was better or <answer>second</answer> representing that the second translation was better."
        f"Here is the reference translation: {reference}. "
        f"Here is the first translation: {translation1}. "
        f"Here is the second translation: {translation2}."
    )
    return prompt

def get_llm_judgment(reference, translation1, translation2):
    """
    Get judgment from LLM about which translation is better
    Includes rate limit handling with exponential backoff
    """
    prompt = create_comparison_prompt(reference, translation1, translation2)
    max_retries = 5
    retry_delay = 1
    
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=JUDGE_MODEL,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant specializing in evaluating translation quality."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,  # Use low temperature for more consistent judgments
            )
            
            judgment_text = response.choices[0].message.content
            
            # Extract the answer from the tags
            pattern = r'<answer>(.*?)</answer>'
            match = re.search(pattern, judgment_text, re.DOTALL)
            
            if match:
                answer = match.group(1).strip().lower()
                if answer == "first" or answer == "second":
                    return answer
                else:
                    print(f"Warning: Invalid answer format: {answer}. Expected 'first' or 'second'.")
                    return "invalid"
            else:
                print(f"Warning: No answer tags found in response: {judgment_text}")
                return "invalid"
                
        except Exception as e:
            if "rate limit" in str(e).lower() and attempt < max_retries - 1:
                sleep_time = retry_delay * (2 ** attempt)  # Exponential backoff
                print(f"Rate limit exceeded. Retrying in {sleep_time} seconds...")
                time.sleep(sleep_time)
            else:
                print(f"Error getting judgment: {str(e)}")
                return "error"
    
    return "error"

def main():
    # Read the dataset with translations
    print("Reading dataset.csv...")
    df = pd.read_csv('../data/dataset.csv')
    
    if 'English' not in df.columns:
        print("Error: 'English' column not found in dataset.csv")
        return
    
    # Check if new model column exists in the dataset
    if NEW_MODEL not in df.columns:
        print(f"Error: '{NEW_MODEL}' column not found in dataset.csv")
        return
    
    # Check which existing model columns are available in dataset
    available_models = [model for model in existing_models if model in df.columns]
    if not available_models:
        print("Error: No existing model translation columns found in dataset.csv")
        return
    
    print(f"Found {len(available_models)} existing model columns in dataset")
    print(f"Will compare new model '{NEW_MODEL}' against existing models")
    
    # Validate row indices
    valid_indices = [idx for idx in ROW_INDICES if idx < len(df)]
    if not valid_indices:
        print("Error: No valid row indices specified")
        return
    
    print(f"Using {len(valid_indices)} rows for judging: {valid_indices}")
    
    # Read existing roundrobin.csv
    try:
        print("Reading existing roundrobin.csv...")
        result_df = pd.read_csv('roundrobin.csv')
    except FileNotFoundError:
        print("Warning: roundrobin.csv not found. Creating new file...")
        # Create a new DataFrame with just row_id column
        result_df = pd.DataFrame({'row_id': valid_indices})
    
    # Initialize new results dictionary
    new_results = {}
    
    # For every existing model, compare with new model in both directions
    for existing_model in tqdm(available_models, desc=f"Processing {NEW_MODEL} comparisons"):
        # Forward comparison (new model as first, existing model as second)
        pair_key = f"{NEW_MODEL} vs {existing_model}"
        new_results[pair_key] = {}
        
        # Reverse comparison (existing model as first, new model as second)
        pair_key_reverse = f"{existing_model} vs {NEW_MODEL}"
        new_results[pair_key_reverse] = {}
        
        for idx in tqdm(valid_indices, desc=f"Judging pairs with {existing_model}", leave=False):
            reference = df.iloc[idx]['English']
            new_translation = df.iloc[idx][NEW_MODEL]
            existing_translation = df.iloc[idx][existing_model]
            
            # Skip if any translation is missing
            if pd.isna(new_translation) or pd.isna(existing_translation) or new_translation == "" or existing_translation == "":
                print(f"Warning: Skipping row {idx} for {pair_key} due to missing data")
                new_results[pair_key][idx] = "skipped"
                new_results[pair_key_reverse][idx] = "skipped"
                continue
            
            # Forward comparison
            judgment = get_llm_judgment(reference, new_translation, existing_translation)
            
            if judgment == "first":
                new_results[pair_key][idx] = NEW_MODEL
            elif judgment == "second":
                new_results[pair_key][idx] = existing_model
            else:
                new_results[pair_key][idx] = "error"
            
            # Reverse comparison
            judgment = get_llm_judgment(reference, existing_translation, new_translation)
            
            if judgment == "first":
                new_results[pair_key_reverse][idx] = existing_model
            elif judgment == "second":
                new_results[pair_key_reverse][idx] = NEW_MODEL
            else:
                new_results[pair_key_reverse][idx] = "error"
    
    # Add new columns to existing result_df
    for pair_key in new_results:
        result_df[pair_key] = result_df['row_id'].map(lambda x: new_results[pair_key].get(x, "N/A"))
    
    # Save the updated results to CSV
    print("Saving updated results to roundrobin.csv...")
    result_df.to_csv('roundrobin.csv', index=False)
    
    # Calculate win counts for the new model
    win_count = 0
    for pair_key in new_results:
        for idx, winner in new_results[pair_key].items():
            if winner == NEW_MODEL:
                win_count += 1
    
    print(f"\nNew model '{NEW_MODEL}' won {win_count} comparisons")
    print("\nDone! Updated results saved to roundrobin.csv")

if __name__ == "__main__":
    main()