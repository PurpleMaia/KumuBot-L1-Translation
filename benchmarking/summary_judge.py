#!/usr/bin/env python3
import pandas as pd
import csv
from collections import defaultdict


def main():
    print("Reading roundrobin.csv...")
    try:
        # Read the roundrobin results CSV
        df = pd.read_csv("roundrobin.csv")

        # Skip the row_id column
        comparison_columns = [col for col in df.columns if col != "row_id"]

        if not comparison_columns:
            print("Error: No comparison columns found in roundrobin.csv")
            return

        print(f"Found {len(comparison_columns)} comparison columns")

        # Initialize win counts
        win_counts = defaultdict(int)

        # Count wins for each model
        for _, row in df.iterrows():
            for column in comparison_columns:
                winner = str(row[column]).strip().lower()
                # Only count if it's a valid model name (not "error" or "skipped")
                if winner not in ["error", "skipped"]:
                    win_counts[winner] += 1

        # Sort models by win count (descending)
        sorted_models = sorted(win_counts.items(), key=lambda x: x[1], reverse=True)

        # Write summary to CSV
        print("Saving summary to judge_results_summary.csv...")
        with open("judge_results_summary.csv", "w", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["Model", "Win Count"])
            for model, wins in sorted_models:
                writer.writerow([model, wins])

        # Print summary to console
        print("\nJudgment Results (sorted by win count):")
        print("=" * 50)
        print(f"{'Model':<30} | {'Win Count':<20}")
        print("-" * 50)
        for model, wins in sorted_models:
            print(f"{model:<30} | {wins}")

        print("\nDone! Results saved to judge_results_summary.csv")

    except FileNotFoundError:
        print("Error: roundrobin.csv file not found.")
    except Exception as e:
        print(f"An error occurred: {str(e)}")


if __name__ == "__main__":
    main()
