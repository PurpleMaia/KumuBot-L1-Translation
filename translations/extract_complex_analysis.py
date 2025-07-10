#!/usr/bin/env python3
"""
Extract complex analysis outputs (translations, commentary, summaries)
from JSON files and compile them into a structured format.
"""

import json
import os
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any
import argparse


def load_json_outputs(output_dir: str) -> List[Dict[str, Any]]:
    """Load all JSON outputs from the specified directory."""
    json_files = []
    output_path = Path(f"translations/{output_dir}")

    if not output_path.exists():
        print(f"Output directory {output_path} does not exist")
        return []

    # Find all complex_analysis JSON files
    for json_file in sorted(output_path.glob("complex_analysis_*.json")):
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            json_files.append(data)

    return json_files


def extract_to_dataframe(
    json_outputs: List[Dict[str, Any]], output_dir: str
) -> pd.DataFrame:
    """Extract data from JSON outputs into a DataFrame."""
    rows = []

    for output in json_outputs:
        chapter = output.get("chapter", "")

        # Extract passages and their analyses
        passages = output.get("passages", [])
        translations = output.get(f"{output_dir}_translation", "").split("\n\n")
        commentaries = output.get(f"{output_dir}_commentary", "").split("\n\n")

        # Process each passage
        for i, passage in enumerate(passages):
            row = {
                "chapter": chapter,
                "paragraph": passage.get("paragraph", ""),
                "hawaiian_text": passage.get("hawaiian_text", ""),
                f"{output_dir}_translation": translations[i]
                if i < len(translations)
                else "",
                f"{output_dir}_commentary": commentaries[i]
                if i < len(commentaries)
                else "",
            }

            # Add reference data if available
            if "reference_translations" in output and i < len(
                output["reference_translations"]
            ):
                row["reference_translation"] = output["reference_translations"][i]

            if "reference_commentary" in output and i == 0:
                row["reference_commentary"] = output["reference_commentary"]

            rows.append(row)

        # Add summary to the last row of each chapter
        if rows and f"{output_dir}_summary" in output:
            rows[-1][f"{output_dir}_summary"] = output[f"{output_dir}_summary"]
            if "reference_summary" in output:
                rows[-1]["reference_summary"] = output["reference_summary"]

    return pd.DataFrame(rows)


def create_summary_report(df: pd.DataFrame, output_dir: str) -> str:
    """Create a summary report of the complex analysis."""
    report = []
    report.append(f"# Complex Analysis Summary Report")
    report.append(f"## Model: {output_dir}\n")

    # Statistics
    report.append("### Statistics")
    report.append(f"- Total chapters analyzed: {df['chapter'].nunique()}")
    report.append(f"- Total passages analyzed: {len(df)}")
    report.append(
        f"- Passages with translations: {df[f'{output_dir}_translation'].notna().sum()}"
    )
    report.append(
        f"- Passages with commentary: {df[f'{output_dir}_commentary'].notna().sum()}"
    )
    report.append(
        f"- Chapters with summaries: {df[f'{output_dir}_summary'].notna().sum()}\n"
    )

    # Sample outputs
    report.append("### Sample Outputs")

    # Get first passage with all components
    sample_row = df[df[f"{output_dir}_translation"].notna()].iloc[0]

    report.append(
        f"\n#### Chapter {sample_row['chapter']}, Paragraph {sample_row['paragraph']}"
    )
    report.append(f"\n**Hawaiian Text:**")
    report.append(f"{sample_row['hawaiian_text'][:200]}...")

    report.append(f"\n**Translation:**")
    report.append(f"{sample_row[f'{output_dir}_translation'][:200]}...")

    if f"{output_dir}_commentary" in sample_row and pd.notna(
        sample_row[f"{output_dir}_commentary"]
    ):
        report.append(f"\n**Commentary:**")
        report.append(f"{sample_row[f'{output_dir}_commentary'][:200]}...")

    # Add summary sample
    summary_rows = df[df[f"{output_dir}_summary"].notna()]
    if not summary_rows.empty:
        report.append(f"\n### Chapter Summary Sample")
        report.append(f"{summary_rows.iloc[0][f'{output_dir}_summary'][:300]}...")

    return "\n".join(report)


def main():
    parser = argparse.ArgumentParser(
        description="Extract complex analysis outputs from JSON files"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        help="Output directory name (defaults to OUTPUT_DIR env var)",
    )

    args = parser.parse_args()

    # Get output directory
    output_dir = args.output_dir or os.getenv("OUTPUT_DIR")
    if not output_dir:
        print(
            "Error: No output directory specified. Use --output-dir or set OUTPUT_DIR"
        )
        return

    print(f"Extracting complex analysis outputs from: {output_dir}")

    # Load JSON outputs
    json_outputs = load_json_outputs(output_dir)
    print(f"Found {len(json_outputs)} output files")

    if not json_outputs:
        print("No outputs found to extract")
        return

    # Extract to DataFrame
    df = extract_to_dataframe(json_outputs, output_dir)

    # Save extracted data
    output_csv = f"data/complex_analysis/{output_dir}_extracted.csv"
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    df.to_csv(output_csv, index=False)
    print(f"Saved extracted data to: {output_csv}")

    # Create summary report
    report = create_summary_report(df, output_dir)
    report_file = f"data/complex_analysis/{output_dir}_summary_report.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"Saved summary report to: {report_file}")


if __name__ == "__main__":
    main()
