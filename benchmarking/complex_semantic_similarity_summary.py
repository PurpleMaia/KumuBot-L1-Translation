#!/usr/bin/env python3
"""
Complex Analysis Semantic Similarity Summary Generator

This script aggregates results from multiple complex analysis models and provides
a comprehensive comparison of their performance across translation, commentary,
and summary components.
"""

import pandas as pd
import numpy as np
import csv
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


def discover_complex_analysis_results():
    """Discover all available complex analysis results."""
    results_dir = Path("benchmarking/complex_analysis")
    if not results_dir.exists():
        return []

    models = []
    for file in results_dir.glob("*_similarity_summary.csv"):
        stem = file.stem.replace("_similarity_summary", "")
        
        # Parse model name and task name
        # Patterns:
        # 1. model_similarity_summary.csv -> (model, None)
        # 2. model_taskname_similarity_summary.csv -> (model, taskname)
        
        # Check for known task patterns - order matters for proper matching
        if "_hybrid_complex_analysis_" in stem:
            # Task-specific format with multiple parts: model_hybrid_complex_analysis_variant
            # Find the start of the task pattern
            task_start = stem.find("_hybrid_complex_analysis_")
            model_name = stem[:task_start]
            task_name = stem[task_start + 1:]  # Skip the leading underscore
            models.append((model_name, task_name))
        elif "_hybrid_complex_analysis" in stem:
            model_name = stem.replace("_hybrid_complex_analysis", "")
            models.append((model_name, "hybrid_complex_analysis"))
        else:
            # No task suffix
            models.append((stem, None))

    # Sort by model name and task name
    return sorted(models, key=lambda x: (x[0], x[1] or ""))


def load_model_results(model_name, task_name=None):
    """Load results for a specific model and task."""
    # Build filename based on task
    if task_name:
        summary_file = f"benchmarking/complex_analysis/{model_name}_{task_name}_similarity_summary.csv"
    else:
        summary_file = f"benchmarking/complex_analysis/{model_name}_similarity_summary.csv"

    if not Path(summary_file).exists():
        return None

    df = pd.read_csv(summary_file)

    # Convert to dictionary for easier handling
    results = {}
    for _, row in df.iterrows():
        component = row["component"]
        results[component] = {
            "average_similarity": row["average_similarity"],
            "valid_count": row["valid_count"],
            "missing_count": row["missing_count"],
        }

    return results


def calculate_composite_score(results):
    """Calculate a composite score based on weighted components."""
    # Default weights: Translation 40%, Commentary 40%, Summary 20%
    weights = {"translation": 0.4, "commentary": 0.4, "summary": 0.2}

    composite_score = 0.0
    total_weight = 0.0

    for component, weight in weights.items():
        if component in results and not np.isnan(
            results[component]["average_similarity"]
        ):
            composite_score += results[component]["average_similarity"] * weight
            total_weight += weight

    if total_weight > 0:
        return composite_score / total_weight
    else:
        return np.nan


def generate_summary_report(output_file="benchmarking/complex_analysis_results.csv"):
    """Generate a comprehensive summary report."""
    models = discover_complex_analysis_results()

    if not models:
        print("No complex analysis results found.")
        return

    print(f"Found {len(models)} models with complex analysis results")

    # Collect all results
    all_results = []

    for model_name, task_name in models:
        results = load_model_results(model_name, task_name)
        if results:
            composite_score = calculate_composite_score(results)
            
            # Create display name that includes task if present
            display_name = model_name
            if task_name:
                display_name = f"{model_name} ({task_name})"

            model_data = {
                "model": display_name,
                "composite_score": composite_score,
                "translation_similarity": results.get("translation", {}).get(
                    "average_similarity", np.nan
                ),
                "translation_valid": results.get("translation", {}).get(
                    "valid_count", 0
                ),
                "commentary_similarity": results.get("commentary", {}).get(
                    "average_similarity", np.nan
                ),
                "commentary_valid": results.get("commentary", {}).get("valid_count", 0),
                "summary_similarity": results.get("summary", {}).get(
                    "average_similarity", np.nan
                ),
                "summary_valid": results.get("summary", {}).get("valid_count", 0),
            }
            all_results.append(model_data)

    # Sort by composite score (descending)
    all_results.sort(
        key=lambda x: x["composite_score"]
        if not np.isnan(x["composite_score"])
        else -1,
        reverse=True,
    )

    # Write detailed CSV
    print(f"Saving detailed results to {output_file}...")
    df = pd.DataFrame(all_results)
    df.to_csv(output_file, index=False)

    # Print summary to console
    print("\nComplex Analysis Results (sorted by composite score):")
    print("=" * 150)
    print(
        f"{'Model':<70} | {'Composite':<10} | {'Translation':<12} | {'Commentary':<12} | {'Summary':<10} | {'Valid Passages':<15}"
    )
    print("-" * 150)

    for result in all_results:
        model = result["model"]
        composite = result["composite_score"]
        translation = result["translation_similarity"]
        commentary = result["commentary_similarity"]
        summary = result["summary_similarity"]
        valid_passages = f"{result['translation_valid']}/{result['commentary_valid']}/{result['summary_valid']}"

        composite_str = f"{composite:.4f}" if not np.isnan(composite) else "N/A"
        translation_str = f"{translation:.4f}" if not np.isnan(translation) else "N/A"
        commentary_str = f"{commentary:.4f}" if not np.isnan(commentary) else "N/A"
        summary_str = f"{summary:.4f}" if not np.isnan(summary) else "N/A"

        print(
            f"{model:<70} | {composite_str:<10} | {translation_str:<12} | {commentary_str:<12} | {summary_str:<10} | {valid_passages:<15}"
        )

    print(f"\nLegend:")
    print(
        f"  Composite: Weighted average (Translation: 40%, Commentary: 40%, Summary: 20%)"
    )
    print(f"  Valid Passages: Translation/Commentary/Summary valid counts")
    print(f"  Results saved to: {output_file}")

    return all_results


def show_detailed_comparison(models=None):
    """Show a detailed comparison of specific models."""
    if not models:
        models = discover_complex_analysis_results()

    if not models:
        print("No models found for comparison.")
        return

    print(f"\nDetailed Component Comparison:")
    print("=" * 80)

    for model in models:
        results = load_model_results(model)
        if results:
            print(f"\n📊 {model}:")
            for component, data in results.items():
                similarity = data["average_similarity"]
                valid_count = data["valid_count"]
                missing_count = data["missing_count"]

                if not np.isnan(similarity):
                    print(
                        f"  {component.capitalize():<12}: {similarity:.4f} ({valid_count}/{valid_count + missing_count} valid)"
                    )
                else:
                    print(
                        f"  {component.capitalize():<12}: N/A ({valid_count}/{valid_count + missing_count} valid)"
                    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate complex analysis similarity summary"
    )
    parser.add_argument(
        "--detailed", action="store_true", help="Show detailed component comparison"
    )
    parser.add_argument("--models", nargs="*", help="Specific models to compare")

    args = parser.parse_args()

    # Generate main summary
    results = generate_summary_report()

    # Show detailed comparison if requested
    if args.detailed:
        show_detailed_comparison(args.models)
