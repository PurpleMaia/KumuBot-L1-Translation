#!/usr/bin/env python3
"""
Convert the Namakaokapaoo analysis from markdown format to CSV format
suitable for the complex analysis task.
"""

import csv
import re
from pathlib import Path


def parse_markdown_table(md_file_path):
    """Parse the markdown file and extract the table data."""
    with open(md_file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Find all table rows (excluding header and separator rows)
    rows = []
    current_row = []
    in_table = False

    for line in content.split("\n"):
        # Check if we're in a table
        if line.strip().startswith("| Source Text"):
            in_table = True
            continue
        elif line.strip().startswith("| -----"):
            continue
        elif in_table and line.strip().startswith("|"):
            # Extract cells from the line
            cells = [cell.strip() for cell in line.split("|")[1:-1]]
            if len(cells) == 3:  # We expect 3 columns
                # Check if this is a continuation of the previous row
                if cells[0] and not cells[0].startswith(" "):
                    # New row
                    if current_row:
                        rows.append(current_row)
                    current_row = cells
                else:
                    # Continuation of previous row
                    for i in range(3):
                        if cells[i]:
                            current_row[i] += "\n" + cells[i]
        elif in_table and not line.strip():
            # End of table
            if current_row:
                rows.append(current_row)
                current_row = []
            in_table = False

    # Don't forget the last row
    if current_row:
        rows.append(current_row)

    return rows


def extract_passages(rows):
    """Extract individual passages from the table rows."""
    passages = []

    for row in rows:
        hawaiian_text = row[0]
        english_translation = row[1]
        commentary = row[2]

        # Extract paragraph numbers from Hawaiian text
        paragraph_matches = re.findall(r"\*\*(\d+):\*\*", hawaiian_text)

        # Split text by paragraph numbers
        hawaiian_paragraphs = re.split(r"\*\*\d+:\*\*", hawaiian_text)
        english_paragraphs = re.split(r"\*\*\d+:\*\*", english_translation)

        # Remove empty first element from split
        if hawaiian_paragraphs and not hawaiian_paragraphs[0].strip():
            hawaiian_paragraphs = hawaiian_paragraphs[1:]
        if english_paragraphs and not english_paragraphs[0].strip():
            english_paragraphs = english_paragraphs[1:]

        # Combine paragraphs with their numbers
        for i, para_num in enumerate(paragraph_matches):
            if i < len(hawaiian_paragraphs) and i < len(english_paragraphs):
                passages.append(
                    {
                        "passage_id": f"namakaokapaoo_ch1_p{para_num}",
                        "chapter": "1",
                        "paragraph": para_num,
                        "hawaiian_text": hawaiian_paragraphs[i].strip(),
                        "english_translation": english_paragraphs[i].strip(),
                        "commentary": commentary
                        if i == 0
                        else "",  # Only include commentary once per row
                    }
                )

    return passages


def extract_summary(md_file_path):
    """Extract the summary section from the markdown file."""
    with open(md_file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Find the summary section
    summary_match = re.search(
        r"\*\*Summary:\*\*\s*(.*?)(?=\*\*Bibliography|\Z)", content, re.DOTALL
    )
    if summary_match:
        return summary_match.group(1).strip()
    return ""


def create_csv(passages, summary, output_path):
    """Create CSV file with the passages and summary."""
    fieldnames = [
        "passage_id",
        "chapter",
        "paragraph",
        "hawaiian_text",
        "english_translation",
        "commentary",
        "overall_summary",
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for i, passage in enumerate(passages):
            # Add summary only to the last row
            if i == len(passages) - 1:
                passage["overall_summary"] = summary
            else:
                passage["overall_summary"] = ""
            writer.writerow(passage)


def main():
    # Input and output paths
    md_file = Path(
        "source-material/Kaao-no-Namakaokapaoo-Mokuna-1-ANALYSIS_modified-by-david-for-conversion-to-MD-and-CSV.md"
    )
    output_csv = Path("data/complex_analysis/namakaokapaoo_dataset.csv")

    # Parse the markdown file
    print(f"Parsing {md_file}...")
    rows = parse_markdown_table(md_file)
    print(f"Found {len(rows)} table rows")

    # Extract passages
    passages = extract_passages(rows)
    print(f"Extracted {len(passages)} passages")

    # Extract summary
    summary = extract_summary(md_file)
    print(f"Extracted summary ({len(summary)} characters)")

    # Create CSV
    create_csv(passages, summary, output_csv)
    print(f"Created {output_csv}")


if __name__ == "__main__":
    main()
