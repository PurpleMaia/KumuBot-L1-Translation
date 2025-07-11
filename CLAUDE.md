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

## Hybrid Complex Analysis Approach

The project includes a hybrid complex analysis system for processing longer texts (such as Hawaiian stories) that require both passage-level and chapter-level analysis.

### Hybrid Processing Architecture

The hybrid approach combines two processing modes:

1. **Passage-level Processing**: Individual paragraphs are processed for translation and commentary
2. **Chapter-level Processing**: Overall summaries are generated after all passages are complete

### Key Components

#### Configuration System

- Uses JSON task configuration files (e.g., `config/tasks/hybrid_complex_analysis.json`)
- Supports both passage-level and chapter-level prompts
- Configurable parallel processing limits

#### Translation Script (`custom-model-parallel-v2.py`)

- Implements hybrid processing mode with automatic retry logic
- Handles passage-level translation and commentary generation
- Generates chapter-level summaries after all passages are processed
- Includes exponential backoff for failed requests
- Supports streaming responses to avoid timeouts
- **Debug mode**: Use `--debug` flag to show LLM response content (translations and commentary) during processing

#### Extraction (`extract_hybrid_complex_analysis.py`)

- Extracts individual passage JSON files into consolidated CSV format
- Handles both passage-level and chapter-level outputs
- Manages special cases (e.g., grouped commentary for paragraphs 10-14)

#### Benchmarking (`complex_semantic_similarity.py`)

- Evaluates semantic similarity for multiple components (translation, commentary, summary)
- Supports both regular and hybrid extracted files
- Provides component-specific evaluation metrics

### Usage Commands

```bash
# Run hybrid complex analysis (individual steps)
OPENAI_MODEL_NAME=gpt-4 OPENAI_API_BASE_URL=https://api.example.com/v1 MAX_PARALLEL=5 python translations/custom-model-parallel-v2.py --task hybrid_complex_analysis

# Run with debug output to see LLM response content (translations and commentary)
python translations/custom-model-parallel-v2.py --task hybrid_complex_analysis --debug

# Extract hybrid results to CSV
python translations/extract_hybrid_complex_analysis.py --output-dir model_name

# Evaluate semantic similarity for complex analysis
python benchmarking/complex_semantic_similarity.py --model model_name

# List available models for evaluation
python benchmarking/complex_semantic_similarity.py --list

# Generate summary comparison across all models
python benchmarking/complex_semantic_similarity_summary.py --detailed
```

### Pipeline Commands

```bash
# Run complete pipeline for hybrid complex analysis
OUTPUT_DIR=model-name ./run_pipeline_v2.sh hybrid_complex_analysis

# Compare multiple models using pipeline
./compare_models.sh model1 model2 model3

# Examples with different models
OUTPUT_DIR=gpt-4 OPENAI_MODEL_NAME=gpt-4 ./run_pipeline_v2.sh hybrid_complex_analysis
OUTPUT_DIR=claude-3 OPENAI_MODEL_NAME=claude-3-sonnet ./run_pipeline_v2.sh hybrid_complex_analysis
```

### Data Structure

Hybrid complex analysis uses a structured approach:

- **Input**: Complex analysis dataset with passages, chapters, and reference translations
- **Processing**: Individual passage JSON files saved per paragraph
- **Output**: Consolidated CSV with translation, commentary, and summary components
- **Evaluation**: Component-specific similarity metrics

#### Data Format Standards

**Summary Placement**: Chapter-level summaries are always placed in **passage 1** to match the reference dataset structure. This ensures consistent comparison during benchmarking.

**Component Distribution**:

- **Translation & Commentary**: Available for each individual passage (1-14)
- **Summary**: Only in passage 1 (chapter-level analysis)
- **Missing Data**: Properly handled as NaN/empty for failed extractions

### Special Features

- **Automatic Retry**: Failed passages are automatically retried with exponential backoff
- **Grouped Commentary**: Handles special cases where multiple paragraphs share commentary (e.g., paragraphs 10-14 in the reference dataset)
  - **Important Fix**: As of the latest update, grouped commentary passages now correctly save individual JSON files
- **Streaming Support**: Uses streaming responses to avoid Cloudflare timeouts
- **Parallel Processing**: Configurable parallelization with timeout handling
- **Individual Passage Recovery**: Malformed responses can be fixed by creating subset datasets and reprocessing specific passages
- **Debug Mode Control**: By default, shows all status messages and progress indicators but hides LLM response content. Use `--debug` to see LLM response content (translations and commentary) during processing

### Current Model Performance

Latest complex analysis semantic similarity results (ranked by composite score):

1. **qwen3-235b-a22b-think-parser-fireworks**: Composite score 0.8155 (Translation: 0.9365, Commentary: 0.6885, Summary: 0.8276)
2. **gemma-3-27b-it-qat-mlx-maui**: Composite score 0.8108 (Translation: 0.9393, Commentary: 0.6856, Summary: 0.8042)
3. **llama4-maverick-fireworks**: Composite score 0.7963 (Translation: 0.9386, Commentary: 0.6816, Summary: 0.7410)
4. **qwen3-30b-a3b-awq-128k-maui**: Composite score 0.7668 (Translation: 0.8533, Commentary: 0.6902, Summary: 0.7470)
5. **qwen3-4b-awq-40k-maui**: Composite score 0.7301 (Translation: 0.8085, Commentary: 0.6221, Summary: 0.7891)

All models achieved 100% completion rate (14/14 passages) with successful handling of grouped commentary passages (10-14).

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

## Guidance Notes

- **Timeout Handling**:
  - When running bash commands or executing .sh scripts please use at least a 30 minute timeout instead of 2 minutes
