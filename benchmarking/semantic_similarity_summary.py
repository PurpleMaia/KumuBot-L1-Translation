#!/usr/bin/env python3
import pandas as pd
import numpy as np
import csv
from dotenv import load_dotenv

load_dotenv()


def calculate_summary_results(
    input_file="benchmarking/dataset_with_similarities.csv",
    output_file="benchmarking/semantic_similarity_results.csv",
):
    """
    Calculate and save summary results of semantic similarities.

    Args:
        input_file (str): Path to CSV with similarity scores
        output_file (str): Path to save summary results
    """
    print(f"Reading data from {input_file}...")
    df = pd.read_csv(input_file)

    # Identify model columns that have similarity scores
    similarity_columns = [col for col in df.columns if col.endswith("_similarity")]
    model_names = [col.replace("_similarity", "") for col in similarity_columns]

    print(f"Found {len(model_names)} models with similarity scores")

    # Dictionary to store average similarities for each model
    avg_similarities = {}

    # Calculate average similarities for each model
    for model, sim_col in zip(model_names, similarity_columns):
        valid_similarities = df[sim_col].dropna().tolist()
        if valid_similarities:
            avg_similarities[model] = sum(valid_similarities) / len(valid_similarities)
        else:
            avg_similarities[model] = np.nan

    # Sort models by average similarity (descending)
    sorted_models = sorted(avg_similarities.items(), key=lambda x: x[1], reverse=True)

    # Write summary to CSV
    print(f"Saving summary to {output_file}...")
    with open(output_file, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Model", "Average Similarity"])
        for model, avg_similarity in sorted_models:
            writer.writerow([model, avg_similarity])

    # Print summary to console
    print("\nSemantic Similarity Results (sorted by average similarity):")
    print("=" * 75)
    print(f"{'Model':<50} | {'Average Similarity':<20}")
    print("-" * 75)
    for model, avg_similarity in sorted_models:
        print(f"{model:<50} | {avg_similarity:.6f}")

    print(f"\nDone! Summary results saved to {output_file}")

    return sorted_models


if __name__ == "__main__":
    calculate_summary_results()
