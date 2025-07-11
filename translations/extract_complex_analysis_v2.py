#!/usr/bin/env python3
"""
Extract complex analysis outputs (translations, commentary, summaries)
from JSON files and compile them into a structured format.

This version supports both:
1. Legacy format: All passages in a single complex_analysis_chapter_X.json file
2. Hybrid format: Individual passage files + chapter manifest
"""

import json
import os
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Optional
import argparse


def detect_output_format(output_dir: str) -> str:
    """Detect whether output is in legacy or hybrid format."""
    output_path = Path(f"translations/{output_dir}")

    if not output_path.exists():
        raise ValueError(f"Output directory {output_path} does not exist")

    # Check for hybrid format (passage files)
    passage_files = list(output_path.glob("*_passage_*.json"))
    manifest_files = list(output_path.glob("*_chapter_*_manifest.json"))

    if passage_files and manifest_files:
        return "hybrid"

    # Check for legacy format
    complex_files = list(output_path.glob("complex_analysis_*.json"))
    if complex_files:
        return "legacy"

    # Check for any chapter files (could be either format)
    chapter_files = list(output_path.glob("*chapter*.json"))
    if chapter_files:
        # If filenames contain "manifest", it's hybrid
        if any("manifest" in f.name for f in chapter_files):
            return "hybrid"
        else:
            return "legacy"

    raise ValueError(f"Could not detect output format in {output_path}")


def load_legacy_outputs(output_dir: str) -> List[Dict[str, Any]]:
    """Load all JSON outputs from the specified directory (legacy format)."""
    json_files = []
    output_path = Path(f"translations/{output_dir}")

    # Find all complex_analysis JSON files
    for json_file in sorted(output_path.glob("complex_analysis_*.json")):
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            json_files.append(data)

    return json_files


def load_hybrid_outputs(output_dir: str) -> List[Dict[str, Any]]:
    """Load outputs from hybrid format (passage files + manifests)."""
    output_path = Path(f"translations/{output_dir}")
    chapters_data = []

    # Find all chapter manifest files
    manifest_files = sorted(output_path.glob("*_chapter_*_manifest.json"))

    for manifest_file in manifest_files:
        with open(manifest_file, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        chapter = manifest.get("chapter", "")

        # Create a structure similar to legacy format for compatibility
        chapter_data = {
            "chapter": chapter,
            "passages": [],
            "passage_ids": [],
            f"{output_dir}_summary": manifest.get(f"{output_dir}_summary", ""),
            "reference_summary": manifest.get("reference_summary", ""),
        }

        # Load individual passage files
        for passage_ref in manifest.get("passage_references", []):
            passage_file = output_path / passage_ref
            if passage_file.exists():
                with open(passage_file, "r", encoding="utf-8") as f:
                    passage_data = json.load(f)

                # Add passage info
                chapter_data["passages"].append(
                    {
                        "paragraph": passage_data.get("paragraph", ""),
                        "hawaiian_text": passage_data.get("hawaiian_text", ""),
                    }
                )
                chapter_data["passage_ids"].append(passage_data.get("passage_id", ""))

                # Store translations and commentary at chapter level for extraction
                paragraph = passage_data.get("paragraph", "")

                # Initialize storage if needed
                if f"{output_dir}_translation" not in chapter_data:
                    chapter_data[f"{output_dir}_translation"] = {}
                if f"{output_dir}_commentary" not in chapter_data:
                    chapter_data[f"{output_dir}_commentary"] = {}

                # Store by paragraph
                chapter_data[f"{output_dir}_translation"][paragraph] = passage_data.get(
                    f"{output_dir}_translation", ""
                )
                chapter_data[f"{output_dir}_commentary"][paragraph] = passage_data.get(
                    f"{output_dir}_commentary", ""
                )

                # Store reference data
                if "reference_translation" in passage_data:
                    if "reference_translations" not in chapter_data:
                        chapter_data["reference_translations"] = {}
                    chapter_data["reference_translations"][paragraph] = passage_data[
                        "reference_translation"
                    ]

                if "reference_commentary" in passage_data:
                    if "reference_commentary" not in chapter_data:
                        chapter_data["reference_commentary"] = {}
                    chapter_data["reference_commentary"][paragraph] = passage_data[
                        "reference_commentary"
                    ]

        chapters_data.append(chapter_data)

    return chapters_data


def extract_legacy_to_dataframe(
    json_outputs: List[Dict[str, Any]], output_dir: str
) -> pd.DataFrame:
    """Extract data from legacy JSON outputs into a DataFrame."""
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


def extract_hybrid_to_dataframe(
    json_outputs: List[Dict[str, Any]], output_dir: str
) -> pd.DataFrame:
    """Extract data from hybrid format outputs into a DataFrame."""
    rows = []

    for chapter_data in json_outputs:
        chapter = chapter_data.get("chapter", "")
        passages = chapter_data.get("passages", [])

        # Get translation and commentary dictionaries
        translations = chapter_data.get(f"{output_dir}_translation", {})
        commentaries = chapter_data.get(f"{output_dir}_commentary", {})
        ref_translations = chapter_data.get("reference_translations", {})
        ref_commentaries = chapter_data.get("reference_commentary", {})

        # Process each passage
        for passage in passages:
            paragraph = str(passage.get("paragraph", ""))

            row = {
                "chapter": chapter,
                "paragraph": paragraph,
                "hawaiian_text": passage.get("hawaiian_text", ""),
                f"{output_dir}_translation": translations.get(paragraph, ""),
                f"{output_dir}_commentary": commentaries.get(paragraph, ""),
            }

            # Add reference data if available
            if paragraph in ref_translations:
                row["reference_translation"] = ref_translations[paragraph]

            if isinstance(ref_commentaries, dict) and paragraph in ref_commentaries:
                row["reference_commentary"] = ref_commentaries[paragraph]
            elif isinstance(ref_commentaries, str) and paragraph == "1":
                # Legacy format where commentary is only in first row
                row["reference_commentary"] = ref_commentaries

            rows.append(row)

        # Add summary to the last row of each chapter
        if rows and chapter_data.get(f"{output_dir}_summary"):
            rows[-1][f"{output_dir}_summary"] = chapter_data[f"{output_dir}_summary"]
            if "reference_summary" in chapter_data:
                rows[-1]["reference_summary"] = chapter_data["reference_summary"]

    return pd.DataFrame(rows)


def create_summary_report(df: pd.DataFrame, output_dir: str, format_type: str) -> str:
    """Create a summary report of the complex analysis."""
    report = []
    report.append(f"# Complex Analysis Summary Report")
    report.append(f"## Model: {output_dir}")
    report.append(f"## Format: {format_type}\n")

    # Statistics
    report.append("### Statistics")
    report.append(f"- Total chapters analyzed: {df['chapter'].nunique()}")
    report.append(f"- Total passages analyzed: {len(df)}")

    # Count non-empty translations and commentary
    trans_col = f"{output_dir}_translation"
    comm_col = f"{output_dir}_commentary"
    summ_col = f"{output_dir}_summary"

    trans_count = df[trans_col].apply(lambda x: bool(x) and str(x).strip() != "").sum()
    comm_count = df[comm_col].apply(lambda x: bool(x) and str(x).strip() != "").sum()
    summ_count = df[summ_col].apply(lambda x: bool(x) and str(x).strip() != "").sum()

    report.append(f"- Passages with translations: {trans_count}")
    report.append(f"- Passages with commentary: {comm_count}")
    report.append(f"- Chapters with summaries: {summ_count}\n")

    # Sample outputs
    report.append("### Sample Outputs")

    # Get first passage with all components
    sample_df = df[df[trans_col].notna() & (df[trans_col] != "")]
    sample_row = sample_df.iloc[0] if not sample_df.empty else None

    if sample_row is not None:
        report.append(
            f"\n#### Chapter {sample_row['chapter']}, Paragraph {sample_row['paragraph']}"
        )
        report.append(f"\n**Hawaiian Text:**")
        report.append(f"{sample_row['hawaiian_text'][:200]}...")

        report.append(f"\n**Translation:**")
        report.append(f"{sample_row[trans_col][:200]}...")

        if (
            comm_col in sample_row
            and pd.notna(sample_row[comm_col])
            and sample_row[comm_col]
        ):
            report.append(f"\n**Commentary:**")
            report.append(f"{sample_row[comm_col][:200]}...")

    # Add summary sample
    summary_rows = df[df[summ_col].notna() & (df[summ_col] != "")]
    if not summary_rows.empty:
        report.append(f"\n### Chapter Summary Sample")
        report.append(f"{summary_rows.iloc[0][summ_col][:300]}...")

    return "\n".join(report)


def main():
    parser = argparse.ArgumentParser(
        description="Extract complex analysis outputs from JSON files (supports both legacy and hybrid formats)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        help="Output directory name (defaults to OUTPUT_DIR env var)",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["auto", "legacy", "hybrid"],
        default="auto",
        help="Output format to expect (default: auto-detect)",
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

    # Detect format
    if args.format == "auto":
        try:
            format_type = detect_output_format(output_dir)
            print(f"Auto-detected format: {format_type}")
        except ValueError as e:
            print(f"Error: {e}")
            return
    else:
        format_type = args.format

    # Load outputs based on format
    try:
        if format_type == "legacy":
            json_outputs = load_legacy_outputs(output_dir)
            print(f"Found {len(json_outputs)} legacy output files")

            if not json_outputs:
                print("No outputs found to extract")
                return

            # Extract to DataFrame
            df = extract_legacy_to_dataframe(json_outputs, output_dir)

        else:  # hybrid
            json_outputs = load_hybrid_outputs(output_dir)
            print(f"Found {len(json_outputs)} chapters in hybrid format")

            if not json_outputs:
                print("No outputs found to extract")
                return

            # Extract to DataFrame
            df = extract_hybrid_to_dataframe(json_outputs, output_dir)

    except Exception as e:
        print(f"Error loading outputs: {e}")
        return

    # Save extracted data
    output_csv = f"data/complex_analysis/{output_dir}_extracted.csv"
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    df.to_csv(output_csv, index=False)
    print(f"Saved extracted data to: {output_csv}")

    # Create summary report
    report = create_summary_report(df, output_dir, format_type)
    report_file = f"data/complex_analysis/{output_dir}_summary_report.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"Saved summary report to: {report_file}")

    # Print summary statistics
    trans_col = f"{output_dir}_translation"
    comm_col = f"{output_dir}_commentary"
    trans_count = df[trans_col].apply(lambda x: bool(x) and str(x).strip() != "").sum()
    comm_count = df[comm_col].apply(lambda x: bool(x) and str(x).strip() != "").sum()

    print(f"\nExtraction Summary:")
    print(f"- Total passages: {len(df)}")
    print(f"- Passages with translations: {trans_count}")
    print(f"- Passages with commentary: {comm_count}")

    if comm_count == len(df):
        print("✓ All passages have commentary!")
    else:
        print(f"⚠ Only {comm_count}/{len(df)} passages have commentary")


if __name__ == "__main__":
    main()
