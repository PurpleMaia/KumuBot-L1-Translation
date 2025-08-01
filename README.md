# Hawaiian to English Translation Project

This repository contains scripts and data for evaluating large language models (LLMs) on Hawaiian→English translation. The head-to-head dataset consists of 10 Hawaiian sentences with reference translations.

## Directory Structure

- `benchmarking/` – scripts to compute embedding similarities and perform pairwise LLM judging.
- `data/` – `dataset.csv` containing the source text, reference translations, and model output columns.
- `demo_chatbot/` – Flask application for interactive translation via OpenAI or Groq.
- `finetuning/` – CSV and script for fine‑tuning models.
- `translations/` – scripts that call various LLMs and store their JSON outputs.

A small text file `next_steps` lists potential future work.

## Dependencies

Install required Python packages using [uv](https://github.com/astral-sh/uv):

```bash
# install uv if you don't already have it
curl -Ls https://astral.sh/uv/install.sh | sh

# create a virtual environment and install dependencies (note that sourcing the .venv is required in case you also use conda)
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

## Setup

1. Create a `.env` file (or export variables) with your API keys:
   ```
   OPENAI_API_KEY_KOA=<OpenAI key used for scripts>
   OPENAI_API_KEY=<key for the demo chatbot>
   GROQ_API_KEY=<Groq API key>
   GOOGLE_API_KEY=<Gemini API key>
   OPENAI_BASE_URL=<custom base URL for OpenAI API (optional)>
   ```
2. Run any script in `translations/` to translate the dataset. Most scripts now
   accept `OUTPUT_DIR` and `OPENAI_MODEL_NAME` from the environment. For example:
   ```bash
   OPENAI_MODEL_NAME=gpt-4o OUTPUT_DIR=gpt-4o \
   MAX_PARALLEL=4 python translations/custom-model-parallel.py
   ```
   Each script writes JSON files to a folder named after the model (or the value
   of `OUTPUT_DIR`).
3. Combine model outputs back into `data/dataset.csv`. You can specify folders
   via `MODEL_FOLDERS` or set `DISCOVER_FOLDERS=true` to automatically detect
   them:
   ```bash
   python translations/extract_translations.py
   ```
4. Evaluate translations:
   - `benchmarking/semantic_similarity.py` computes embedding similarities. It uses the same `MODEL_FOLDERS`/`DISCOVER_FOLDERS` logic as `extract_translations.py`.
   - `benchmarking/llm_as_judge.py` compares translations using an LLM and writes `roundrobin.csv` and `judge_results_summary.csv`.
   - `benchmarking/semantic_similarity_summary.py` summarizes similarity scores.
5. (Optional) launch the entire translation and evaluation pipeline with
   `run_pipeline.sh`:
   ```bash
   OPENAI_BASE_URL=my-url OPENAI_MODEL_NAME=my-model OUTPUT_DIR=my-folder ./run_pipeline.sh
   ```
6. (Optional) Launch the demo chatbot:
   ```bash
   python demo_chatbot/app.py
   ```

These steps reproduce the translation outputs and benchmarking results in the repository.
