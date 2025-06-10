# Hawaiian to English Translation Project

This repository contains scripts and data for evaluating large language models (LLMs) on Hawaiian→English translation. The dataset consists of 10 Hawaiian sentences with reference translations.

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
   ```
2. Run any script in `translations/` to translate the dataset, e.g.:
   ```bash
   python translations/gpt4o.py
   ```
   Each script writes JSON files to a folder named after the model.
3. Combine model outputs back into `data/dataset.csv`:
   ```bash
   python translations/extract_translations.py
   ```
4. Evaluate translations:
   - `benchmarking/semantic_similarity.py` computes embedding similarities.
   - `benchmarking/llm_as_judge.py` compares translations using an LLM and writes `roundrobin.csv` and `judge_results_summary.csv`.
   - `benchmarking/semantic_similarity_summary.py` summarizes similarity scores.
5. (Optional) Launch the demo chatbot:
   ```bash
   python demo_chatbot/app.py
   ```

These steps reproduce the translation outputs and benchmarking results in the repository.
