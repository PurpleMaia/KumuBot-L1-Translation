# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Hawaiian-to-English translation benchmarking project that evaluates multiple Large Language Models (LLMs) on their ability to translate Hawaiian text. The project includes:
- Translation scripts for various LLMs (GPT-4, Llama, Gemini, Claude, etc.)
- Benchmarking tools for evaluating translation quality
- A Flask-based demo chatbot for interactive translation
- Fine-tuning capabilities for custom models

## Common Commands

### Setup and Dependencies
```bash
# Install dependencies using uv (recommended)
uv pip install -r requirements.txt

# Or using regular pip
pip install -r requirements.txt
```

### Running Translations
```bash
# Run individual model translations
python translations/gpt4o.py
python translations/llama3.3_parallel.py
python translations/gemini-1.5-pro.py

# Run custom model with environment variables
OUTPUT_DIR=my_output OPENAI_MODEL_NAME=gpt-4 MAX_PARALLEL=5 python translations/custom-model-parallel.py

# Run the complete pipeline (translation + benchmarking)
./run_pipeline.sh
```

### Benchmarking
```bash
# Extract translations from JSON outputs to dataset
python translations/extract_translations.py

# Compute semantic similarity scores
python benchmarking/compute_similarity.py

# Generate similarity summary
python benchmarking/generate_similarity_summary.py

# Run LLM-as-judge evaluation
python benchmarking/llm_judge_wrapper.py
```

### Demo Chatbot
```bash
# Start the Flask web server
cd demo_chatbot
python app.py
# Access at http://localhost:5003
```

## Architecture and Key Components

### Core Data Flow
1. **Source Data**: `data/dataset.csv` contains 10 Hawaiian sentences with reference translations
2. **Translation**: Scripts in `translations/` call various LLM APIs to generate translations
3. **Storage**: Results are saved as JSON files in `translations/[model_name]/`
4. **Extraction**: `extract_translations.py` consolidates outputs back into the dataset
5. **Evaluation**: Benchmarking scripts compute quality metrics

### Environment Configuration
Required environment variables (set in `.env` file):
- `OPENAI_API_KEY_KOA` - OpenAI API key
- `GROQ_API_KEY` - Groq API key for Llama models
- `GOOGLE_API_KEY` - Google API key for Gemini models
- `ANTHROPIC_API_KEY` - Anthropic API key for Claude models
- `OPENAI_BASE_URL` - Custom endpoint for OpenAI-compatible APIs (optional)
- `OPENAI_MODEL_NAME` - Model name for custom endpoints
- `OUTPUT_DIR` - Output directory for custom model results
- `MAX_PARALLEL` - Maximum parallel requests (default: 3)

### Translation Script Architecture
All translation scripts follow a similar pattern:
1. Load dataset from CSV
2. Initialize LLM client with API credentials
3. Iterate through Hawaiian sentences
4. Generate translations with specific prompts
5. Save results as JSON with metadata (model, temperature, timestamps)

### Benchmarking Approach
- **Semantic Similarity**: Uses sentence embeddings to compare translations with references
- **LLM Judge**: Uses GPT-4 to evaluate translation quality on multiple criteria
- Results are aggregated and summarized for comparison

## Testing

Currently, there are no automated tests in the repository. When adding new functionality:
- Test translation scripts manually with sample sentences
- Verify JSON output format matches expected structure
- Check that extraction script correctly updates the dataset
- Ensure benchmarking scripts handle missing/incomplete data gracefully

## Workflow Tips

- Always use uv pip to work with packages instead of just pip
- When running scripts and testing code, use the .env settings OPENAI_API_BASE_URL and OPENAI_API_EMBEDDING_BASE_URL and OPENAI_MODEL_NAME don't try to mock a server response. and use the real data files
instead of making example test data files (but it is ok if you want to temporarily use a subset of the real data for tests if that makes sense at times)