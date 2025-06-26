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

# Define the new model name
new_model = "gpt-4o-mini-finetuned"


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
                dimensions=3072,  # text-embedding-large-v3 supports 3072 dimensions
            )
            return response.data[0].embedding
        except Exception as e:
            if "rate limit" in str(e).lower() and attempt < max_retries - 1:
                sleep_time = retry_delay * (2**attempt)  # Exponential backoff
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
    # Read the dataset with translations and similarities
    print("Reading dataset_with_similarities.csv...")
    try:
        df = pd.read_csv("dataset_with_similarities.csv")
    except FileNotFoundError:
        print(
            "Error: dataset_with_similarities.csv not found. Make sure you're in the correct directory."
        )
        return

    # Read the original dataset to get the new model column
    print("Reading dataset.csv to get the new model data...")
    try:
        original_df = pd.read_csv("../data/dataset.csv")
    except FileNotFoundError:
        print("Error: dataset.csv not found in ../data/ directory.")
        return

    # Check if new model column exists in original dataset
    if new_model not in original_df.columns:
        print(f"Error: '{new_model}' column not found in dataset.csv")
        return

    # Check if English column exists for reference
    if "English" not in df.columns:
        print("Error: 'English' column not found in dataset_with_similarities.csv")
        return

    # Add the new model column to the dataframe if it doesn't already exist
    if new_model not in df.columns:
        print(f"Adding '{new_model}' column from original dataset...")
        df[new_model] = original_df[new_model]
    else:
        print(
            f"Note: '{new_model}' column already exists in dataset_with_similarities.csv"
        )

    # Check if similarity column already exists
    similarity_column = f"{new_model}_similarity"
    if similarity_column in df.columns:
        print(
            f"Warning: '{similarity_column}' column already exists. It will be overwritten."
        )

    # Get embeddings for reference translations
    print("Computing embeddings for reference translations...")
    reference_embeddings = []
    for i, ref_translation in enumerate(tqdm(df["English"])):
        if pd.isna(ref_translation) or ref_translation == "":
            print(f"Warning: Empty reference translation at row {i}")
            reference_embeddings.append(None)
        else:
            embedding = get_embedding(ref_translation)
            reference_embeddings.append(embedding)

    # Compute similarity with reference translations for the new model
    print(f"Processing {new_model} translations...")
    similarities = []
    valid_similarities = []

    for i, (model_translation, ref_embedding) in enumerate(
        tqdm(zip(df[new_model], reference_embeddings))
    ):
        if (
            pd.isna(model_translation)
            or model_translation == ""
            or ref_embedding is None
        ):
            print(f"Warning: Skipping row {i} for {new_model} due to missing data")
            similarities.append(np.nan)
        else:
            model_embedding = get_embedding(model_translation)
            similarity = cosine_similarity(model_embedding, ref_embedding)
            similarities.append(similarity)
            valid_similarities.append(similarity)

    # Add similarity column to the dataframe
    df[similarity_column] = similarities

    # Save the updated dataframe with similarity scores
    print("Saving results to dataset_with_similarities.csv...")
    df.to_csv("dataset_with_similarities.csv", index=False)

    # Calculate average similarity for the new model
    avg_similarity = np.nan
    if valid_similarities:
        avg_similarity = sum(valid_similarities) / len(valid_similarities)

    # Print summary to console
    print("\nSemantic Similarity Results for new model:")
    print("=" * 50)
    print(f"{new_model:<30} | {avg_similarity:.6f}")

    print("\nDone! Results saved to dataset_with_similarities.csv")
    print(f"Added column: {new_model}_similarity")


if __name__ == "__main__":
    main()
