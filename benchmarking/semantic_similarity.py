#!/usr/bin/env python3
import os
import pandas as pd
import numpy as np
from openai import OpenAI
from dotenv import load_dotenv
import time
from tqdm import tqdm

# Load environment variables from .env file (if any)
load_dotenv()

# Get API key from environment variable
api_key = os.getenv("OPENAI_API_KEY_KOA")
if not api_key:
    raise ValueError("Please set the OPENAI_API_KEY environment variable")

# Initialize OpenAI client
client = OpenAI(api_key=api_key)

# Define the model name
embedding_model = "text-embedding-3-large"

# Define the model folders
model_folders = [
    "gemini-2.0-flash-thinking",
    "gpt4o",
    "o1",
    "llama-3.3",
    "gpt-4o-mini",
    "gpt-4.5-preview",
    "deepseek-r1-distill-llama-70b",
    "gpt-4o-mini-finetuned"
]

def get_embedding(text):
    """
    Get embedding for a text using OpenAI API
    Includes rate limit handling with exponential backoff
    """
    max_retries = 5
    retry_delay = 1
    
    for attempt in range(max_retries):
        try:
            response = client.embeddings.create(
                model=embedding_model,
                input=text,
                dimensions=3072  # text-embedding-large-v3 supports 3072 dimensions
            )
            return response.data[0].embedding
        except Exception as e:
            if "rate limit" in str(e).lower() and attempt < max_retries - 1:
                sleep_time = retry_delay * (2 ** attempt)  # Exponential backoff
                print(f"Rate limit exceeded. Retrying in {sleep_time} seconds...")
                time.sleep(sleep_time)
            else:
                print(f"Error getting embedding: {str(e)}")
                raise

def cosine_similarity(vec1, vec2):
    """
    Compute cosine similarity between two vectors
    """
    dot_product = np.dot(vec1, vec2)
    norm_a = np.linalg.norm(vec1)
    norm_b = np.linalg.norm(vec2)
    
    if norm_a == 0 or norm_b == 0:
        return 0  # Prevent division by zero
    
    return dot_product / (norm_a * norm_b)

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
    
    # Dictionary to store average similarities for each model
    model_similarities = {model: [] for model in available_models}
    
    # Get embeddings for reference translations
    print("Computing embeddings for reference translations...")
    reference_embeddings = []
    for i, ref_translation in enumerate(tqdm(df['English'])):
        if pd.isna(ref_translation) or ref_translation == "":
            print(f"Warning: Empty reference translation at row {i}")
            reference_embeddings.append(None)
        else:
            embedding = get_embedding(ref_translation)
            reference_embeddings.append(embedding)
    
    # For each model, compute similarity with reference translations
    for model in available_models:
        print(f"Processing {model} translations...")
        similarities = []
        
        for i, (model_translation, ref_embedding) in enumerate(tqdm(zip(df[model], reference_embeddings))):
            if pd.isna(model_translation) or model_translation == "" or ref_embedding is None:
                print(f"Warning: Skipping row {i} for {model} due to missing data")
                similarities.append(np.nan)
            else:
                model_embedding = get_embedding(model_translation)
                similarity = cosine_similarity(model_embedding, ref_embedding)
                similarities.append(similarity)
                
                # Save to the model_similarities dictionary
                model_similarities[model].append(similarity)
        
        # Add similarity column to the dataframe
        df[f"{model}_similarity"] = similarities
    
    # Save the updated dataframe with similarity scores
    output_file = 'dataset_with_similarities.csv'
    print(f"Saving results to {output_file}...")
    df.to_csv(output_file, index=False)
    
    print("\nDone! Processing completed successfully.")

if __name__ == "__main__":
    main()