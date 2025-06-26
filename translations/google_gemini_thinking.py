import pandas as pd
import json
import os
import time
from constants import prompt
from dotenv import load_dotenv
from google import genai
from pathlib import Path
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Configuration

OUTPUT_DIR = "gemini-2.0-flash-thinking"
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")  # Get API key from .env file
if not GOOGLE_API_KEY:
    raise ValueError(
        "GOOGLE_API_KEY not found in environment variables. Please check your .env file."
    )
MODEL = "gemini-2.0-flash-thinking-exp-01-21"  # Keeping the original model name

# Create output directory if it doesn't exist
os.makedirs(OUTPUT_DIR, exist_ok=True)


class GeminiTranslator:
    def __init__(self, api_key: str):
        """
        Initialize the Gemini translator with API credentials

        Args:
            api_key (str): Google API key
        """
        self.client = genai.Client(
            api_key=api_key, http_options={"api_version": "v1alpha"}
        )
        self.model = MODEL

    def translate_text(self, hawaiian_text: str) -> str:
        """
        Translate Hawaiian text to English using the specified Gemini model.

        Args:
            hawaiian_text (str): The Hawaiian text to translate

        Returns:
            str: The translated English text
        """
        try:
            # Create the full prompt by appending the Hawaiian text
            full_prompt = prompt + hawaiian_text

            # Make the API call
            response = self.client.models.generate_content(
                model=self.model,
                contents=full_prompt,
                config={
                    "temperature": 0.0,
                    "top_p": 0.95,
                    "top_k": 0,
                    "max_output_tokens": 1024,
                },
            )

            # Extract the response text
            if (
                response.candidates
                and response.candidates[0].content
                and response.candidates[0].content.parts
            ):
                return response.candidates[0].content.parts[0].text
            return None

        except Exception as e:
            logger.error(f"Error translating text: {str(e)}")
            return None

    def process_dataset(
        self, dataframe: pd.DataFrame, hawaiian_col: str, english_col: str
    ):
        """
        Process all rows in the dataset

        Args:
            dataframe (pd.DataFrame): The dataset containing Hawaiian text
            hawaiian_col (str): Column name for Hawaiian text
            english_col (str): Column name for reference English translation
        """
        for idx, row in dataframe.iterrows():
            hawaiian_text = row[hawaiian_col]
            reference_translation = row[english_col]

            # Skip empty texts
            if pd.isna(hawaiian_text) or not hawaiian_text:
                logger.info(f"Skipping row {idx}: Empty Hawaiian text")
                continue

            logger.info(f"Processing row {idx}: {hawaiian_text[:50]}...")

            # Translate the Hawaiian text
            translation = self.translate_text(hawaiian_text)

            if translation:
                # Create a JSON object with the data
                output_data = {
                    "row_id": idx,
                    "hawaiian_text": hawaiian_text,
                    "gemini_translation": translation,
                    "reference_translation": reference_translation,
                }

                # Save to a JSON file
                output_file = os.path.join(OUTPUT_DIR, f"translation_{idx}.json")
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(output_data, f, ensure_ascii=False, indent=2)

                logger.info(f"Saved translation to {output_file}")

                # Sleep briefly to avoid hitting API rate limits
                time.sleep(1)
            else:
                logger.error(f"Failed to translate row {idx}")


def main():
    # Read the dataset from the specific file path
    file_path = "../data/dataset.csv"
    try:
        df = pd.read_csv(file_path)
        logger.info(f"Successfully loaded {file_path}. Found {len(df)} rows.")
    except Exception as e:
        logger.error(f"Error loading file {file_path}: {e}")
        return

    # Use the exact column names
    hawaiian_col = "Hawaiian"
    english_col = "English"

    # Verify the columns exist
    if hawaiian_col not in df.columns or english_col not in df.columns:
        logger.warning(
            f"Warning: Expected column names '{hawaiian_col}' and '{english_col}' not found."
        )
        logger.info(f"Available columns: {df.columns.tolist()}")
        # Fall back to first and second columns if needed
        hawaiian_col = df.columns[0]
        english_col = df.columns[1]

    logger.info(f"Using columns: Hawaiian='{hawaiian_col}', English='{english_col}'")

    # Initialize translator
    translator = GeminiTranslator(GOOGLE_API_KEY)

    # Process the dataset
    translator.process_dataset(df, hawaiian_col, english_col)


if __name__ == "__main__":
    main()
