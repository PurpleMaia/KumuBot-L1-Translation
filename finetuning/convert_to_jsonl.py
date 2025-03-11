import csv
import json

# Path to your input CSV file
input_csv = "finetuning_dataset.csv"
# Path for the output JSONL file
output_jsonl = "hawaiian_english_training.jsonl"

# Define the structure for the fine-tuning examples
# For translation tasks, we'll use a standard format with system, user, and assistant messages
examples = []

# Read the CSV file
with open(input_csv, 'r', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        # Create a training example in the format expected by OpenAI
        example = {
            "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful assistant that translates Hawaiian text to English."
                },
                {
                    "role": "user",
                    "content": row["L1 Hawaiian_Text"]
                },
                {
                    "role": "assistant",
                    "content": row["Reference_Translation"]
                }
            ]
        }
        examples.append(example)

# Write the examples to a JSONL file
with open(output_jsonl, 'w', encoding='utf-8') as jsonlfile:
    for example in examples:
        jsonlfile.write(json.dumps(example) + '\n')

print(f"Successfully converted {len(examples)} examples to JSONL format.")
print(f"Output saved to {output_jsonl}")