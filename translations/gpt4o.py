import pandas as pd
import json
import os
import requests
import time
from constants import prompt
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration
OUTPUT_DIR = "gpt4o"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY_KOA")  # Get API key from .env file
if not OPENAI_API_KEY:
    raise ValueError(
        "OPENAI_API_KEY not found in environment variables. Please check your .env file."
    )
MODEL = "gpt-4o"

# Create output directory if it doesn't exist
os.makedirs(OUTPUT_DIR, exist_ok=True)


def translate_text(hawaiian_text, model=MODEL):
    """
    Translate Hawaiian text to English using the specified OpenAI model.

    Args:
        hawaiian_text (str): The Hawaiian text to translate
        model (str): The OpenAI model to use for translation

    Returns:
        str: The translated English text
    """
    # Create the full prompt by appending the Hawaiian text
    full_prompt = prompt + hawaiian_text

    # Make the API request to OpenAI
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}",
    }

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": full_prompt}],
        "temperature": 0,  # Lower temperature for more consistent translations
        "max_tokens": 1024,  # Adjust based on your needs
    }

    response = requests.post(
        "https://api.openai.com/v1/chat/completions", headers=headers, json=payload
    )

    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        print(f"Error: {response.status_code}, {response.text}")
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

    # Process each row
    for idx, row in df.iterrows():
        hawaiian_text = row[hawaiian_col]
        reference_translation = row[english_col]

        # Skip empty texts
        if pd.isna(hawaiian_text) or not hawaiian_text:
            print(f"Skipping row {idx}: Empty Hawaiian text")
            continue

        print(f"Processing row {idx}: {hawaiian_text[:50]}...")

        # Translate the Hawaiian text
        translation = translate_text(hawaiian_text)

        if translation:
            # Create a JSON object with the data
            output_data = {
                "row_id": idx,
                "hawaiian_text": hawaiian_text,
                "gpt4o_translation": translation,
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
