#!/usr/bin/env python3
"""
Refactored custom model parallel translator that supports multiple task types
through configuration files.

Usage:
    python custom-model-parallel-v2.py --task simple_translation
    python custom-model-parallel-v2.py --task complex_analysis
"""

import pandas as pd
import json
import os
import requests
import argparse
import re
import time
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, List, Any, Optional
from task_config import TaskConfig

load_dotenv()

# Environment variables
OUTPUT_DIR = os.getenv("OUTPUT_DIR")
API_KEY = os.getenv("OPENAI_API_KEY_KOA")
BASE_URL = os.getenv("OPENAI_API_BASE_URL")
MODEL_NAME = os.getenv("OPENAI_MODEL_NAME", "gpt-4o")
MAX_PARALLEL = int(os.getenv("MAX_PARALLEL", "3"))
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "8096"))
SELF_REASONING_PARSER = os.getenv("SELF_REASONING_PARSER", "").lower() in [
    "true",
    "1",
    "yes",
]
USE_STREAMING = os.getenv("USE_STREAMING", "true").lower() in [
    "true",
    "1",
    "yes",
]


class TaskProcessor:
    """Process translations/analysis based on task configuration."""

    def __init__(self, task_config: TaskConfig, debug: bool = False):
        self.config = task_config
        self.debug = debug
        self.validate_environment()
        self.setup_output_directory()

    def validate_environment(self):
        """Validate required environment variables."""
        if not OUTPUT_DIR:
            raise ValueError(
                "OUTPUT_DIR not found in environment variables. Please check your .env file."
            )
        if not API_KEY:
            raise ValueError(
                "OPENAI_API_KEY_KOA not found in environment variables. Please check your .env file."
            )
        if not BASE_URL:
            raise ValueError(
                "OPENAI_API_BASE_URL not found in environment variables. Please check your .env file."
            )

    def setup_output_directory(self):
        """Create output directory if it doesn't exist."""
        self.output_dir = f"translations/{OUTPUT_DIR}"
        os.makedirs(self.output_dir, exist_ok=True)

    def call_llm(self, prompt: str, system_prompt: str = None) -> Optional[str]:
        """Call the LLM API with the given prompt."""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}",
        }

        # Use provided system prompt or fall back to config
        system_msg = (
            system_prompt if system_prompt is not None else self.config.system_prompt
        )

        # can make Qwen3 models not think by putting this in the sys prompt: "content": "/no_think "+system_msg
        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": prompt},
        ]

        payload = {
            "model": MODEL_NAME,
            "messages": messages,
            "max_tokens": MAX_TOKENS,
            "stream": USE_STREAMING,
        }

        url = BASE_URL.rstrip("/") + "/chat/completions"

        # Set longer timeout for complex analysis tasks
        timeout_seconds = 600  # 10 minutes

        try:
            print(f"Making API request with {timeout_seconds}s timeout...")
            response = requests.post(
                url, headers=headers, json=payload, timeout=timeout_seconds
            )

            if response.status_code == 200:
                if USE_STREAMING:
                    # Handle streaming response
                    llm_content = ""
                    print("Receiving streaming response...")
                    for line in response.iter_lines():
                        if line:
                            line_text = line.decode("utf-8")
                            if line_text.startswith("data: "):
                                data_text = line_text[6:]  # Remove 'data: ' prefix
                                if data_text.strip() == "[DONE]":
                                    break
                                try:
                                    chunk_data = json.loads(data_text)
                                    if (
                                        "choices" in chunk_data
                                        and len(chunk_data["choices"]) > 0
                                    ):
                                        delta = chunk_data["choices"][0].get(
                                            "delta", {}
                                        )
                                        if "content" in delta:
                                            content_chunk = delta["content"]
                                            llm_content += content_chunk
                                            if self.debug:
                                                print(content_chunk, end="", flush=True)
                                except json.JSONDecodeError:
                                    continue
                    if self.debug:
                        print()  # New line after streaming
                    else:
                        print("✓ Response received")
                else:
                    # Handle non-streaming response
                    llm_content = response.json()["choices"][0]["message"]["content"]

                # Apply self-reasoning parser if enabled
                if SELF_REASONING_PARSER:
                    print("Stripping <think> content...")
                    llm_content = re.sub(
                        r"<think>.*?</think>", "", llm_content, flags=re.DOTALL
                    )

                # Debug: Show LLM response content
                if self.debug:
                    print(f"\n--- LLM Response ---")
                    print(llm_content)
                    print(f"--- End Response ---\n")

                return llm_content
            else:
                print(f"API Error: {response.status_code}")
                print(
                    f"Response: {response.text[:1000]}..."
                )  # Truncate long error messages
                return None

        except requests.exceptions.Timeout:
            print(f"Request timed out after {timeout_seconds} seconds")
            return None
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            return None

    def process_simple_translation(self, row: pd.Series, idx: int) -> Dict[str, Any]:
        """Process a single row for simple translation task."""
        source_text = row[self.config.source_column]

        # Format the prompt
        prompt = self.config.format_user_prompt(source_text=source_text)

        # Call LLM
        response = self.call_llm(prompt)
        if not response:
            return None

        # Parse output
        parsed = self.config.parse_output(response)

        # Prepare output data
        output_data = {
            "row_id": idx,
            f"{self.config.source_column}_text": source_text,
            "reference_translation": row[
                list(self.config.reference_columns.values())[0]
            ],
            f"{OUTPUT_DIR}_translation": parsed.get("translation", ""),
            "raw_response": response,
        }

        return output_data

    def process_complex_analysis(self, group: pd.DataFrame) -> Dict[str, Any]:
        """Process a group of passages for complex analysis task."""
        # Prepare passages
        passages = []
        for _, row in group.iterrows():
            passage_data = {
                "paragraph": str(row["paragraph"]),
                "hawaiian_text": str(row[self.config.source_column]),
            }
            passages.append(passage_data)

        # Format passages
        formatted_passages = self.config.format_passages(passages)

        # Get chapter info
        chapter = str(group.iloc[0]["chapter"])

        # Format the prompt
        prompt = self.config.format_user_prompt(
            chapter=chapter, passages=formatted_passages
        )

        # Call LLM
        response = self.call_llm(prompt)
        if not response:
            return None

        # Parse output
        parsed = self.config.parse_output(response)

        # Prepare output data
        output_data = {
            "chapter": chapter,
            "passage_ids": group["passage_id"].tolist(),
            "passages": passages,
            f"{OUTPUT_DIR}_translation": parsed.get("translation", ""),
            f"{OUTPUT_DIR}_commentary": parsed.get("commentary", ""),
            f"{OUTPUT_DIR}_summary": parsed.get("summary", ""),
            "raw_response": response,
        }

        # Add reference data if available
        if "english_translation" in group.columns:
            output_data["reference_translations"] = group[
                "english_translation"
            ].tolist()
        if "commentary" in group.columns:
            output_data["reference_commentary"] = group["commentary"].iloc[0]
        if "overall_summary" in group.columns:
            # Get the summary from the last row (where it's stored)
            summary_rows = group[group["overall_summary"].notna()]
            if not summary_rows.empty:
                output_data["reference_summary"] = summary_rows.iloc[0][
                    "overall_summary"
                ]

        return output_data

    def save_output(self, output_data: Dict[str, Any], identifier: str):
        """Save output data to JSON file."""
        output_file = os.path.join(
            self.output_dir, f"{self.config.task_name}_{identifier}.json"
        )

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)

        print(f"Saved output to {output_file}")

    def process_dataset(self):
        """Process the entire dataset based on task configuration."""
        # Load dataset
        base_dir = Path(__file__).resolve().parents[1]
        file_path = base_dir / self.config.dataset_path

        try:
            df = pd.read_csv(file_path)
            print(f"Successfully loaded {file_path}. Found {len(df)} rows.")
        except Exception as e:
            print(f"Error loading file {file_path}: {e}")
            return

        # Process based on task type
        if self.config.task_type == "translation":
            self._process_simple_dataset(df)
        elif self.config.task_type == "analysis":
            self._process_complex_dataset(df)
        elif self.config.task_type == "hybrid_analysis":
            self._process_hybrid_dataset(df)
        else:
            raise ValueError(f"Unknown task type: {self.config.task_type}")

    def _process_simple_dataset(self, df: pd.DataFrame):
        """Process dataset for simple translation tasks."""
        with ThreadPoolExecutor(max_workers=MAX_PARALLEL) as executor:
            futures = []

            for idx, row in df.iterrows():
                source_text = row.get(self.config.source_column)
                if pd.isna(source_text) or not source_text:
                    print(f"Skipping row {idx}: Empty source text")
                    continue

                future = executor.submit(self._process_simple_row, row, idx)
                futures.append(future)

            # Process results
            for future in as_completed(futures):
                try:
                    result = future.result()
                    if result:
                        self.save_output(result, f"row_{result['row_id']}")
                except Exception as e:
                    print(f"Error processing row: {e}")

    def _process_simple_row(self, row: pd.Series, idx: int) -> Optional[Dict[str, Any]]:
        """Wrapper for simple translation processing."""
        return self.process_simple_translation(row, idx)

    def _process_complex_dataset(self, df: pd.DataFrame):
        """Process dataset for complex analysis tasks."""
        # Group by grouping columns
        grouping_cols = self.config.grouping_columns

        if not grouping_cols:
            # Process entire dataset as one group
            result = self.process_complex_analysis(df)
            if result:
                self.save_output(result, "all")
        else:
            # Process each group
            grouped = df.groupby(
                grouping_cols[0]
            )  # For now, just use first grouping column

            with ThreadPoolExecutor(max_workers=self.config.max_parallel) as executor:
                futures = []

                for group_key, group_df in grouped:
                    future = executor.submit(
                        self._process_complex_group, group_key, group_df
                    )
                    futures.append(future)

                # Process results
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        print(f"Error processing group: {e}")

    def _process_complex_group(self, group_key: Any, group_df: pd.DataFrame):
        """Wrapper for complex analysis processing."""
        result = self.process_complex_analysis(group_df)
        if result:
            self.save_output(result, f"chapter_{group_key}")

    def _process_hybrid_dataset(self, df: pd.DataFrame):
        """Process dataset using hybrid approach (passage-level then chapter-level)."""
        print("Processing using hybrid approach...")

        # Group by chapter
        chapter_groups = df.groupby("chapter")

        for chapter, chapter_df in chapter_groups:
            print(f"\nProcessing Chapter {chapter}...")

            # Stage 1: Process passages in parallel
            passage_results = self._process_passages_parallel(chapter_df, chapter)

            # Stage 1.5: Check for missing passages and retry them
            passage_results = self._check_and_retry_missing_passages(
                chapter, chapter_df, passage_results
            )

            # Stage 2: Generate chapter summary using all translations
            if passage_results:
                self._generate_chapter_summary(chapter, passage_results)

    def _process_passages_parallel(
        self, chapter_df: pd.DataFrame, chapter: str
    ) -> List[Dict[str, Any]]:
        """Process individual passages in parallel for translation and commentary."""
        results = []

        # Get max parallel workers from config
        processing_config = self.config.config.get("processing", {})
        stages = processing_config.get("stages", [])
        passage_stage = next((s for s in stages if s["name"] == "passage_analysis"), {})
        config_max_parallel = passage_stage.get("max_parallel", 5)

        # Use environment variable if set, otherwise use config value
        max_workers = min(MAX_PARALLEL, config_max_parallel)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []

            for idx, row in chapter_df.iterrows():
                # Submit passage for processing
                future = executor.submit(self._process_single_passage, row, chapter)
                futures.append((row["paragraph"], future))

            # Collect results
            for paragraph, future in futures:
                try:
                    print(f"  ⏳ Waiting for passage {paragraph} to complete...")
                    result = future.result(
                        timeout=120
                    )  # Set timeout for future.result()
                    if result:
                        results.append(result)
                        print(f"  ✓ Completed passage {paragraph}")
                    else:
                        print(
                            f"  ⚠️  Passage {paragraph} returned None result in parallel mode"
                        )
                except concurrent.futures.TimeoutError:
                    print(
                        f"  ⏱️  Timeout processing passage {paragraph} in parallel mode"
                    )
                except Exception as e:
                    print(f"  ✗ Error processing passage {paragraph}: {e}")

        return results

    def _check_and_retry_missing_passages(
        self,
        chapter: str,
        chapter_df: pd.DataFrame,
        passage_results: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Check for missing passages and retry them individually with backoff."""
        # Get expected passages from the dataset
        expected_passages = set(chapter_df["paragraph"].tolist())

        # Get completed passages from results
        completed_passages = set()
        for result in passage_results:
            if result and "paragraph" in result:
                completed_passages.add(int(result["paragraph"]))

        # Find missing passages
        missing_passages = expected_passages - completed_passages

        if missing_passages:
            print(f"\n⚠️  Missing passages detected: {sorted(missing_passages)}")
            print("Switching to individual processing mode for failed passages...")

            # Retry missing passages individually with exponential backoff
            for paragraph in sorted(missing_passages):
                print(f"  🔄 Retrying passage {paragraph} individually...")

                # Get the specific row for this passage
                passage_row = chapter_df[chapter_df["paragraph"] == paragraph]
                if not passage_row.empty:
                    success = False
                    max_retries = 3

                    for attempt in range(max_retries):
                        try:
                            if attempt > 0:
                                # Exponential backoff: wait 2^attempt seconds
                                wait_time = 2**attempt
                                print(
                                    f"    ⏳ Waiting {wait_time}s before retry attempt {attempt + 1}..."
                                )
                                time.sleep(wait_time)

                            result = self._process_single_passage_with_retry(
                                passage_row.iloc[0], chapter
                            )
                            if result:
                                passage_results.append(result)
                                print(
                                    f"  ✅ Successfully retried passage {paragraph} on attempt {attempt + 1}"
                                )
                                success = True
                                break
                            else:
                                print(
                                    f"  ⚠️  Attempt {attempt + 1} failed for passage {paragraph} - no result returned"
                                )
                        except Exception as e:
                            print(
                                f"  ❌ Error on attempt {attempt + 1} for passage {paragraph}: {e}"
                            )

                    if not success:
                        print(f"  💥 All retry attempts failed for passage {paragraph}")
                else:
                    print(f"  ❌ No data found for passage {paragraph}")
        else:
            print(f"✅ All passages completed successfully")

        return passage_results

    def _handle_special_case_passage(
        self, row: pd.Series, chapter: str
    ) -> Dict[str, Any]:
        """Handle special cases like grouped commentary for paragraphs 10-14."""
        # Check if special cases are enabled
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
                    f"  📋 Processing special case: paragraph {row['paragraph']} uses grouped commentary"
                )
                return self._process_grouped_commentary_passage(row, chapter, group)

        return None

    def _process_grouped_commentary_passage(
        self, row: pd.Series, chapter: str, group: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process a passage that uses grouped commentary from another paragraph."""
        hawaiian_text = row[self.config.source_column]
        paragraph = row["paragraph"]
        passage_id = row.get("passage_id", f"ch{chapter}_p{paragraph}")

        # Generate translation (but not commentary) for this passage
        prompts = self.config.config.get("prompts", {})
        passage_prompts = prompts.get("passage_analysis", {})

        system_prompt = passage_prompts.get("system", "")
        user_template = passage_prompts.get("user_template", "")

        # Create a modified prompt that only asks for translation
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

        # Call LLM
        response = self.call_llm(user_prompt, system_prompt)
        if not response:
            return None

        # Parse response
        parsed = self._parse_passage_response(response)

        # Get the grouped commentary from the reference data
        grouped_commentary_text = self._get_grouped_commentary(group)

        # Prepare output
        output = {
            "chapter": str(chapter),
            "paragraph": int(paragraph),
            "passage_id": str(passage_id),
            "hawaiian_text": str(hawaiian_text),
            f"{OUTPUT_DIR}_translation": parsed.get("translation", ""),
            f"{OUTPUT_DIR}_commentary": grouped_commentary_text,
            "raw_response": response,
            "special_case": "grouped_commentary",
        }

        # Add reference data if available
        if "english_translation" in row:
            output["reference_translation"] = str(row["english_translation"])
        if "commentary" in row and pd.notna(row["commentary"]):
            output["reference_commentary"] = str(row["commentary"])

        # Save passage-level output (this was missing!)
        self.save_output(output, f"passage_{chapter}_{paragraph}")

        return output

    def _get_grouped_commentary(self, group: Dict[str, Any]) -> str:
        """Extract grouped commentary from the dataset."""
        try:
            # Load the full dataset to get the grouped commentary
            dataset_path = self.config.config.get("dataset", {}).get("path", "")
            if not dataset_path:
                return f"[Grouped commentary for paragraphs {group.get('paragraphs', [])} - see paragraph {group.get('commentary_location', '')}]"

            df = pd.read_csv(dataset_path)

            # Extract paragraph number from commentary_location (e.g., "paragraph_8" -> 8)
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
                            # Extract everything after "**Paragraphs 10—14**"
                            parts = commentary_text.split("**Paragraphs 10—14**")
                            if len(parts) > 1:
                                return f"**Paragraphs 10—14**{parts[1]}"
                        return commentary_text

            return f"[Grouped commentary for paragraphs {group.get('paragraphs', [])} - see paragraph {group.get('commentary_location', '')}]"

        except Exception as e:
            print(f"    ⚠️  Error loading grouped commentary: {e}")
            return f"[Grouped commentary for paragraphs {group.get('paragraphs', [])} - see paragraph {group.get('commentary_location', '')}]"

    def _process_single_passage_with_retry(
        self, row: pd.Series, chapter: str
    ) -> Dict[str, Any]:
        """Process a single passage with enhanced error handling for individual retries."""
        try:
            return self._process_single_passage(row, chapter)
        except requests.exceptions.Timeout:
            print(f"    ⏱️  Timeout occurred - this is expected for individual retry")
            return None
        except requests.exceptions.ConnectionError as e:
            print(f"    🔌 Connection error - retrying: {e}")
            return None
        except Exception as e:
            print(f"    ❌ Unexpected error: {e}")
            return None

    def _process_single_passage(self, row: pd.Series, chapter: str) -> Dict[str, Any]:
        """Process a single passage for translation and commentary."""
        hawaiian_text = row[self.config.source_column]
        paragraph = row["paragraph"]
        passage_id = row.get("passage_id", f"ch{chapter}_p{paragraph}")

        print(f"    📝 Starting processing for passage {paragraph}")

        # Check if this passage is in a special group
        special_case_result = self._handle_special_case_passage(row, chapter)
        if special_case_result:
            print(f"    ✅ Special case handling completed for passage {paragraph}")
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

        # Call LLM with full prompt
        print(f"    🔄 Calling LLM for passage {paragraph}")
        response = self.call_llm(user_prompt, system_prompt)
        if not response:
            print(f"    ❌ No response from LLM for passage {paragraph}")
            return None
        print(f"    ✅ LLM response received for passage {paragraph}")

        # Parse response
        parsed = self._parse_passage_response(response)

        # Check if parsing was successful
        if not parsed.get("translation") and not parsed.get("commentary"):
            print(
                f"    ❌ Failed to parse translation/commentary from response for passage {paragraph}"
            )
            # Always show first 200 chars of response for parsing failures to help diagnose issues
            print(f"    Raw response preview: {response[:200]}...")
            return None

        # Prepare output
        output = {
            "chapter": str(chapter),
            "paragraph": int(paragraph),
            "passage_id": str(passage_id),
            "hawaiian_text": str(hawaiian_text),
            f"{OUTPUT_DIR}_translation": parsed.get("translation", ""),
            f"{OUTPUT_DIR}_commentary": parsed.get("commentary", ""),
            "raw_response": response,
        }

        # Add reference data if available
        if "english_translation" in row:
            output["reference_translation"] = str(row["english_translation"])
        if "commentary" in row and pd.notna(row["commentary"]):
            output["reference_commentary"] = str(row["commentary"])

        # Save passage-level output
        self.save_output(output, f"passage_{chapter}_{paragraph}")

        return output

    def _generate_chapter_summary(
        self, chapter: str, passage_results: List[Dict[str, Any]]
    ):
        """Generate chapter summary using all passage translations."""
        print(f"\nGenerating summary for Chapter {chapter}...")

        # Collect all translations
        all_translations = []
        for result in sorted(passage_results, key=lambda x: int(x["paragraph"])):
            translation = result.get(f"{OUTPUT_DIR}_translation", "")
            if translation:
                all_translations.append(
                    f"Paragraph {result['paragraph']}:\n{translation}"
                )

        if not all_translations:
            print("  ✗ No translations found for summary generation")
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

        # Call LLM for summary
        response = self.call_llm(user_prompt, system_prompt)
        if not response:
            print("  ✗ Failed to generate summary")
            return

        # Parse summary
        parsed = self._parse_summary_response(response)

        # Create chapter manifest
        manifest = {
            "chapter": int(chapter),
            "passage_count": len(passage_results),
            "passage_references": [
                f"hybrid_complex_analysis_passage_{chapter}_{r['paragraph']}.json"
                for r in sorted(passage_results, key=lambda x: int(x["paragraph"]))
            ],
            f"{OUTPUT_DIR}_summary": parsed.get("summary", ""),
            "raw_summary_response": response,
        }

        # Add reference summary if available
        chapter_df = pd.DataFrame(passage_results)
        if "reference_summary" in chapter_df.columns:
            summary_rows = chapter_df[chapter_df["reference_summary"].notna()]
            if not summary_rows.empty:
                manifest["reference_summary"] = summary_rows.iloc[0][
                    "reference_summary"
                ]

        # Save manifest
        self.save_output(manifest, f"chapter_{chapter}_manifest")
        print(f"  ✓ Summary generated for Chapter {chapter}")

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
        # Try to find commentary with both opening and closing tags first
        commentary_match = re.search(
            r"<commentary>(.*?)</commentary>", response, re.DOTALL | re.IGNORECASE
        )
        if commentary_match:
            parsed["commentary"] = commentary_match.group(1).strip()
        else:
            # If no closing tag, extract everything from opening tag to end of response
            commentary_match = re.search(
                r"<commentary>(.*)", response, re.DOTALL | re.IGNORECASE
            )
            if commentary_match:
                parsed["commentary"] = commentary_match.group(1).strip()

        # Debug parsing results
        if not parsed.get("translation") and not parsed.get("commentary"):
            print(
                f"    🔍 Parsing debug: translation={'✓' if parsed.get('translation') else '✗'}, commentary={'✓' if parsed.get('commentary') else '✗'}"
            )
            # Check if there are any XML-like tags at all
            if (
                "<translation>" in response.lower()
                or "<commentary>" in response.lower()
            ):
                print(f"    🔍 Found XML tags in response but failed to parse content")
            else:
                print(f"    🔍 No XML tags found in response")

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


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run translation/analysis with specified task configuration"
    )
    parser.add_argument(
        "--task",
        type=str,
        required=True,
        help="Task configuration name (e.g., simple_translation, complex_analysis)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug output (show LLM response content including translations and commentary)",
    )

    args = parser.parse_args()

    # Load task configuration
    config_path = f"task_configs/{args.task}.json"

    try:
        task_config = TaskConfig(config_path)
        print(f"Loaded task configuration: {task_config.task_name}")
        print(f"Task type: {task_config.task_type}")
        print(f"Description: {task_config.config.get('description', 'N/A')}")
    except Exception as e:
        print(f"Error loading task configuration: {e}")
        return

    # Process dataset
    processor = TaskProcessor(task_config, debug=args.debug)
    processor.process_dataset()


if __name__ == "__main__":
    main()
