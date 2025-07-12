#!/usr/bin/env python3
"""
Compare different embedding models for semantic similarity evaluation.

This script runs the complex semantic similarity evaluation with different
embedding models to compare their performance and help make an informed
decision about which model to use.
"""

import os
import sys
import argparse
import pandas as pd
import numpy as np
from pathlib import Path
import subprocess
import json
from typing import Dict, List, Tuple
from dotenv import load_dotenv

load_dotenv()


class EmbeddingModelComparator:
    """Compare different embedding models for semantic similarity."""

    def __init__(self):
        self.models_to_test = [
            {
                "name": "nomic-embed-text",
                "dimensions": 768,
                "context_tokens": 2048,
                "description": "Current model - Nomic Embed Text v1.5",
            },
            {
                "name": "snowflake-arctic-embed2-8k",
                "dimensions": 1024,
                "context_tokens": 8192,
                "description": "Snowflake Arctic Embed 2 - Larger context",
            },
        ]

        self.results_dir = Path("benchmarking/embedding_comparison")
        self.results_dir.mkdir(exist_ok=True)

    def run_evaluation(
        self,
        model_name: str,
        output_dir: str,
        embedding_model: str,
        dimensions: int,
        task_name: str = None,
    ) -> Dict:
        """Run semantic similarity evaluation with specific embedding model."""
        print(f"\n{'=' * 60}")
        print(f"Running evaluation with {embedding_model} ({dimensions} dims)")
        print(f"Model: {model_name}, Output: {output_dir}")
        print(f"{'=' * 60}")

        # Set environment variables for the embedding model
        env = os.environ.copy()
        env["EMBEDDING_MODEL"] = embedding_model
        env["EMBEDDING_DIMENSIONS"] = str(dimensions)

        # Run the evaluation
        cmd = [
            sys.executable,
            "benchmarking/complex_semantic_similarity.py",
            "--model",
            output_dir,
        ]

        if task_name:
            cmd.extend(["--task-name", task_name])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=env,
                timeout=300,  # 5 minute timeout
            )

            if result.returncode != 0:
                print(f"Error running evaluation: {result.stderr}")
                return None

            # Parse the results from the generated files
            if task_name:
                summary_file = f"benchmarking/complex_analysis/{output_dir}_{task_name}_similarity_summary.csv"
            else:
                summary_file = (
                    f"benchmarking/complex_analysis/{output_dir}_similarity_summary.csv"
                )

            if os.path.exists(summary_file):
                df = pd.read_csv(summary_file)
                return {
                    "embedding_model": embedding_model,
                    "dimensions": dimensions,
                    "results": df.to_dict("records"),
                }
            else:
                print(f"Results file not found: {summary_file}")
                return None

        except subprocess.TimeoutExpired:
            print(f"Evaluation timed out for {embedding_model}")
            return None
        except Exception as e:
            print(f"Error: {e}")
            return None

    def compare_models(self, test_models: List[Tuple[str, str]]) -> pd.DataFrame:
        """Compare embedding models across multiple test models.

        Args:
            test_models: List of (model_name, task_name) tuples
        """
        all_results = []

        for test_model, task_name in test_models:
            print(
                f"\n\nTesting with model: {test_model}"
                + (f" (task: {task_name})" if task_name else "")
            )

            for embed_config in self.models_to_test:
                # Backup existing results if they exist
                self._backup_results(test_model, task_name)

                # Run evaluation
                results = self.run_evaluation(
                    model_name=test_model,
                    output_dir=test_model,
                    embedding_model=embed_config["name"],
                    dimensions=embed_config["dimensions"],
                    task_name=task_name,
                )

                if results:
                    # Store results with metadata
                    for component_result in results["results"]:
                        all_results.append(
                            {
                                "test_model": test_model,
                                "embedding_model": embed_config["name"],
                                "embedding_dims": embed_config["dimensions"],
                                "context_tokens": embed_config["context_tokens"],
                                "component": component_result["component"],
                                "similarity": component_result["average_similarity"],
                                "valid_count": component_result["valid_count"],
                            }
                        )

                    # Save intermediate results
                    self._save_results(
                        test_model, embed_config["name"], results, task_name
                    )

                # Restore original results
                self._restore_results(test_model, task_name)

        # Create comparison dataframe
        comparison_df = pd.DataFrame(all_results)
        return comparison_df

    def _backup_results(self, model_name: str, task_name: str = None):
        """Backup existing results before running new evaluation."""
        if task_name:
            files_to_backup = [
                f"benchmarking/complex_analysis/{model_name}_{task_name}_similarity_results.json",
                f"benchmarking/complex_analysis/{model_name}_{task_name}_similarity_summary.csv",
            ]
        else:
            files_to_backup = [
                f"benchmarking/complex_analysis/{model_name}_similarity_results.json",
                f"benchmarking/complex_analysis/{model_name}_similarity_summary.csv",
            ]

        backup_dir = self.results_dir / "backups"
        backup_dir.mkdir(exist_ok=True)

        for file in files_to_backup:
            if os.path.exists(file):
                backup_path = backup_dir / f"{Path(file).name}.backup"
                subprocess.run(["cp", file, str(backup_path)], check=False)

    def _restore_results(self, model_name: str, task_name: str = None):
        """Restore original results after evaluation."""
        backup_dir = self.results_dir / "backups"

        if task_name:
            files_to_restore = [
                f"benchmarking/complex_analysis/{model_name}_{task_name}_similarity_results.json",
                f"benchmarking/complex_analysis/{model_name}_{task_name}_similarity_summary.csv",
            ]
        else:
            files_to_restore = [
                f"benchmarking/complex_analysis/{model_name}_similarity_results.json",
                f"benchmarking/complex_analysis/{model_name}_similarity_summary.csv",
            ]

        for file in files_to_restore:
            backup_path = backup_dir / f"{Path(file).name}.backup"
            if backup_path.exists():
                subprocess.run(["cp", str(backup_path), file], check=False)

    def _save_results(
        self, test_model: str, embed_model: str, results: Dict, task_name: str = None
    ):
        """Save results for specific model combination."""
        if task_name:
            filename = (
                self.results_dir
                / f"{test_model}_{task_name}_{embed_model.replace('-', '_')}_results.json"
            )
        else:
            filename = (
                self.results_dir
                / f"{test_model}_{embed_model.replace('-', '_')}_results.json"
            )
        with open(filename, "w") as f:
            json.dump(results, f, indent=2)

    def generate_report(self, comparison_df: pd.DataFrame):
        """Generate comparison report."""
        print("\n" + "=" * 80)
        print("EMBEDDING MODEL COMPARISON REPORT")
        print("=" * 80)

        # Pivot table for easier comparison
        for test_model in comparison_df["test_model"].unique():
            print(f"\n### Results for: {test_model}")
            model_df = comparison_df[comparison_df["test_model"] == test_model]

            pivot = model_df.pivot_table(
                index="component",
                columns="embedding_model",
                values="similarity",
                aggfunc="first",
            )

            # Calculate differences
            if len(pivot.columns) == 2:
                col1, col2 = pivot.columns
                pivot["difference"] = pivot[col2] - pivot[col1]
                pivot["pct_change"] = pivot["difference"] / pivot[col1] * 100

                print(f"\n{pivot.round(4).to_string()}")

                # Summary statistics
                avg_improvement = pivot["pct_change"].mean()
                print(f"\nAverage improvement: {avg_improvement:.2f}%")

        # Overall comparison
        print("\n" + "=" * 80)
        print("OVERALL COMPARISON")
        print("=" * 80)

        summary = comparison_df.groupby(["embedding_model", "component"])[
            "similarity"
        ].mean()
        print(summary.round(4).to_string())

        # Save full report
        report_path = self.results_dir / "comparison_report.csv"
        comparison_df.to_csv(report_path, index=False)
        print(f"\nFull report saved to: {report_path}")

        return comparison_df


def main():
    parser = argparse.ArgumentParser(
        description="Compare embedding models for semantic similarity"
    )
    parser.add_argument(
        "--models", nargs="+", help="Models to test (defaults to a representative set)"
    )
    parser.add_argument(
        "--quick", action="store_true", help="Quick test with just one model"
    )

    args = parser.parse_args()

    # Discover available models with their task names
    from pathlib import Path
    import re

    data_dir = Path("data/complex_analysis")
    available_models = []

    for file in data_dir.glob("*_extracted.csv"):
        filename = file.stem

        # Parse task-specific models
        if "_hybrid_complex_analysis_" in filename:
            match = re.match(r"(.+?)_(hybrid_complex_analysis_.+)_extracted", filename)
            if match:
                model_name = match.group(1)
                task_name = match.group(2)
                available_models.append((model_name, task_name))
        elif filename.endswith("_hybrid_extracted"):
            model_name = filename.replace("_hybrid_extracted", "")
            available_models.append((model_name, None))
        elif filename.endswith("_extracted"):
            model_name = filename.replace("_extracted", "")
            available_models.append((model_name, None))

    # Filter based on user selection
    if args.models:
        # Filter to only requested models
        filtered_models = []
        for model_name, task_name in available_models:
            if model_name in args.models:
                filtered_models.append((model_name, task_name))
        available_models = filtered_models
    elif args.quick:
        # Just use one model for quick test
        if available_models:
            available_models = [available_models[0]]

    if not available_models:
        print("No valid models found for testing")
        return

    print(f"Found {len(available_models)} model configurations to test:")
    for model, task in available_models:
        print(f"  - {model}" + (f" (task: {task})" if task else ""))

    # Run comparison
    comparator = EmbeddingModelComparator()
    comparison_df = comparator.compare_models(available_models)

    # Generate report
    if not comparison_df.empty:
        comparator.generate_report(comparison_df)
    else:
        print("No results to compare")


if __name__ == "__main__":
    main()
