"""
Task configuration loader and manager for different translation/analysis tasks.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional


class TaskConfig:
    """Load and manage task configurations."""

    def __init__(self, config_path: str):
        """Initialize with a configuration file path."""
        self.config_path = Path(config_path)
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file."""
        with open(self.config_path, "r") as f:
            return json.load(f)

    @property
    def task_name(self) -> str:
        return self.config["task_name"]

    @property
    def task_type(self) -> str:
        return self.config["task_type"]

    @property
    def dataset_path(self) -> str:
        return self.config["dataset"]["path"]

    @property
    def source_column(self) -> str:
        return self.config["dataset"]["source_column"]

    @property
    def reference_columns(self) -> Dict[str, str]:
        """Get reference columns - handles both simple and complex tasks."""
        if "reference_column" in self.config["dataset"]:
            # Simple task with single reference
            return {"translation": self.config["dataset"]["reference_column"]}
        else:
            # Complex task with multiple references
            return self.config["dataset"]["reference_columns"]

    @property
    def id_column(self) -> str:
        return self.config["dataset"].get("id_column", "row_id")

    @property
    def grouping_columns(self) -> Optional[List[str]]:
        """Get grouping columns for complex tasks."""
        return self.config["dataset"].get("grouping_columns")

    @property
    def output_format(self) -> str:
        return self.config["output"]["format"]

    @property
    def output_fields(self) -> List[str]:
        return self.config["output"]["fields"]

    @property
    def parsing_tags(self) -> Dict[str, str]:
        """Get parsing tags for extracting different components."""
        return self.config["output"]["parsing"]

    @property
    def system_prompt(self) -> str:
        return self.config["prompt"]["system"].strip()

    @property
    def user_prompt_template(self) -> str:
        return self.config["prompt"]["user_template"].strip()

    @property
    def passage_format(self) -> Optional[str]:
        """Get passage format template for complex tasks."""
        return self.config["prompt"].get("passage_format", "").strip()

    @property
    def batch_size(self) -> str:
        """Get batch size - can be numeric or 'chapter' for grouping."""
        return self.config["processing"]["batch_size"]

    @property
    def max_parallel(self) -> int:
        return self.config["processing"].get("max_parallel", 3)

    @property
    def evaluation_metrics(self) -> List[str]:
        return self.config["evaluation"]["metrics"]

    def format_user_prompt(self, **kwargs) -> str:
        """Format the user prompt with provided data."""
        return self.user_prompt_template.format(**kwargs)

    def format_passages(self, passages: List[Dict[str, Any]]) -> str:
        """Format multiple passages for complex tasks."""
        if not self.passage_format:
            return ""

        formatted_passages = []
        for passage in passages:
            formatted = self.passage_format.format(**passage)
            formatted_passages.append(formatted)

        return "\n\n".join(formatted_passages)

    def parse_output(self, text: str) -> Dict[str, str]:
        """Parse model output based on configured tags."""
        result = {}

        for field, tag in self.parsing_tags.items():
            # Extract content between tags
            start_tag = f"<{tag}>"
            end_tag = f"</{tag}>"

            start_idx = text.find(start_tag)
            if start_idx != -1:
                start_idx += len(start_tag)
                end_idx = text.find(end_tag, start_idx)
                if end_idx != -1:
                    result[field] = text[start_idx:end_idx].strip()
                else:
                    result[field] = ""
            else:
                result[field] = ""

        return result


def get_available_tasks() -> List[str]:
    """Get list of available task configurations."""
    config_dir = Path("task_configs")
    if not config_dir.exists():
        return []

    tasks = []
    for config_file in config_dir.glob("*.json"):
        tasks.append(config_file.stem)

    return sorted(tasks)
