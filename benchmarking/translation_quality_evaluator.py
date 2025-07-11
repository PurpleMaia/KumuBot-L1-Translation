#!/usr/bin/env python3
"""
Translation Quality Evaluator for Complex Analysis

This module specifically evaluates the quality of Hawaiian→English translations
within complex passages, accounting for context and cultural nuances.
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
api_base_url = os.getenv("OPENAI_API_EMBEDDING_BASE_URL")

if not api_key or not api_base_url:
    raise ValueError("Please set OPENAI_API_KEY_KOA and OPENAI_API_EMBEDDING_BASE_URL")

client = OpenAI(api_key=api_key, base_url=api_base_url)
embedding_model = "nomic-embed-text"


class TranslationQualityEvaluator:
    """Evaluates translation quality for complex Hawaiian passage analysis."""

    def __init__(self):
        self.embedding_cache = {}
        self.cultural_terms = self._load_cultural_terms()

    def _load_cultural_terms(self) -> List[str]:
        """Load Hawaiian cultural terms that require careful translation."""
        # Common Hawaiian cultural terms that should be preserved or carefully translated
        return [
            "aloha",
            "mahalo",
            "pono",
            "mana",
            "kapu",
            "ali'i",
            "kahuna",
            "hale",
            "ohana",
            "keiki",
            "kupuna",
            "malama",
            "kokua",
            "hula",
            "lei",
            "luau",
            "poi",
            "taro",
            "kalo",
            "imu",
            "heiau",
            "konohiki",
            "mo'i",
            "kapa",
            "malo",
            "pa'u",
        ]

    def get_embedding(self, text: str) -> Optional[List[float]]:
        """Get embedding for text with caching and rate limiting."""
        if not text or pd.isna(text) or text.strip() == "":
            return None

        # Clean text for consistent embeddings
        clean_text = self._clean_text_for_embedding(text)

        if clean_text in self.embedding_cache:
            return self.embedding_cache[clean_text]

        max_retries = 5
        retry_delay = 1

        for attempt in range(max_retries):
            try:
                response = client.embeddings.create(
                    model=embedding_model,
                    input=clean_text,
                    dimensions=768,
                )
                embedding = response.data[0].embedding
                self.embedding_cache[clean_text] = embedding
                return embedding
            except Exception as e:
                if "rate limit" in str(e).lower() and attempt < max_retries - 1:
                    sleep_time = retry_delay * (2**attempt)
                    print(f"Rate limit exceeded. Retrying in {sleep_time} seconds...")
                    time.sleep(sleep_time)
                else:
                    print(f"Error getting embedding: {str(e)}")
                    return None
        return None

    def _clean_text_for_embedding(self, text: str) -> str:
        """Clean text for consistent embedding generation."""
        if pd.isna(text):
            return ""

        # Remove extra whitespace and normalize
        text = re.sub(r"\s+", " ", str(text).strip())

        # Remove common markup that might interfere
        text = re.sub(r"<[^>]+>", "", text)  # Remove HTML/XML tags
        text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)  # Remove markdown bold
        text = re.sub(r"\*([^*]+)\*", r"\1", text)  # Remove markdown italic

        return text

    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if vec1 is None or vec2 is None:
            return np.nan

        dot_product = np.dot(vec1, vec2)
        norm_a = np.linalg.norm(vec1)
        norm_b = np.linalg.norm(vec2)

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return float(dot_product / (norm_a * norm_b))

    def evaluate_cultural_preservation(
        self, hawaiian_text: str, translation: str
    ) -> float:
        """Evaluate how well cultural terms are preserved in translation."""
        if pd.isna(hawaiian_text) or pd.isna(translation):
            return np.nan

        hawaiian_lower = str(hawaiian_text).lower()
        translation_lower = str(translation).lower()

        # Find cultural terms in Hawaiian text
        found_cultural_terms = []
        for term in self.cultural_terms:
            if term.lower() in hawaiian_lower:
                found_cultural_terms.append(term)

        if not found_cultural_terms:
            return 1.0  # No cultural terms to evaluate

        # Check preservation in translation
        preserved_count = 0
        for term in found_cultural_terms:
            # Check if term is preserved as-is or properly explained
            if term.lower() in translation_lower or self._has_cultural_explanation(
                term, translation_lower
            ):
                preserved_count += 1

        return preserved_count / len(found_cultural_terms)

    def _has_cultural_explanation(self, term: str, translation: str) -> bool:
        """Check if a cultural term has proper explanation in translation."""
        # Simple heuristic: look for explanatory phrases near term mentions
        explanatory_patterns = [
            f"{term}.*?\\b(chief|leader|ruler|noble)",  # ali'i
            f"{term}.*?\\b(house|home|building)",  # hale
            f"{term}.*?\\b(family|relatives)",  # ohana
            f"{term}.*?\\b(child|children)",  # keiki
            f"{term}.*?\\b(elder|grandparent)",  # kupuna
            f"{term}.*?\\b(sacred|forbidden|taboo)",  # kapu
            f"{term}.*?\\b(priest|spiritual|healer)",  # kahuna
        ]

        for pattern in explanatory_patterns:
            if re.search(pattern, translation, re.IGNORECASE):
                return True

        return False

    def evaluate_fluency(self, translation: str) -> float:
        """Evaluate fluency of English translation."""
        if pd.isna(translation) or str(translation).strip() == "":
            return np.nan

        text = str(translation).strip()

        # Basic fluency indicators
        fluency_score = 1.0

        # Penalize for obvious translation artifacts
        artifacts = [
            r"\b(the the|a a|an an)\b",  # Repeated articles
            r"\b\w+\s+\1\b",  # Repeated words
            r"[^\w\s\.,!?;:\'\"()-]",  # Unusual characters
            r"\s{2,}",  # Multiple spaces
        ]

        for pattern in artifacts:
            matches = len(re.findall(pattern, text, re.IGNORECASE))
            if matches > 0:
                fluency_score -= min(0.2, matches * 0.05)

        # Bonus for proper sentence structure
        sentences = re.split(r"[.!?]+", text)
        well_formed_sentences = 0

        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 5 and sentence[0].isupper():
                well_formed_sentences += 1

        if len(sentences) > 1:
            structure_bonus = well_formed_sentences / len(sentences) * 0.1
            fluency_score += structure_bonus

        return max(0.0, min(1.0, fluency_score))

    def evaluate_contextual_accuracy(
        self,
        hawaiian_passage: str,
        translation: str,
        reference: str,
        chapter_context: str = "",
    ) -> float:
        """Evaluate how well translation captures contextual meaning."""
        if any(pd.isna(x) for x in [hawaiian_passage, translation, reference]):
            return np.nan

        # Get embeddings for all texts
        hawaiian_embedding = self.get_embedding(str(hawaiian_passage))
        translation_embedding = self.get_embedding(str(translation))
        reference_embedding = self.get_embedding(str(reference))

        if any(
            x is None
            for x in [hawaiian_embedding, translation_embedding, reference_embedding]
        ):
            return np.nan

        # Contextual accuracy is how well the translation preserves
        # the semantic relationship between source and reference

        # Similarity between translation and reference
        trans_ref_similarity = self.cosine_similarity(
            translation_embedding, reference_embedding
        )

        # If we have chapter context, factor that in
        if chapter_context and str(chapter_context).strip():
            context_embedding = self.get_embedding(str(chapter_context))
            if context_embedding is not None:
                # How well does translation align with chapter context
                trans_context_similarity = self.cosine_similarity(
                    translation_embedding, context_embedding
                )
                # Weight: 70% reference similarity + 30% context alignment
                contextual_score = (
                    0.7 * trans_ref_similarity + 0.3 * trans_context_similarity
                )
            else:
                contextual_score = trans_ref_similarity
        else:
            contextual_score = trans_ref_similarity

        return max(0.0, min(1.0, contextual_score))

    def evaluate_passage_translations(
        self, model_df: pd.DataFrame, ref_df: pd.DataFrame, output_dir: str
    ) -> Dict[str, any]:
        """Evaluate translation quality for all passages."""
        print(f"\n=== Evaluating Translation Quality for {output_dir} ===")

        results = {
            "model": output_dir,
            "total_passages": len(model_df),
            "translation_metrics": {
                "semantic_similarity": [],
                "cultural_preservation": [],
                "fluency": [],
                "contextual_accuracy": [],
            },
            "summary_stats": {},
        }

        # Get chapter context for contextual evaluation
        chapter_context = ""
        if "overall_summary" in ref_df.columns:
            summary_rows = ref_df[ref_df["overall_summary"].notna()]
            if not summary_rows.empty:
                chapter_context = summary_rows.iloc[0]["overall_summary"]

        print("Evaluating semantic similarity...")
        for i, (model_row, ref_row) in enumerate(
            tqdm(zip(model_df.iterrows(), ref_df.iterrows()))
        ):
            model_row = model_row[1]  # Get actual row data
            ref_row = ref_row[1]

            model_translation = model_row.get(f"{output_dir}_translation", "")
            ref_translation = ref_row.get("english_translation", "")
            hawaiian_text = ref_row.get("hawaiian_text", "")

            # Semantic similarity
            model_embedding = self.get_embedding(str(model_translation))
            ref_embedding = self.get_embedding(str(ref_translation))
            semantic_sim = self.cosine_similarity(model_embedding, ref_embedding)
            results["translation_metrics"]["semantic_similarity"].append(semantic_sim)

            # Cultural preservation
            cultural_score = self.evaluate_cultural_preservation(
                hawaiian_text, model_translation
            )
            results["translation_metrics"]["cultural_preservation"].append(
                cultural_score
            )

            # Fluency
            fluency_score = self.evaluate_fluency(model_translation)
            results["translation_metrics"]["fluency"].append(fluency_score)

            # Contextual accuracy
            contextual_score = self.evaluate_contextual_accuracy(
                hawaiian_text, model_translation, ref_translation, chapter_context
            )
            results["translation_metrics"]["contextual_accuracy"].append(
                contextual_score
            )

        # Calculate summary statistics
        for metric_name, scores in results["translation_metrics"].items():
            valid_scores = [s for s in scores if not np.isnan(s)]

            if valid_scores:
                results["summary_stats"][metric_name] = {
                    "mean": float(np.mean(valid_scores)),
                    "std": float(np.std(valid_scores)),
                    "min": float(np.min(valid_scores)),
                    "max": float(np.max(valid_scores)),
                    "valid_count": len(valid_scores),
                    "missing_count": len(scores) - len(valid_scores),
                }
            else:
                results["summary_stats"][metric_name] = {
                    "mean": 0.0,
                    "std": 0.0,
                    "min": 0.0,
                    "max": 0.0,
                    "valid_count": 0,
                    "missing_count": len(scores),
                }

        # Print summary
        print("\nTranslation Quality Summary:")
        for metric_name, stats in results["summary_stats"].items():
            print(
                f"  {metric_name.replace('_', ' ').title()}: {stats['mean']:.4f} ± {stats['std']:.4f}"
            )

        return results

    def save_results(self, results: Dict[str, any], output_dir: str):
        """Save translation quality results."""
        os.makedirs("benchmarking/complex_analysis", exist_ok=True)

        # Save detailed results
        json_path = (
            f"benchmarking/complex_analysis/{output_dir}_translation_quality.json"
        )
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)

        # Create detailed CSV for analysis
        detailed_data = []
        for i in range(results["total_passages"]):
            row = {"model": output_dir, "passage_id": i}
            for metric_name, scores in results["translation_metrics"].items():
                if i < len(scores):
                    row[metric_name] = scores[i]
                else:
                    row[metric_name] = np.nan
            detailed_data.append(row)

        detailed_df = pd.DataFrame(detailed_data)
        detailed_csv_path = f"benchmarking/complex_analysis/{output_dir}_translation_quality_detailed.csv"
        detailed_df.to_csv(detailed_csv_path, index=False)

        # Create summary CSV
        summary_data = []
        for metric_name, stats in results["summary_stats"].items():
            summary_data.append(
                {
                    "model": output_dir,
                    "metric": metric_name,
                    "mean": stats["mean"],
                    "std": stats["std"],
                    "min": stats["min"],
                    "max": stats["max"],
                    "valid_count": stats["valid_count"],
                    "missing_count": stats["missing_count"],
                }
            )

        summary_df = pd.DataFrame(summary_data)
        summary_csv_path = f"benchmarking/complex_analysis/{output_dir}_translation_quality_summary.csv"
        summary_df.to_csv(summary_csv_path, index=False)

        print(f"\nTranslation quality results saved to:")
        print(f"  - {json_path}")
        print(f"  - {detailed_csv_path}")
        print(f"  - {summary_csv_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate translation quality for complex analysis outputs"
    )
    parser.add_argument("--model", type=str, help="Specific model to evaluate")

    args = parser.parse_args()

    # Discover available models
    data_dir = Path("data/complex_analysis")
    available_models = []

    if data_dir.exists():
        for file in data_dir.glob("*_extracted.csv"):
            model_name = file.stem.replace("_extracted", "")
            available_models.append(model_name)

    if not available_models:
        print("No complex analysis outputs found.")
        return

    # Initialize evaluator
    evaluator = TranslationQualityEvaluator()

    # Evaluate models
    if args.model:
        if args.model not in available_models:
            print(f"Model '{args.model}' not found. Available: {available_models}")
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

            results = evaluator.evaluate_passage_translations(model_df, ref_df, model)
            evaluator.save_results(results, model)

        except Exception as e:
            print(f"Error evaluating model {model}: {e}")
            continue

    print("\n=== Translation Quality Evaluation Complete ===")


if __name__ == "__main__":
    main()
