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
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "1024"))
SELF_REASONING_PARSER = os.getenv("SELF_REASONING_PARSER", "").lower() in [
    "true",
    "1",
    "yes",
]
USE_STREAMING = os.getenv("USE_STREAMING", "false").lower() in [
    "true",
    "1",
    "yes",
]


class TaskProcessor:
    """Process translations/analysis based on task configuration."""

    def __init__(self, task_config: TaskConfig):
        self.config = task_config
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

    def call_llm(self, prompt: str) -> Optional[str]:
        """Call the LLM API with the given prompt."""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}",
        }

        messages = [
            {"role": "system", "content": self.config.system_prompt},
            {"role": "user", "content": prompt},
        ]

        payload = {
            "model": MODEL_NAME,
            "messages": messages,
            "temperature": 0,
            "max_tokens": MAX_TOKENS,
            "stream": USE_STREAMING,
        }

        url = BASE_URL.rstrip("/") + "/chat/completions"
        
        # Set longer timeout for complex analysis tasks
        timeout_seconds = 600  # 10 minutes
        
        try:
            print(f"Making API request with {timeout_seconds}s timeout...")
            response = requests.post(
                url, 
                headers=headers, 
                json=payload,
                timeout=timeout_seconds
            )
            
            if response.status_code == 200:
                if USE_STREAMING:
                    # Handle streaming response
                    llm_content = ""
                    print("Receiving streaming response...")
                    for line in response.iter_lines():
                        if line:
                            line_text = line.decode('utf-8')
                            if line_text.startswith('data: '):
                                data_text = line_text[6:]  # Remove 'data: ' prefix
                                if data_text.strip() == '[DONE]':
                                    break
                                try:
                                    chunk_data = json.loads(data_text)
                                    if 'choices' in chunk_data and len(chunk_data['choices']) > 0:
                                        delta = chunk_data['choices'][0].get('delta', {})
                                        if 'content' in delta:
                                            content_chunk = delta['content']
                                            llm_content += content_chunk
                                            print(content_chunk, end='', flush=True)
                                except json.JSONDecodeError:
                                    continue
                    print()  # New line after streaming
                else:
                    # Handle non-streaming response
                    llm_content = response.json()["choices"][0]["message"]["content"]
                
                # Apply self-reasoning parser if enabled
                if SELF_REASONING_PARSER:
                    print("Stripping <think> content...")
                    llm_content = re.sub(
                        r"<think>.*?</think>", "", llm_content, flags=re.DOTALL
                    )
                
                return llm_content
            else:
                print(f"API Error: {response.status_code}")
                print(f"Response: {response.text[:1000]}...")  # Truncate long error messages
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
    processor = TaskProcessor(task_config)
    processor.process_dataset()


if __name__ == "__main__":
    main()
