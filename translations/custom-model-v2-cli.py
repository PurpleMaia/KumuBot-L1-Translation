#!/usr/bin/env python3
"""
Manual CLI version of custom-model-parallel-v2.py that copies prompts to clipboard
and waits for user responses instead of calling LLM APIs.

This allows testing task configurations with LLMs hosted in web browsers
by manually copying prompts and pasting responses.

Usage:
    python custom-model-v2-cli.py --task hybrid_complex_analysis_original
    python custom-model-v2-cli.py --task hybrid_complex_analysis_enhanced_fewshot
"""

import pandas as pd
import json
import os
import argparse
import re
import time
import subprocess
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, List, Any, Optional
from task_config import TaskConfig

load_dotenv()

# Environment variables
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "manual-cli-test")


class ManualCLIProcessor:
    """Process translations/analysis manually via clipboard and user input."""

    def __init__(self, task_config: TaskConfig, debug: bool = False):
        self.config = task_config
        self.debug = debug
        self.setup_output_directory()

    def setup_output_directory(self):
        """Create output directory if it doesn't exist."""
        self.output_dir = f"translations/{OUTPUT_DIR}"
        os.makedirs(self.output_dir, exist_ok=True)
        print(f"Output directory: {self.output_dir}")

    def copy_to_clipboard(self, text: str) -> bool:
        """Copy text to clipboard using system commands."""
        try:
            # Try macOS pbcopy first
            result = subprocess.run(
                ["pbcopy"], input=text, text=True, capture_output=True
            )
            if result.returncode == 0:
                return True
        except FileNotFoundError:
            pass

        try:
            # Try Linux xclip
            result = subprocess.run(
                ["xclip", "-selection", "clipboard"],
                input=text,
                text=True,
                capture_output=True,
            )
            if result.returncode == 0:
                return True
        except FileNotFoundError:
            pass

        try:
            # Try Windows clip
            result = subprocess.run(
                ["clip"], input=text, text=True, capture_output=True
            )
            if result.returncode == 0:
                return True
        except FileNotFoundError:
            pass

        return False

    def read_from_clipboard(self) -> str:
        """Read text from clipboard using system commands."""
        try:
            # Try macOS pbpaste first
            result = subprocess.run(["pbpaste"], capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout
        except FileNotFoundError:
            pass

        try:
            # Try Linux xclip
            result = subprocess.run(
                ["xclip", "-selection", "clipboard", "-o"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                return result.stdout
        except FileNotFoundError:
            pass

        try:
            # Try Windows powershell
            result = subprocess.run(
                ["powershell", "-command", "Get-Clipboard"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                return result.stdout
        except FileNotFoundError:
            pass

        return ""

    def get_user_response(self, prompt_type: str, passage_info: str = "") -> str:
        """Get LLM response from user via manual input or clipboard."""
        print(f"\n{'=' * 80}")
        print(f"🤖 PROMPT FOR {prompt_type.upper()}")
        if passage_info:
            print(f"📍 {passage_info}")
        print(f"{'=' * 80}")
        print("📋 Prompt has been copied to clipboard!")
        print("✅ Paste it into your LLM interface and copy the response back.")
        print("💬 Options:")
        print("   - Type 'c' or 'clip' to read response from clipboard")
        print("   - Type 'p' or 'paste' to manually paste response")
        print("   - Type 'q' or 'quit' to cancel entire run")
        print(f"{'=' * 80}")

        while True:
            try:
                user_input = input("Choose (c/p/q): ").strip().lower()

                if user_input in ["q", "quit", "exit"]:
                    print("\n🛑 User requested to quit the entire run")
                    raise KeyboardInterrupt("User quit")

                elif user_input in ["c", "clip", "clipboard"]:
                    # Read from clipboard
                    response = self.read_from_clipboard().strip()
                    if not response:
                        print("⚠️  Clipboard is empty or couldn't read from clipboard")
                        continue
                    print(
                        f"✅ Response read from clipboard ({len(response)} characters)"
                    )
                    return response

                elif user_input in ["p", "paste"]:
                    # Manual paste mode
                    print(
                        "💬 Paste the response below and press Enter twice when done:"
                    )

                    lines = []
                    empty_line_count = 0

                    while True:
                        try:
                            line = input()

                            if line.strip() == "":
                                empty_line_count += 1
                                if empty_line_count >= 2:  # Two consecutive empty lines
                                    break
                                lines.append(line)
                            else:
                                empty_line_count = 0
                                lines.append(line)
                        except EOFError:
                            break

                    response = "\n".join(lines).strip()

                    if not response:
                        print("⚠️  No response provided")
                        continue

                    print(f"✅ Response received ({len(response)} characters)")
                    return response

                else:
                    print(
                        f"❌ Unknown option: {user_input}. Please type 'c', 'p', or 'q'"
                    )

            except EOFError:
                return ""
            except KeyboardInterrupt:
                print("\n❌ User cancelled operation")
                raise  # Re-raise to propagate the cancellation

    def process_hybrid_dataset(self):
        """Process dataset using hybrid approach with manual interaction."""
        # Load dataset
        base_dir = Path(__file__).resolve().parents[1]
        file_path = base_dir / self.config.dataset_path

        try:
            df = pd.read_csv(file_path)
            print(f"Successfully loaded {file_path}. Found {len(df)} rows.")
        except Exception as e:
            print(f"Error loading file {file_path}: {e}")
            return

        print("Starting manual CLI processing...")
        print("You will be prompted for each passage and chapter summary.")

        # Group by chapter
        chapter_groups = df.groupby("chapter")

        try:
            for chapter, chapter_df in chapter_groups:
                print(f"\n🏷️  Processing Chapter {chapter}...")

                # Stage 1: Process passages one by one
                passage_results = []
                total_passages = len(chapter_df)

                for idx, row in chapter_df.iterrows():
                    current_passage = row["paragraph"]
                    print(
                        f"📊 Progress: Passage {current_passage} of {total_passages} passages in Chapter {chapter}"
                    )

                    passage_result = self._process_single_passage_manual(row, chapter)
                    if passage_result:
                        passage_results.append(passage_result)
                        print(
                            f"✅ Completed passage {current_passage} ({len(passage_results)}/{total_passages} successful)"
                        )
                    else:
                        print(f"⚠️  Skipped passage {current_passage}")

                print(
                    f"\n📋 Chapter {chapter} Summary: {len(passage_results)}/{total_passages} passages completed"
                )

                # Stage 2: Generate chapter summary
                if passage_results:
                    self._generate_chapter_summary_manual(chapter, passage_results)
        except KeyboardInterrupt:
            print(f"\n🛑 Processing cancelled by user")
            print(f"📁 Partial results may be available in: translations/{OUTPUT_DIR}")
            return

    def _process_single_passage_manual(
        self, row: pd.Series, chapter: str
    ) -> Dict[str, Any]:
        """Process a single passage manually."""
        hawaiian_text = row[self.config.source_column]
        paragraph = row["paragraph"]
        passage_id = row.get("passage_id", f"ch{chapter}_p{paragraph}")

        print(f"\n📝 Processing passage {paragraph} of chapter {chapter}")

        # Check for special cases (grouped commentary)
        special_case_result = self._handle_special_case_passage(row, chapter)
        if special_case_result:
            return special_case_result

        # Get passage analysis prompts
        prompts = self.config.config.get("prompts", {})
        passage_prompts = prompts.get("passage_analysis", {})

        # Format the prompt
        system_prompt = passage_prompts.get("system", "")
        user_template = passage_prompts.get("user_template", "")

        user_prompt = user_template.format(
            chapter=chapter, paragraph=paragraph, hawaiian_text=hawaiian_text
        )

        # Create a single combined prompt that works better with web interfaces
        # Most web LLMs work better with a single prompt that includes context
        full_prompt = f"{system_prompt}\n\n{user_prompt}"

        # Copy to clipboard
        if self.copy_to_clipboard(full_prompt):
            passage_info = f"Chapter {chapter}, Paragraph {paragraph}"
            response = self.get_user_response("PASSAGE ANALYSIS", passage_info)
        else:
            print("❌ Failed to copy to clipboard. Showing prompt:")
            print(full_prompt)
            passage_info = f"Chapter {chapter}, Paragraph {paragraph}"
            response = self.get_user_response("PASSAGE ANALYSIS", passage_info)

        if not response:
            print(f"❌ Skipping passage {paragraph} - no response provided")
            return None

        # Parse response
        parsed = self._parse_passage_response(response)

        # Check parsing success
        if not parsed.get("translation") and not parsed.get("commentary"):
            print(f"⚠️  Failed to parse translation/commentary from response")
            print("🔍 Response preview:", response[:200], "...")

            # Check for XML tags
            has_translation_tag = "<translation>" in response.lower()
            has_commentary_tag = "<commentary>" in response.lower()
            print(
                f"🔍 XML tags found: translation={has_translation_tag}, commentary={has_commentary_tag}"
            )

            # Ask user if they want to retry
            retry = input("🔄 Retry this passage? (y/n): ").lower().strip()
            if retry == "y":
                return self._process_single_passage_manual(row, chapter)
            else:
                return None

        # Prepare output
        output = {
            "chapter": chapter,
            "paragraph": paragraph,
            "passage_id": passage_id,
            "hawaiian_text": hawaiian_text,
            f"{OUTPUT_DIR}_translation": parsed.get("translation", ""),
            f"{OUTPUT_DIR}_commentary": parsed.get("commentary", ""),
            "raw_response": response,
            "processing_method": "manual_cli",
        }

        # Add reference data if available
        if "english_translation" in row:
            output["reference_translation"] = row["english_translation"]
        if "commentary" in row and pd.notna(row["commentary"]):
            output["reference_commentary"] = row["commentary"]

        # Save passage-level output
        self.save_output(output, f"passage_{chapter}_{paragraph}")
        print(f"✅ Saved passage {paragraph}")

        return output

    def _handle_special_case_passage(
        self, row: pd.Series, chapter: str
    ) -> Optional[Dict[str, Any]]:
        """Handle special cases like grouped commentary for paragraphs 10-14."""
        special_cases = self.config.config.get("special_cases", {})
        grouped_commentary = special_cases.get("grouped_commentary", {})

        if not grouped_commentary.get("enabled", False):
            return None

        # Check if this passage is in a special group
        groups = grouped_commentary.get("groups", [])
        for group in groups:
            if group.get("chapter") == int(chapter) and int(
                row["paragraph"]
            ) in group.get("paragraphs", []):
                print(
                    f"📋 Special case: paragraph {row['paragraph']} uses grouped commentary"
                )
                return self._process_grouped_commentary_passage_manual(
                    row, chapter, group
                )

        return None

    def _process_grouped_commentary_passage_manual(
        self, row: pd.Series, chapter: str, group: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process a passage that uses grouped commentary from another paragraph."""
        hawaiian_text = row[self.config.source_column]
        paragraph = row["paragraph"]
        passage_id = row.get("passage_id", f"ch{chapter}_p{paragraph}")

        # Generate translation only for grouped commentary passages
        prompts = self.config.config.get("prompts", {})
        passage_prompts = prompts.get("passage_analysis", {})

        system_prompt = passage_prompts.get("system", "")
        user_template = passage_prompts.get("user_template", "")

        # Modify template for translation-only
        modified_template = user_template.replace(
            "2. Detailed commentary explaining cultural context, linguistic features, and historical significance",
            "2. Brief note that this passage is part of a larger narrative section",
        ).replace(
            "- <commentary></commentary> tags for the analytical commentary",
            "- <commentary></commentary> tags for a brief note about the narrative context",
        )

        user_prompt = modified_template.format(
            chapter=chapter, paragraph=paragraph, hawaiian_text=hawaiian_text
        )

        # Create a single combined prompt that works better with web interfaces
        full_prompt = f"{system_prompt}\n\n{user_prompt}"

        # Copy to clipboard and get response
        if self.copy_to_clipboard(full_prompt):
            passage_info = (
                f"Chapter {chapter}, Paragraph {paragraph} (GROUPED COMMENTARY)"
            )
            response = self.get_user_response("PASSAGE TRANSLATION", passage_info)
        else:
            print("❌ Failed to copy to clipboard. Showing prompt:")
            print(full_prompt)
            passage_info = (
                f"Chapter {chapter}, Paragraph {paragraph} (GROUPED COMMENTARY)"
            )
            response = self.get_user_response("PASSAGE TRANSLATION", passage_info)

        if not response:
            return None

        # Parse response
        parsed = self._parse_passage_response(response)

        # Get the grouped commentary from reference data
        grouped_commentary_text = self._get_grouped_commentary(group)

        # Prepare output
        output = {
            "chapter": chapter,
            "paragraph": paragraph,
            "passage_id": passage_id,
            "hawaiian_text": hawaiian_text,
            f"{OUTPUT_DIR}_translation": parsed.get("translation", ""),
            f"{OUTPUT_DIR}_commentary": grouped_commentary_text,
            "raw_response": response,
            "special_case": "grouped_commentary",
            "processing_method": "manual_cli",
        }

        # Add reference data if available
        if "english_translation" in row:
            output["reference_translation"] = row["english_translation"]
        if "commentary" in row and pd.notna(row["commentary"]):
            output["reference_commentary"] = row["commentary"]

        # Save passage-level output
        self.save_output(output, f"passage_{chapter}_{paragraph}")
        print(f"✅ Saved grouped commentary passage {paragraph}")

        return output

    def _get_grouped_commentary(self, group: Dict[str, Any]) -> str:
        """Extract grouped commentary from the dataset."""
        try:
            dataset_path = self.config.config.get("dataset", {}).get("path", "")
            if not dataset_path:
                return f"[Grouped commentary for paragraphs {group.get('paragraphs', [])} - see paragraph {group.get('commentary_location', '')}]"

            df = pd.read_csv(dataset_path)

            # Extract paragraph number from commentary_location
            commentary_location = group.get("commentary_location", "")
            if commentary_location.startswith("paragraph_"):
                commentary_paragraph = int(commentary_location.split("_")[1])

                # Find the row with the commentary
                commentary_row = df[df["paragraph"] == commentary_paragraph]
                if not commentary_row.empty and "commentary" in commentary_row.columns:
                    commentary_text = commentary_row["commentary"].iloc[0]
                    if pd.notna(commentary_text):
                        # Extract the specific section for paragraphs 10-14
                        if "**Paragraphs 10—14**" in commentary_text:
                            parts = commentary_text.split("**Paragraphs 10—14**")
                            if len(parts) > 1:
                                return f"**Paragraphs 10—14**{parts[1]}"
                        return commentary_text

            return f"[Grouped commentary for paragraphs {group.get('paragraphs', [])} - see paragraph {group.get('commentary_location', '')}]"

        except Exception as e:
            print(f"⚠️  Error loading grouped commentary: {e}")
            return f"[Grouped commentary for paragraphs {group.get('paragraphs', [])} - see paragraph {group.get('commentary_location', '')}]"

    def _generate_chapter_summary_manual(
        self, chapter: str, passage_results: List[Dict[str, Any]]
    ):
        """Generate chapter summary manually."""
        print(f"\n📊 Generating summary for Chapter {chapter}...")

        # Collect all translations
        all_translations = []
        for result in sorted(passage_results, key=lambda x: int(x["paragraph"])):
            translation = result.get(f"{OUTPUT_DIR}_translation", "")
            if translation:
                all_translations.append(
                    f"Paragraph {result['paragraph']}:\n{translation}"
                )

        if not all_translations:
            print("❌ No translations found for summary generation")
            return

        # Get chapter summary prompts
        prompts = self.config.config.get("prompts", {})
        summary_prompts = prompts.get("chapter_summary", {})

        # Format the prompt
        system_prompt = summary_prompts.get("system", "")
        user_template = summary_prompts.get("user_template", "")

        all_translations_text = "\n\n".join(all_translations)
        user_prompt = user_template.format(
            chapter=chapter, all_translations=all_translations_text
        )

        # Create a single combined prompt that works better with web interfaces
        full_prompt = f"{system_prompt}\n\n{user_prompt}"

        # Copy to clipboard and get response
        if self.copy_to_clipboard(full_prompt):
            chapter_info = f"Chapter {chapter} Summary"
            response = self.get_user_response("CHAPTER SUMMARY", chapter_info)
        else:
            print("❌ Failed to copy to clipboard. Showing prompt:")
            print(full_prompt)
            chapter_info = f"Chapter {chapter} Summary"
            response = self.get_user_response("CHAPTER SUMMARY", chapter_info)

        if not response:
            print("❌ No summary response provided")
            return

        # Parse summary
        parsed = self._parse_summary_response(response)

        # Create chapter manifest
        manifest = {
            "chapter": chapter,
            "passage_count": len(passage_results),
            "passage_references": [
                f"{self.config.task_name}_passage_{chapter}_{r['paragraph']}.json"
                for r in sorted(passage_results, key=lambda x: int(x["paragraph"]))
            ],
            f"{OUTPUT_DIR}_summary": parsed.get("summary", ""),
            "raw_summary_response": response,
            "processing_method": "manual_cli",
        }

        # Save manifest
        self.save_output(manifest, f"chapter_{chapter}_manifest")
        print(f"✅ Summary saved for Chapter {chapter}")

    def _parse_passage_response(self, response: str) -> Dict[str, str]:
        """Parse passage-level response for translation and commentary."""
        parsed = {}

        # Extract translation
        translation_match = re.search(
            r"<translation>(.*?)</translation>", response, re.DOTALL | re.IGNORECASE
        )
        if translation_match:
            parsed["translation"] = translation_match.group(1).strip()

        # Extract commentary
        commentary_match = re.search(
            r"<commentary>(.*?)</commentary>", response, re.DOTALL | re.IGNORECASE
        )
        if commentary_match:
            parsed["commentary"] = commentary_match.group(1).strip()
        else:
            # If no closing tag, extract everything from opening tag to end
            commentary_match = re.search(
                r"<commentary>(.*)", response, re.DOTALL | re.IGNORECASE
            )
            if commentary_match:
                parsed["commentary"] = commentary_match.group(1).strip()

        return parsed

    def _parse_summary_response(self, response: str) -> Dict[str, str]:
        """Parse chapter summary response."""
        parsed = {}

        # Extract summary
        summary_match = re.search(
            r"<summary>(.*?)</summary>", response, re.DOTALL | re.IGNORECASE
        )
        if summary_match:
            parsed["summary"] = summary_match.group(1).strip()
        else:
            # If no tags, use entire response as summary
            parsed["summary"] = response.strip()

        return parsed

    def save_output(self, output_data: Dict[str, Any], identifier: str):
        """Save output data to JSON file."""
        output_file = os.path.join(
            self.output_dir, f"{self.config.task_name}_{identifier}.json"
        )

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)

        if self.debug:
            print(f"📁 Saved output to {output_file}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Manual CLI version for testing task configurations with web-based LLMs"
    )
    parser.add_argument(
        "--task",
        type=str,
        required=True,
        help="Task configuration name (e.g., hybrid_complex_analysis_original, hybrid_complex_analysis_enhanced_fewshot)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug output with detailed file operations",
    )

    args = parser.parse_args()

    # Check for OUTPUT_DIR environment variable
    if "OUTPUT_DIR" not in os.environ:
        print("⚠️  OUTPUT_DIR not set. Using default: manual-cli-test")
        os.environ["OUTPUT_DIR"] = "manual-cli-test"

    # Load task configuration
    config_path = f"task_configs/{args.task}.json"

    try:
        task_config = TaskConfig(config_path)
        print(f"✅ Loaded task configuration: {task_config.task_name}")
        print(f"📋 Task type: {task_config.task_type}")
        print(f"📝 Description: {task_config.config.get('description', 'N/A')}")
    except Exception as e:
        print(f"❌ Error loading task configuration: {e}")
        return

    # Only support hybrid_analysis for now
    if task_config.task_type != "hybrid_analysis":
        print(
            f"❌ Only hybrid_analysis task type is supported, got: {task_config.task_type}"
        )
        print(
            "💡 Try: --task hybrid_complex_analysis_original or --task hybrid_complex_analysis_enhanced_fewshot"
        )
        return

    print(f"\n🚀 Starting manual CLI processing...")
    print(f"📁 Output directory: translations/{OUTPUT_DIR}")
    print(f"🔧 Task configuration: {args.task}")
    print(f"💻 Clipboard functionality will be used for prompts")
    print(f"{'=' * 80}")

    # Process dataset
    processor = ManualCLIProcessor(task_config, debug=args.debug)
    processor.process_hybrid_dataset()

    print(f"\n✅ Manual CLI processing completed!")
    print(f"📁 Check output files in: translations/{OUTPUT_DIR}")


if __name__ == "__main__":
    main()
