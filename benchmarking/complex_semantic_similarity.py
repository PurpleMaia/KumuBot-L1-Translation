#!/usr/bin/env python3
"""
Multi-Component Semantic Similarity Evaluator for Complex Analysis Tasks

This module evaluates the semantic similarity of complex analysis outputs
by comparing each component (translation, commentary, summary) separately
against reference data.
"""

import os
import pandas as pd
import numpy as np
from openai import OpenAI
from dotenv import load_dotenv
import time
import json
import argparse
from tqdm import tqdm
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Load environment variables
load_dotenv()

# Get API configuration
api_key = os.getenv("OPENAI_API_KEY_KOA")
if not api_key:
    raise ValueError("Please set the OPENAI_API_KEY_KOA environment variable")

api_base_url = os.getenv("OPENAI_API_EMBEDDING_BASE_URL")
if not api_base_url:
    raise ValueError(
        "Please set the OPENAI_API_EMBEDDING_BASE_URL environment variable"
    )

# Initialize OpenAI client
client = OpenAI(api_key=api_key, base_url=api_base_url)
embedding_model = "nomic-embed-text"


class MultiComponentEvaluator:
    """Evaluates multi-component analysis outputs."""

    def __init__(self):
        self.embedding_cache = {}

    def get_embedding(self, text: str) -> Optional[List[float]]:
        """Get embedding for text with caching and rate limiting."""
        if not text or pd.isna(text):
            return None

        # Use cache to avoid redundant API calls
        if text in self.embedding_cache:
            return self.embedding_cache[text]

        max_retries = 5
        retry_delay = 1

        for attempt in range(max_retries):
            try:
                response = client.embeddings.create(
                    model=embedding_model,
                    input=text,
                    dimensions=768,
                )
                embedding = response.data[0].embedding
                self.embedding_cache[text] = embedding
                return embedding
            except Exception as e:
                if "rate limit" in str(e).lower() and attempt < max_retries - 1:
                    sleep_time = retry_delay * (2**attempt)
                    print(f"Rate limit exceeded. Retrying in {sleep_time} seconds...")
                    time.sleep(sleep_time)
                else:
                    print(f"Error getting embedding: {str(e)}")
                    return None
        return None

    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if vec1 is None or vec2 is None:
            return np.nan

        dot_product = np.dot(vec1, vec2)
        norm_a = np.linalg.norm(vec1)
        norm_b = np.linalg.norm(vec2)

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return float(dot_product / (norm_a * norm_b))

    def load_complex_analysis_data(self, output_dir: str) -> pd.DataFrame:
        """Load extracted complex analysis data from CSV."""
        # Try hybrid extracted first, then regular extracted
        hybrid_csv_path = f"data/complex_analysis/{output_dir}_hybrid_extracted.csv"
        regular_csv_path = f"data/complex_analysis/{output_dir}_extracted.csv"

        if os.path.exists(hybrid_csv_path):
            return pd.read_csv(hybrid_csv_path)
        elif os.path.exists(regular_csv_path):
            return pd.read_csv(regular_csv_path)
        else:
            raise FileNotFoundError(
                f"Complex analysis data not found: {hybrid_csv_path} or {regular_csv_path}"
            )

    def load_reference_data(self) -> pd.DataFrame:
        """Load reference data for complex analysis."""
        ref_path = "data/complex_analysis/namakaokapaoo_dataset.csv"

        if not os.path.exists(ref_path):
            raise FileNotFoundError(f"Reference data not found: {ref_path}")

        return pd.read_csv(ref_path)

    def evaluate_component_similarity(
        self, model_texts: List[str], reference_texts: List[str], component_name: str
    ) -> Tuple[List[float], float]:
        """Evaluate semantic similarity for a specific component."""
        print(f"Evaluating {component_name} similarity...")

        similarities = []

        # Get embeddings for reference texts
        print(f"Computing embeddings for reference {component_name}...")
        ref_embeddings = []
        for ref_text in tqdm(reference_texts):
            embedding = self.get_embedding(str(ref_text) if pd.notna(ref_text) else "")
            ref_embeddings.append(embedding)

        # Get embeddings for model texts and compute similarities
        print(f"Computing embeddings for model {component_name}...")
        for i, (model_text, ref_embedding) in enumerate(
            tqdm(zip(model_texts, ref_embeddings))
        ):
            if ref_embedding is None or pd.isna(model_text) or model_text == "":
                similarities.append(np.nan)
                continue

            model_embedding = self.get_embedding(str(model_text))
            similarity = self.cosine_similarity(model_embedding, ref_embedding)
            similarities.append(similarity)

        # Calculate average similarity (excluding NaN values)
        valid_similarities = [s for s in similarities if not np.isnan(s)]
        avg_similarity = np.mean(valid_similarities) if valid_similarities else 0.0

        return similarities, avg_similarity

    def prepare_component_data(
        self, model_df: pd.DataFrame, ref_df: pd.DataFrame, output_dir: str
    ) -> Dict[str, Tuple[List[str], List[str]]]:
        """Prepare component data for evaluation."""
        components = {}

        # Translation component
        model_translations = model_df[f"{output_dir}_translation"].fillna("").tolist()
        ref_translations = ref_df["english_translation"].fillna("").tolist()
        components["translation"] = (model_translations, ref_translations)

        # Commentary component (only for rows that have it)
        if f"{output_dir}_commentary" in model_df.columns:
            model_commentary = model_df[f"{output_dir}_commentary"].fillna("").tolist()
            ref_commentary = ref_df["commentary"].fillna("").tolist()
            components["commentary"] = (model_commentary, ref_commentary)

        # Summary component (only for rows that have it)
        if f"{output_dir}_summary" in model_df.columns:
            model_summaries = model_df[f"{output_dir}_summary"].fillna("").tolist()
            ref_summaries = ref_df["overall_summary"].fillna("").tolist()
            components["summary"] = (model_summaries, ref_summaries)

        return components

    def evaluate_model(self, output_dir: str) -> Dict[str, any]:
        """Evaluate a single model's complex analysis output."""
        print(f"\n=== Evaluating model: {output_dir} ===")

        # Load data
        model_df = self.load_complex_analysis_data(output_dir)
        ref_df = self.load_reference_data()

        # Prepare component data
        components = self.prepare_component_data(model_df, ref_df, output_dir)

        # Evaluate each component
        results = {
            "model": output_dir,
            "total_passages": len(model_df),
            "components": {},
        }

        for component_name, (model_texts, ref_texts) in components.items():
            similarities, avg_similarity = self.evaluate_component_similarity(
                model_texts, ref_texts, component_name
            )

            results["components"][component_name] = {
                "similarities": similarities,
                "average_similarity": avg_similarity,
                "valid_count": sum(1 for s in similarities if not np.isnan(s)),
                "missing_count": sum(1 for s in similarities if np.isnan(s)),
            }

            print(
                f"{component_name.title()} - Average similarity: {avg_similarity:.4f}"
            )

        return results

    def save_results(self, results: Dict[str, any], output_dir: str):
        """Save evaluation results to files."""
        # Create output directory
        os.makedirs("benchmarking/complex_analysis", exist_ok=True)

        # Save detailed results as JSON
        json_path = (
            f"benchmarking/complex_analysis/{output_dir}_similarity_results.json"
        )
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)

        # Create summary DataFrame
        summary_data = []
        for component, data in results["components"].items():
            summary_data.append(
                {
                    "model": output_dir,
                    "component": component,
                    "average_similarity": data["average_similarity"],
                    "valid_count": data["valid_count"],
                    "missing_count": data["missing_count"],
                }
            )

        summary_df = pd.DataFrame(summary_data)
        csv_path = f"benchmarking/complex_analysis/{output_dir}_similarity_summary.csv"
        summary_df.to_csv(csv_path, index=False)

        print(f"\nResults saved to:")
        print(f"  - {json_path}")
        print(f"  - {csv_path}")


def discover_complex_analysis_outputs() -> List[str]:
    """Discover available complex analysis outputs."""
    data_dir = Path("data/complex_analysis")
    if not data_dir.exists():
        return []

    outputs = set()  # Use set to avoid duplicates
    # Look for both regular and hybrid extracted files
    for file in data_dir.glob("*_extracted.csv"):
        output_name = file.stem.replace("_extracted", "")
        outputs.add(output_name)

    for file in data_dir.glob("*_hybrid_extracted.csv"):
        output_name = file.stem.replace("_hybrid_extracted", "")
        outputs.add(output_name)

    return sorted(list(outputs))


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate semantic similarity for complex analysis outputs"
    )
    parser.add_argument(
        "--model",
        type=str,
        help="Specific model to evaluate (defaults to all discovered models)",
    )
    parser.add_argument(
        "--list", action="store_true", help="List available models and exit"
    )

    args = parser.parse_args()

    # List available models
    available_models = discover_complex_analysis_outputs()

    if args.list:
        print("Available complex analysis outputs:")
        for model in available_models:
            print(f"  - {model}")
        return

    if not available_models:
        print("No complex analysis outputs found.")
        print("Run complex analysis first, then extract results.")
        return

    # Initialize evaluator
    evaluator = MultiComponentEvaluator()

    # Evaluate specific model or all models
    if args.model:
        if args.model not in available_models:
            print(f"Model '{args.model}' not found in available outputs.")
            print(f"Available models: {available_models}")
            return
        models_to_evaluate = [args.model]
    else:
        models_to_evaluate = available_models

    print(f"Evaluating {len(models_to_evaluate)} model(s)...")

    # Evaluate each model
    for model in models_to_evaluate:
        try:
            results = evaluator.evaluate_model(model)
            evaluator.save_results(results, model)
        except Exception as e:
            print(f"Error evaluating model {model}: {e}")
            continue

    print("\n=== Multi-Component Evaluation Complete ===")


if __name__ == "__main__":
    main()
