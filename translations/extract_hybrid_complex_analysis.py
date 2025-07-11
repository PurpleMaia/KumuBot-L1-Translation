#!/usr/bin/env python3
"""
Extract hybrid complex analysis outputs from individual passage JSON files
and compile them into a structured format.
"""

import json
import os
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any
import argparse
import re
from dotenv import load_dotenv

load_dotenv()


def load_passage_outputs(output_dir: str) -> List[Dict[str, Any]]:
    """Load all passage JSON outputs from the specified directory."""
    passage_files = []
    output_path = Path(f"translations/{output_dir}")

    if not output_path.exists():
        print(f"Output directory {output_path} does not exist")
        return []

    # Find all hybrid_complex_analysis_passage JSON files
    pattern = re.compile(r"hybrid_complex_analysis_passage_(\d+)_(\d+)\.json")

    for json_file in output_path.glob("hybrid_complex_analysis_passage_*.json"):
        match = pattern.search(json_file.name)
        if match:
            chapter = int(match.group(1))
            paragraph = int(match.group(2))

            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                data["_file_chapter"] = chapter
                data["_file_paragraph"] = paragraph
                passage_files.append(data)

    # Sort by chapter and paragraph
    passage_files.sort(key=lambda x: (x["_file_chapter"], x["_file_paragraph"]))
    return passage_files


def load_chapter_manifest(output_dir: str) -> Dict[str, Any]:
    """Load chapter manifest if it exists."""
    output_path = Path(f"translations/{output_dir}")
    manifest_files = list(
        output_path.glob("hybrid_complex_analysis_chapter_*_manifest.json")
    )

    if manifest_files:
        with open(manifest_files[0], "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def extract_to_dataframe(
    passage_outputs: List[Dict[str, Any]], output_dir: str
) -> pd.DataFrame:
    """Extract data from passage outputs into a DataFrame."""
    rows = []

    for passage in passage_outputs:
        # Extract basic passage info
        chapter = passage.get("chapter", passage.get("_file_chapter", ""))
        paragraph = passage.get("paragraph", passage.get("_file_paragraph", ""))

        row = {
            "passage_id": passage.get("passage_id", f"ch{chapter}_p{paragraph}"),
            "chapter": chapter,
            "paragraph": paragraph,
            "hawaiian_text": passage.get("hawaiian_text", ""),
            f"{output_dir}_translation": passage.get(f"{output_dir}_translation", ""),
            f"{output_dir}_commentary": passage.get(f"{output_dir}_commentary", ""),
        }

        # Add reference data if available
        if "reference_translation" in passage:
            row["reference_translation"] = passage["reference_translation"]
        if "reference_commentary" in passage:
            row["reference_commentary"] = passage["reference_commentary"]

        rows.append(row)

    df = pd.DataFrame(rows)

    # Add chapter summary to the first row of each chapter (standardized format)
    chapter_manifest = load_chapter_manifest(output_dir)
    if chapter_manifest and f"{output_dir}_summary" in chapter_manifest:
        # Find the first row of the chapter and add the summary
        first_row_idx = df.index[0]  # Assuming single chapter for now
        df.loc[first_row_idx, f"{output_dir}_summary"] = chapter_manifest[
            f"{output_dir}_summary"
        ]

        if "reference_summary" in chapter_manifest:
            df.loc[first_row_idx, "reference_summary"] = chapter_manifest[
                "reference_summary"
            ]

    return df


def create_summary_report(df: pd.DataFrame, output_dir: str) -> str:
    """Create a summary report of the hybrid complex analysis."""
    report = []
    report.append(f"# Hybrid Complex Analysis Summary Report")
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

    # Count summaries (only non-empty ones)
    summary_count = (
        df[f"{output_dir}_summary"].notna().sum()
        if f"{output_dir}_summary" in df.columns
        else 0
    )
    report.append(f"- Chapters with summaries: {summary_count}\n")

    # Completion percentage
    total_passages = len(df)
    completed_translations = df[f"{output_dir}_translation"].notna().sum()
    completed_commentary = df[f"{output_dir}_commentary"].notna().sum()

    report.append("### Completion Rates")
    report.append(
        f"- Translation completion: {completed_translations}/{total_passages} ({100 * completed_translations / total_passages:.1f}%)"
    )
    report.append(
        f"- Commentary completion: {completed_commentary}/{total_passages} ({100 * completed_commentary / total_passages:.1f}%)"
    )

    # Quality metrics
    report.append(
        f"- Average translation length: {df[f'{output_dir}_translation'].str.len().mean():.0f} characters"
    )
    report.append(
        f"- Average commentary length: {df[f'{output_dir}_commentary'].str.len().mean():.0f} characters\n"
    )

    # Sample outputs
    report.append("### Sample Outputs")

    # Get first passage with all components
    complete_passages = df[
        (df[f"{output_dir}_translation"].notna())
        & (df[f"{output_dir}_commentary"].notna())
    ]

    if not complete_passages.empty:
        sample_row = complete_passages.iloc[0]

        report.append(
            f"\n#### Chapter {sample_row['chapter']}, Paragraph {sample_row['paragraph']}"
        )
        report.append(f"**Passage ID:** {sample_row['passage_id']}")

        report.append(f"\n**Hawaiian Text:**")
        hawaiian_text = sample_row["hawaiian_text"]
        report.append(
            f"{hawaiian_text[:300]}{'...' if len(hawaiian_text) > 300 else ''}"
        )

        report.append(f"\n**Translation:**")
        translation = sample_row[f"{output_dir}_translation"]
        report.append(f"{translation[:300]}{'...' if len(translation) > 300 else ''}")

        report.append(f"\n**Commentary:**")
        commentary = sample_row[f"{output_dir}_commentary"]
        report.append(f"{commentary[:500]}{'...' if len(commentary) > 500 else ''}")

    # Add summary sample if available
    if f"{output_dir}_summary" in df.columns:
        summary_rows = df[df[f"{output_dir}_summary"].notna()]
        if not summary_rows.empty:
            report.append(f"\n### Chapter Summary Sample")
            summary = summary_rows.iloc[0][f"{output_dir}_summary"]
            report.append(f"{summary[:500]}{'...' if len(summary) > 500 else ''}")

    return "\n".join(report)


def main():
    parser = argparse.ArgumentParser(
        description="Extract hybrid complex analysis outputs from individual passage JSON files"
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

    print(f"Extracting hybrid complex analysis outputs from: {output_dir}")

    # Load passage outputs
    passage_outputs = load_passage_outputs(output_dir)
    print(f"Found {len(passage_outputs)} passage files")

    if not passage_outputs:
        print("No passage outputs found to extract")
        return

    # Extract to DataFrame
    df = extract_to_dataframe(passage_outputs, output_dir)
    print(f"Extracted {len(df)} passages")

    # Save extracted data
    output_csv = f"data/complex_analysis/{output_dir}_hybrid_extracted.csv"
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    df.to_csv(output_csv, index=False)
    print(f"Saved extracted data to: {output_csv}")

    # Create summary report
    report = create_summary_report(df, output_dir)
    report_file = f"data/complex_analysis/{output_dir}_hybrid_summary_report.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"Saved summary report to: {report_file}")


if __name__ == "__main__":
    main()
