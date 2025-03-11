#!/usr/bin/env python3
import os
import pandas as pd
import re
import time
import itertools
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

# Define the model folders - USERS CAN MODIFY THIS LIST TO INCLUDE ONLY SPECIFIC MODELS
model_folders = [
    "gemini-2.0-flash-thinking",
    "gpt4o",
    "o1",
    "llama-3.3",
    "gpt-4o-mini",
    "gpt-4.5-preview",
    "deepseek-r1-distill-llama-70b"
]

# Define which rows to use for judging - USERS CAN MODIFY THIS LIST
# For example, to only use the first two examples, set to [0, 1]
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
    
    # Check which model columns exist in the dataset
    available_models = [model for model in model_folders if model in df.columns]
    if not available_models:
        print("Error: No model translation columns found in dataset.csv")
        return
    
    print(f"Found {len(available_models)} model columns in dataset")
    
    # Validate row indices
    valid_indices = [idx for idx in ROW_INDICES if idx < len(df)]
    if not valid_indices:
        print("Error: No valid row indices specified")
        return
    
    print(f"Using {len(valid_indices)} rows for judging: {valid_indices}")
    
    # Get all pairs of models
    model_pairs = list(itertools.combinations(available_models, 2))
    print(f"Total model pairs to compare: {len(model_pairs) * 2}")  # *2 for both directions
    
    # Initialize results dictionary
    results = {}
    for idx in valid_indices:
        results[idx] = {}
    
    # For every pair of models, compare translations in both directions
    for model1, model2 in tqdm(model_pairs, desc="Processing model pairs"):
        # Forward comparison (model1 as first, model2 as second)
        pair_key = f"{model1} vs {model2}"
        
        for idx in tqdm(valid_indices, desc=f"Judging {pair_key}", leave=False):
            reference = df.iloc[idx]['English']
            translation1 = df.iloc[idx][model1]
            translation2 = df.iloc[idx][model2]
            
            # Skip if any translation is missing
            if pd.isna(translation1) or pd.isna(translation2) or translation1 == "" or translation2 == "":
                print(f"Warning: Skipping row {idx} for {pair_key} due to missing data")
                results[idx][pair_key] = "skipped"
                continue
            
            judgment = get_llm_judgment(reference, translation1, translation2)
            
            if judgment == "first":
                results[idx][pair_key] = model1
            elif judgment == "second":
                results[idx][pair_key] = model2
            else:
                results[idx][pair_key] = "error"
        
        # Reverse comparison (model2 as first, model1 as second)
        pair_key_reverse = f"{model2} vs {model1}"
        
        for idx in tqdm(valid_indices, desc=f"Judging {pair_key_reverse}", leave=False):
            reference = df.iloc[idx]['English']
            translation1 = df.iloc[idx][model2]
            translation2 = df.iloc[idx][model1]
            
            # Skip if any translation is missing
            if pd.isna(translation1) or pd.isna(translation2) or translation1 == "" or translation2 == "":
                print(f"Warning: Skipping row {idx} for {pair_key_reverse} due to missing data")
                results[idx][pair_key_reverse] = "skipped"
                continue
            
            judgment = get_llm_judgment(reference, translation1, translation2)
            
            if judgment == "first":
                results[idx][pair_key_reverse] = model2
            elif judgment == "second":
                results[idx][pair_key_reverse] = model1
            else:
                results[idx][pair_key_reverse] = "error"
    
    # Create a dataframe from the results
    result_df = pd.DataFrame.from_dict(results, orient='index')
    
    # Add a row_id column
    result_df.index.name = 'row_id'
    result_df = result_df.reset_index()
    
    # Save the results to CSV
    print("Saving results to roundrobin.csv...")
    result_df.to_csv('roundrobin.csv', index=False)
    
    # Calculate win counts
    win_counts = {model: 0 for model in available_models}
    
    for idx in valid_indices:
        for column in result_df.columns:
            if column != 'row_id':
                winner = results[idx].get(column)
                if winner in win_counts:
                    win_counts[winner] += 1
    
    # Sort models by win count (descending)
    sorted_models = sorted(win_counts.items(), key=lambda x: x[1], reverse=True)
    
    # Write summary to CSV
    print("Saving summary to judge_results_summary.csv...")
    with open('judge_results_summary.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Model', 'Win Count'])
        for model, wins in sorted_models:
            writer.writerow([model, wins])
    
    # Print summary to console
    print("\nJudgment Results (sorted by win count):")
    print("=" * 50)
    print(f"{'Model':<30} | {'Win Count':<20}")
    print("-" * 50)
    for model, wins in sorted_models:
        print(f"{model:<30} | {wins}")
    
    print("\nDone! Results saved to roundrobin.csv and judge_results_summary.csv")

if __name__ == "__main__":
    main()