import pandas as pd
import json
import os
import time
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration
OUTPUT_DIR = "gpt-4o-mini-finetuned"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY_KOA")  # Get API key from .env file
if not OPENAI_API_KEY:
    raise ValueError(
        "OPENAI_API_KEY not found in environment variables. Please check your .env file."
    )

# Your fine-tuned model name - replace with your actual fine-tuned model ID
FINETUNED_MODEL = "ft:gpt-4o-mini-2024-07-18:personal:finetuned-mini:B9exEeD9"

# Create output directory if it doesn't exist
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)


def translate_text(hawaiian_text, model=FINETUNED_MODEL):
    """
    Translate Hawaiian text to English using the fine-tuned OpenAI model.

    Args:
        hawaiian_text (str): The Hawaiian text to translate
        model (str): The OpenAI model to use for translation

    Returns:
        str: The translated English text
    """
    try:
        # Make the API request to OpenAI using the client
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that translates Hawaiian text to English.",
                },
                {"role": "user", "content": hawaiian_text},
            ],
            temperature=0,  # Lower temperature for more consistent translations
            max_tokens=1024,  # Adjust based on your needs
        )

        # Extract translated text from response
        return response.choices[0].message.content

    except Exception as e:
        print(f"Error in API call: {e}")
        return None


def main():
    # Read the dataset from the specific file path
    file_path = "../data/dataset.csv"
    try:
        df = pd.read_csv(file_path)
        print(f"Successfully loaded {file_path}. Found {len(df)} rows.")
    except Exception as e:
        print(f"Error loading file {file_path}: {e}")
        return

    # Use the exact column names
    hawaiian_col = "Hawaiian"
    english_col = "English"

    # Verify the columns exist
    if hawaiian_col not in df.columns or english_col not in df.columns:
        print(
            f"Warning: Expected column names '{hawaiian_col}' and '{english_col}' not found."
        )
        print(f"Available columns: {df.columns.tolist()}")
        # Fall back to first and second columns if needed
        hawaiian_col = df.columns[0]
        english_col = df.columns[1]

    print(f"Using columns: Hawaiian='{hawaiian_col}', English='{english_col}'")
    print(f"Using fine-tuned model: {FINETUNED_MODEL}")

    # Process each row
    for idx, row in df.iterrows():
        hawaiian_text = row[hawaiian_col]
        reference_translation = row[english_col]

        # Skip empty texts
        if pd.isna(hawaiian_text) or not hawaiian_text:
            print(f"Skipping row {idx}: Empty Hawaiian text")
            continue

        print(f"Processing row {idx}: {hawaiian_text[:50]}...")

        # Translate the Hawaiian text using the fine-tuned model
        translation = translate_text(hawaiian_text)

        if translation:
            # Create a JSON object with the data
            output_data = {
                "row_id": idx,
                "hawaiian_text": hawaiian_text,
                "gpt-4o-mini-finetuned_translation": translation,
                "reference_translation": reference_translation,
            }

            # Save to a JSON file
            output_file = os.path.join(OUTPUT_DIR, f"translation_{idx}.json")
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)

            print(f"Saved translation to {output_file}")

            # Sleep briefly to avoid hitting API rate limits
            time.sleep(1)
        else:
            print(f"Failed to translate row {idx}")


if __name__ == "__main__":
    main()
