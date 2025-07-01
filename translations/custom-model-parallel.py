import pandas as pd
import json
import os
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from constants import prompt
import re
from dotenv import load_dotenv

load_dotenv()

# Allow overriding the output directory via the OUTPUT_DIR environment variable
OUTPUT_DIR = os.getenv("OUTPUT_DIR")
if not OUTPUT_DIR:
    raise ValueError(
        "OUTPUT_DIR not found in environment variables. Please check your .env file."
    )
API_KEY = os.getenv("OPENAI_API_KEY_KOA")
if not API_KEY:
    raise ValueError(
        "OPENAI_API_KEY_KOA not found in environment variables. Please check your .env file."
    )
BASE_URL = os.getenv("OPENAI_API_BASE_URL")
if not BASE_URL:
    raise ValueError(
        "OPENAI_API_BASE_URL not found in environment variables. Please check your .env file."
    )
MODEL_NAME = os.getenv("OPENAI_MODEL_NAME", "gpt-4o")
MAX_PARALLEL = int(os.getenv("MAX_PARALLEL", "1"))
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "1024"))
SELF_REASONING_PARSER = os.getenv("SELF_REASONING_PARSER", False)

os.makedirs("translations/" + OUTPUT_DIR, exist_ok=True)


def translate_text(hawaiian_text: str) -> str | None:
    full_prompt = prompt + hawaiian_text
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    }
    payload = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": full_prompt}],
        "temperature": 0,
        "max_tokens": MAX_TOKENS,
    }
    url = BASE_URL.rstrip("/") + "/chat/completions"
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        llm_content = response.json()["choices"][0]["message"]["content"]
        if SELF_REASONING_PARSER:
            print("now stripping <think> content")
            llm_content = re.sub(r'<think>.*?</think>', '', llm_content, flags=re.DOTALL)
        return llm_content
    print(f"Error: {response.status_code}, {response.text}")
    return None


def process_row(idx: int, hawaiian_text: str, reference_translation: str):
    translation = translate_text(hawaiian_text)
    if translation:
        key_name = OUTPUT_DIR + "_translation"
        output_data = {
            "row_id": idx,
            "hawaiian_text": hawaiian_text,
            "reference_translation": reference_translation,
        }
        output_data[key_name] = translation
        output_file = os.path.join(
            "translations/" + OUTPUT_DIR, f"translation_{idx}.json"
        )
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        print(f"Saved translation to {output_file}")
    else:
        print(f"Failed to translate row {idx}")


def main():
    base_dir = Path(__file__).resolve().parents[1]
    file_path = base_dir / "data" / "dataset.csv"
    try:
        df = pd.read_csv(file_path)
        print(f"Successfully loaded {file_path}. Found {len(df)} rows.")
    except Exception as e:
        print(f"Error loading file {file_path}: {e}")
        return

    hawaiian_col = "Hawaiian"
    english_col = "English"
    if hawaiian_col not in df.columns or english_col not in df.columns:
        print(
            f"Warning: Expected column names '{hawaiian_col}' and '{english_col}' not found."
        )
        hawaiian_col = df.columns[0]
        english_col = df.columns[1]
    print(f"Using columns: Hawaiian='{hawaiian_col}', English='{english_col}'")

    with ThreadPoolExecutor(max_workers=MAX_PARALLEL) as executor:
        futures = []
        for idx, row in df.iterrows():
            hawaiian_text = row[hawaiian_col]
            if pd.isna(hawaiian_text) or not hawaiian_text:
                print(f"Skipping row {idx}: Empty Hawaiian text")
                continue
            futures.append(
                executor.submit(
                    process_row,
                    idx,
                    hawaiian_text,
                    row[english_col],
                )
            )
        for future in as_completed(futures):
            future.result()


if __name__ == "__main__":
    main()
