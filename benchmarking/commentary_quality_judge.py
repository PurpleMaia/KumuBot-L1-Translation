#!/usr/bin/env python3
"""
Commentary Quality Evaluator using LLM Judge

This module uses an LLM as a judge to evaluate the quality of cultural/historical
commentary generated for Hawaiian passage analysis.
"""

import os
import pandas as pd
import numpy as np
from openai import OpenAI
from dotenv import load_dotenv
import time
import json
import argparse
from tqdm import tqdm
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import re

# Load environment variables
load_dotenv()

# Get API configuration
api_key = os.getenv("OPENAI_API_KEY_KOA")
api_base_url = os.getenv("OPENAI_API_BASE_URL")

if not api_key or not api_base_url:
    raise ValueError("Please set OPENAI_API_KEY_KOA and OPENAI_API_BASE_URL")

client = OpenAI(api_key=api_key, base_url=api_base_url)
judge_model = os.getenv("OPENAI_MODEL_NAME", "gpt-4o")


class CommentaryQualityJudge:
    """LLM-based judge for evaluating commentary quality."""

    def __init__(self):
        self.evaluation_criteria = {
            "cultural_accuracy": {
                "description": "How accurately does the commentary represent Hawaiian cultural concepts and practices?",
                "weight": 0.3,
            },
            "historical_context": {
                "description": "How well does the commentary provide relevant historical context?",
                "weight": 0.25,
            },
            "linguistic_analysis": {
                "description": "How thorough and accurate is the linguistic analysis of Hawaiian language features?",
                "weight": 0.25,
            },
            "academic_rigor": {
                "description": "How well does the commentary meet academic standards for scholarly analysis?",
                "weight": 0.2,
            },
        }

    def create_evaluation_prompt(
        self,
        hawaiian_text: str,
        model_commentary: str,
        reference_commentary: str,
        criterion: str,
    ) -> str:
        """Create evaluation prompt for a specific criterion."""

        criterion_info = self.evaluation_criteria[criterion]

        base_prompt = f"""You are an expert evaluator of Hawaiian cultural and linguistic analysis. Your task is to evaluate the quality of commentary on Hawaiian passages.

EVALUATION CRITERION: {criterion.replace("_", " ").title()}
CRITERION DESCRIPTION: {criterion_info["description"]}

HAWAIIAN PASSAGE:
{hawaiian_text}

REFERENCE COMMENTARY (Expert Analysis):
{reference_commentary}

MODEL COMMENTARY (To Evaluate):
{model_commentary}

Please evaluate the MODEL COMMENTARY compared to the REFERENCE COMMENTARY on the criterion of {criterion.replace("_", " ")}.

EVALUATION SCALE:
5 - Excellent: Exceeds reference quality, provides additional valuable insights
4 - Good: Meets reference quality with minor gaps or differences
3 - Satisfactory: Adequate analysis but missing some important elements
2 - Poor: Significant gaps or inaccuracies compared to reference
1 - Very Poor: Major errors, misunderstandings, or lack of relevant content

EVALUATION INSTRUCTIONS:
1. Compare the model commentary directly to the reference commentary
2. Consider accuracy, depth, relevance, and completeness
3. Focus specifically on {criterion.replace("_", " ")} aspects
4. Provide a score from 1-5 and detailed justification

Please respond in the following JSON format:
{{
    "score": <integer 1-5>,
    "justification": "<detailed explanation of the score>",
    "strengths": ["<strength 1>", "<strength 2>", ...],
    "weaknesses": ["<weakness 1>", "<weakness 2>", ...],
    "suggestions": ["<improvement suggestion 1>", "<improvement suggestion 2>", ...]
}}"""

        return base_prompt

    def evaluate_commentary_criterion(
        self,
        hawaiian_text: str,
        model_commentary: str,
        reference_commentary: str,
        criterion: str,
    ) -> Optional[Dict]:
        """Evaluate commentary on a specific criterion using LLM judge."""

        if pd.isna(model_commentary) or str(model_commentary).strip() == "":
            return {
                "score": 1,
                "justification": "No commentary provided",
                "strengths": [],
                "weaknesses": ["Missing commentary"],
                "suggestions": ["Provide commentary for this passage"],
            }

        if pd.isna(reference_commentary) or str(reference_commentary).strip() == "":
            return {
                "score": 3,  # Default score when no reference
                "justification": "No reference commentary available for comparison",
                "strengths": ["Commentary provided"],
                "weaknesses": ["Cannot compare to reference"],
                "suggestions": ["Include reference commentary for better evaluation"],
            }

        prompt = self.create_evaluation_prompt(
            str(hawaiian_text),
            str(model_commentary),
            str(reference_commentary),
            criterion,
        )

        max_retries = 3
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                response = client.chat.completions.create(
                    model=judge_model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert evaluator of Hawaiian cultural and linguistic analysis. Provide detailed, objective evaluations in the requested JSON format.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.1,  # Low temperature for consistent evaluation
                    max_tokens=1000,
                )

                response_text = response.choices[0].message.content

                # Try to parse JSON response
                try:
                    # Extract JSON from response if it's wrapped in markdown or text
                    json_match = re.search(
                        r"```json\s*(.*?)\s*```", response_text, re.DOTALL
                    )
                    if json_match:
                        json_text = json_match.group(1)
                    else:
                        # Look for JSON object
                        json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
                        if json_match:
                            json_text = json_match.group(0)
                        else:
                            json_text = response_text

                    result = json.loads(json_text)

                    # Validate result structure
                    required_keys = [
                        "score",
                        "justification",
                        "strengths",
                        "weaknesses",
                        "suggestions",
                    ]
                    if all(key in result for key in required_keys):
                        # Ensure score is in valid range
                        result["score"] = max(1, min(5, int(result["score"])))
                        return result
                    else:
                        print(f"Invalid JSON structure in response: {response_text}")

                except json.JSONDecodeError as e:
                    print(f"JSON parse error: {e}")
                    print(f"Response text: {response_text}")

                # If JSON parsing fails, try to extract score manually
                score_match = re.search(
                    r'score["\']?\s*:\s*(\d+)', response_text, re.IGNORECASE
                )
                if score_match:
                    score = int(score_match.group(1))
                    return {
                        "score": max(1, min(5, score)),
                        "justification": response_text,
                        "strengths": [],
                        "weaknesses": [],
                        "suggestions": [],
                    }

            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"Error in LLM evaluation (attempt {attempt + 1}): {e}")
                    time.sleep(retry_delay)
                else:
                    print(f"Failed to evaluate after {max_retries} attempts: {e}")
                    return None

        return None

    def evaluate_full_commentary(
        self, hawaiian_text: str, model_commentary: str, reference_commentary: str
    ) -> Dict[str, any]:
        """Evaluate commentary on all criteria."""

        results = {"criteria_scores": {}, "overall_score": 0.0, "weighted_score": 0.0}

        total_weight = 0.0
        weighted_sum = 0.0

        for criterion, criterion_info in self.evaluation_criteria.items():
            print(f"  Evaluating {criterion.replace('_', ' ')}...")

            evaluation = self.evaluate_commentary_criterion(
                hawaiian_text, model_commentary, reference_commentary, criterion
            )

            if evaluation:
                results["criteria_scores"][criterion] = evaluation
                score = evaluation["score"]
                weight = criterion_info["weight"]

                weighted_sum += score * weight
                total_weight += weight
            else:
                # Use default score if evaluation fails
                results["criteria_scores"][criterion] = {
                    "score": 1,
                    "justification": "Evaluation failed",
                    "strengths": [],
                    "weaknesses": ["Could not evaluate"],
                    "suggestions": [],
                }
                weighted_sum += 1 * criterion_info["weight"]
                total_weight += criterion_info["weight"]

        # Calculate overall scores
        if total_weight > 0:
            results["weighted_score"] = weighted_sum / total_weight
            scores = [
                results["criteria_scores"][c]["score"]
                for c in self.evaluation_criteria.keys()
            ]
            results["overall_score"] = np.mean(scores)

        return results

    def evaluate_model_commentaries(
        self, model_df: pd.DataFrame, ref_df: pd.DataFrame, output_dir: str
    ) -> Dict[str, any]:
        """Evaluate all commentaries for a model."""

        print(f"\n=== Evaluating Commentary Quality for {output_dir} ===")

        results = {
            "model": output_dir,
            "total_passages": len(model_df),
            "passage_evaluations": [],
            "summary_stats": {},
        }

        commentary_col = f"{output_dir}_commentary"

        if commentary_col not in model_df.columns:
            print(f"No commentary column found: {commentary_col}")
            return results

        # Evaluate each passage
        for i, (model_row, ref_row) in enumerate(
            tqdm(
                zip(model_df.iterrows(), ref_df.iterrows()),
                desc="Evaluating commentaries",
            )
        ):
            model_row = model_row[1]
            ref_row = ref_row[1]

            hawaiian_text = ref_row.get("hawaiian_text", "")
            model_commentary = model_row.get(commentary_col, "")
            reference_commentary = ref_row.get("commentary", "")

            print(f"\nEvaluating passage {i + 1}/{len(model_df)}...")

            passage_evaluation = self.evaluate_full_commentary(
                hawaiian_text, model_commentary, reference_commentary
            )

            passage_evaluation["passage_id"] = i
            passage_evaluation["hawaiian_text"] = (
                str(hawaiian_text)[:100] + "..."
            )  # Truncate for storage

            results["passage_evaluations"].append(passage_evaluation)

        # Calculate summary statistics
        self._calculate_summary_stats(results)

        return results

    def _calculate_summary_stats(self, results: Dict[str, any]):
        """Calculate summary statistics for all evaluations."""

        if not results["passage_evaluations"]:
            return

        # Initialize stats structure
        results["summary_stats"] = {
            "overall_scores": [],
            "weighted_scores": [],
            "criteria_stats": {},
        }

        # Collect scores
        for evaluation in results["passage_evaluations"]:
            results["summary_stats"]["overall_scores"].append(
                evaluation["overall_score"]
            )
            results["summary_stats"]["weighted_scores"].append(
                evaluation["weighted_score"]
            )

        # Calculate stats for each criterion
        for criterion in self.evaluation_criteria.keys():
            criterion_scores = []
            for evaluation in results["passage_evaluations"]:
                if criterion in evaluation["criteria_scores"]:
                    criterion_scores.append(
                        evaluation["criteria_scores"][criterion]["score"]
                    )

            if criterion_scores:
                results["summary_stats"]["criteria_stats"][criterion] = {
                    "mean": float(np.mean(criterion_scores)),
                    "std": float(np.std(criterion_scores)),
                    "min": float(np.min(criterion_scores)),
                    "max": float(np.max(criterion_scores)),
                    "count": len(criterion_scores),
                }

        # Overall summary stats
        for score_type in ["overall_scores", "weighted_scores"]:
            scores = results["summary_stats"][score_type]
            if scores:
                results["summary_stats"][f"{score_type}_stats"] = {
                    "mean": float(np.mean(scores)),
                    "std": float(np.std(scores)),
                    "min": float(np.min(scores)),
                    "max": float(np.max(scores)),
                    "count": len(scores),
                }

        # Print summary
        print(f"\nCommentary Quality Summary:")
        print(
            f"  Overall Score: {results['summary_stats']['overall_scores_stats']['mean']:.2f} ± {results['summary_stats']['overall_scores_stats']['std']:.2f}"
        )
        print(
            f"  Weighted Score: {results['summary_stats']['weighted_scores_stats']['mean']:.2f} ± {results['summary_stats']['weighted_scores_stats']['std']:.2f}"
        )

        for criterion, stats in results["summary_stats"]["criteria_stats"].items():
            print(
                f"  {criterion.replace('_', ' ').title()}: {stats['mean']:.2f} ± {stats['std']:.2f}"
            )

    def save_results(self, results: Dict[str, any], output_dir: str):
        """Save commentary evaluation results."""
        os.makedirs("benchmarking/complex_analysis", exist_ok=True)

        # Save detailed results
        json_path = (
            f"benchmarking/complex_analysis/{output_dir}_commentary_quality.json"
        )
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)

        # Create summary CSV
        summary_data = []
        for criterion, stats in (
            results["summary_stats"].get("criteria_stats", {}).items()
        ):
            summary_data.append(
                {
                    "model": output_dir,
                    "criterion": criterion,
                    "mean_score": stats["mean"],
                    "std_score": stats["std"],
                    "min_score": stats["min"],
                    "max_score": stats["max"],
                    "weight": self.evaluation_criteria[criterion]["weight"],
                }
            )

        if summary_data:
            summary_df = pd.DataFrame(summary_data)
            summary_csv_path = f"benchmarking/complex_analysis/{output_dir}_commentary_quality_summary.csv"
            summary_df.to_csv(summary_csv_path, index=False)

        # Create detailed passage-level CSV
        passage_data = []
        for eval_result in results["passage_evaluations"]:
            row = {
                "model": output_dir,
                "passage_id": eval_result["passage_id"],
                "overall_score": eval_result["overall_score"],
                "weighted_score": eval_result["weighted_score"],
            }

            for criterion in self.evaluation_criteria.keys():
                if criterion in eval_result["criteria_scores"]:
                    row[f"{criterion}_score"] = eval_result["criteria_scores"][
                        criterion
                    ]["score"]
                else:
                    row[f"{criterion}_score"] = np.nan

            passage_data.append(row)

        if passage_data:
            passage_df = pd.DataFrame(passage_data)
            passage_csv_path = f"benchmarking/complex_analysis/{output_dir}_commentary_quality_detailed.csv"
            passage_df.to_csv(passage_csv_path, index=False)

        print(f"\nCommentary quality results saved to:")
        print(f"  - {json_path}")
        if summary_data:
            print(f"  - {summary_csv_path}")
        if passage_data:
            print(f"  - {passage_csv_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate commentary quality using LLM judge"
    )
    parser.add_argument("--model", type=str, help="Specific model to evaluate")
    parser.add_argument(
        "--judge-model",
        type=str,
        default=judge_model,
        help="Model to use as judge (default: from OPENAI_MODEL_NAME)",
    )

    args = parser.parse_args()

    # Update judge model if specified
    global judge_model
    judge_model = args.judge_model

    # Discover available models
    data_dir = Path("data/complex_analysis")
    available_models = []

    if data_dir.exists():
        for file in data_dir.glob("*_extracted.csv"):
            model_name = file.stem.replace("_extracted", "")
            # Check if model has commentary
            df = pd.read_csv(file)
            commentary_col = f"{model_name}_commentary"
            if commentary_col in df.columns:
                available_models.append(model_name)

    if not available_models:
        print("No complex analysis outputs with commentary found.")
        return

    print(f"Using {judge_model} as judge model")
    print(f"Available models with commentary: {available_models}")

    # Initialize judge
    judge = CommentaryQualityJudge()

    # Evaluate models
    if args.model:
        if args.model not in available_models:
            print(f"Model '{args.model}' not found or has no commentary.")
            return
        models_to_evaluate = [args.model]
    else:
        models_to_evaluate = available_models

    # Load reference data
    ref_path = "data/complex_analysis/namakaokapaoo_dataset.csv"
    if not os.path.exists(ref_path):
        print(f"Reference data not found: {ref_path}")
        return

    ref_df = pd.read_csv(ref_path)

    # Evaluate each model
    for model in models_to_evaluate:
        try:
            model_path = f"data/complex_analysis/{model}_extracted.csv"
            model_df = pd.read_csv(model_path)

            results = judge.evaluate_model_commentaries(model_df, ref_df, model)
            judge.save_results(results, model)

        except Exception as e:
            print(f"Error evaluating model {model}: {e}")
            continue

    print("\n=== Commentary Quality Evaluation Complete ===")


if __name__ == "__main__":
    main()
