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

# Manual CLI testing with web-based LLMs (no API required)
OUTPUT_DIR=model-name python translations/custom-model-v2-cli.py --task hybrid_complex_analysis_enhanced_fewshot

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
- **Grouped Commentary Handling**: Supports excluding passages 10-14 from commentary evaluation when using grouped reference
- Results are aggregated and summarized for comparison

## Hybrid Complex Analysis Approach

The project includes a hybrid complex analysis system for processing longer texts (such as Hawaiian stories) that require both passage-level and chapter-level analysis.

### Hybrid Processing Architecture

The hybrid approach combines two processing modes:

1. **Passage-level Processing**: Individual paragraphs are processed for translation and commentary
2. **Chapter-level Processing**: Overall summaries are generated after all passages are complete

### Key Components

#### Configuration System

- Uses JSON task configuration files (e.g., `task_configs/hybrid_complex_analysis_enhanced_fewshot.json`)
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

# Evaluate with grouped commentary excluded (passages 10-14)
python benchmarking/complex_semantic_similarity.py --model model_name --exclude-grouped-commentary

# List available models for evaluation
python benchmarking/complex_semantic_similarity.py --list

# Generate summary comparison across all models (shows both regular and excluded versions)
python benchmarking/complex_semantic_similarity_summary.py

# Show only results with grouped commentary excluded
python benchmarking/complex_semantic_similarity_summary.py --exclude-grouped-commentary
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

**Enhanced few-shot success rate**: 82% of tested models (9/11) showed significant improvement
All models achieved 100% completion rate (14/14 passages) with successful handling of grouped commentary passages (10-14).

**Manual CLI Validation**: Direct comparison between API (Gemma 3 27B QAT MLX-maui: 0.8271) and web browser manual CLI (Gemma 3 27B Manual CLI: 0.8187) shows consistent performance with only 0.84 point difference, validating manual testing methodology.

### Prompt Engineering Results

**Multi-model testing across prompt variations revealed clear patterns:**

#### **Enhanced Few-shot Prompting: Production-Ready Strategy**

- **82% success rate**: 9 out of 11 tested models showed significant improvement
- **Cross-architecture effectiveness**: Works across Llama, Gemma, Qwen, and DeepSeek families
- **Consistent gains**: 20-47 point composite score improvements for compatible models
- **Key insight**: Quality examples outperform prescriptive instructions

#### **Model Architecture Compatibility Patterns**

- **✅ Standard models**: Universal success (100% improvement rate)
- **✅ Implicit reasoning models**: DeepSeek V3 achieved #4 ranking with enhanced few-shot
- **⚠️ Explicit reasoning models**: R1-style and think-parser models showed degraded performance
- **✅ Original prompts for reasoning models**: DeepSeek R1 improved +4.9 points with original prompts (0.7430 → 0.7922)
- **Identification rule**: Use original prompts for models that output `<think>` chains or have "r1"/"think-parser" in name

#### **"Improved" Prompts: Confirmed Anti-pattern**

- **Performance degradation**: Consistently worst scores across all tested architectures
- **Translation quality drops**: 2-4% reduction due to cognitive overload
- **Over-engineering evidence**: Complex constraints reduce natural language generation

## Manual CLI Testing Tool

The project includes a manual CLI testing tool (`translations/custom-model-v2-cli.py`) that enables testing task configurations with web-based LLMs without requiring API access.

### Manual CLI Features

- **Clipboard Integration**: Automatically copies prompts to clipboard for easy pasting into web interfaces
- **Flexible Input Methods**: Choose between clipboard reading (`c`) or manual paste (`p`) for LLM responses
- **Progress Tracking**: Shows completion status and allows early exit with `q`
- **Same Format Output**: Generates identical JSON files compatible with existing extraction and benchmarking pipeline
- **Special Case Handling**: Supports grouped commentary and all task configuration features

### Manual CLI Usage

```bash
# Test enhanced few-shot prompts with web LLM
OUTPUT_DIR=model-name python translations/custom-model-v2-cli.py --task hybrid_complex_analysis_enhanced_fewshot

# Test original prompts
OUTPUT_DIR=model-name python translations/custom-model-v2-cli.py --task hybrid_complex_analysis_original

# Enable debug output
python translations/custom-model-v2-cli.py --task hybrid_complex_analysis_enhanced_fewshot --debug
```

### Manual CLI Workflow

1. Script copies prompt to clipboard automatically
2. Paste prompt into web LLM interface (Google AI Studio, ChatGPT, etc.)
3. Copy LLM response back to clipboard
4. Type `c` to read from clipboard, `p` to manually paste, or `q` to quit
5. Process repeats for all 14 passages plus chapter summary
6. Results compatible with existing benchmarking pipeline

### Manual CLI Validation Results

**Gemma 3 27B Performance Comparison:**

- **API Version** (MLX-maui): Composite 0.8271 (Translation: 95.0%, Commentary: 72.5%, Summary: 78.5%)
- **Manual CLI Version** (Google AI Studio): Composite 0.8187 (Translation: 95.3%, Commentary: 71.4%, Summary: 75.9%)
- **Difference**: Only 0.84 points (1% relative difference), validating manual testing methodology

This demonstrates that manual CLI testing provides reliable results for comparing prompt strategies and model capabilities without requiring API access.

## API Cost Analysis

### Complex Analysis Task Costs

**o4-mini** (enhanced few-shot):

- **Cost**: $0.130 per complete complex analysis run
- **Performance**: 0.8237 composite score (ranked 10th)
- **Strengths**: Complete output with balanced performance across all components

**GPT-4.1** (enhanced few-shot):

- **Cost**: $0.090 per complete complex analysis run (56,271 tokens)
- **Performance**: 0.8257 composite score (ranked 6th)
- **Strengths**: **Highest translation quality (96.6%)** among all models tested
- **Complete**: Now includes all components (translation, commentary, summary)

**GPT-4.1-nano** (enhanced few-shot):

- **Cost**: ~$0.026 per complete complex analysis run (estimated)
- **Performance**: 0.8230 composite score (ranked 10th)
- **Strengths**: Highest summary quality (87.0%) among OpenAI models

**GPT-4.1-mini** (enhanced few-shot):

- **Cost**: ~$0.026 per complete complex analysis run (24,801 tokens baseline)
- **Performance**: 0.8176 composite score (ranked 12th)
- **Improvement**: +0.76 points over improved prompts

**Cost Comparison**:

- **o4-mini**: $0.130 (highest cost, balanced performance)
- **GPT-4.1**: $0.090 (premium translation quality)
- **GPT-4.1-mini/nano**: $0.026 (most cost-effective)
- **Cost ratios**: o4-mini is 5x more expensive than mini/nano; GPT-4.1 is 3.5x more expensive

#### **Enhanced Few-Shot Implementation**

- **3 diverse examples**: Character introduction, dialogue, and symbolic action passages
- **Chapter summary example**: Demonstrates synthesis and scholarly analysis depth
- **Natural flow**: No forced formatting or rigid structural requirements
- **Production config**: `hybrid_complex_analysis_enhanced_fewshot.json`

#### **Component-Specific Excellence Achieved**

- **Translation champion**: Llama4 Maverick (96.4% similarity)
- **Commentary leaders**: Multiple models achieving 72%+ similarity
- **Summary specialist**: Qwen3 30B (88.4% similarity - new record)

### Text Normalization in Benchmarking

The semantic similarity evaluation now includes text normalization (as of latest update) to focus on content rather than formatting differences:

- **Applied equally** to both reference and model texts before computing embeddings
- **Normalizations include**: bullet standardization, markdown removal, whitespace cleanup, header formatting
- **Impact**: Revealed true semantic similarities by removing formatting "false positives"
- **Key finding**: Original model summaries showed 3.7% drop after normalization, revealing that formatting was masking content differences
- **Few-shot improvement**: Commentary improved by 3.73% after normalization, showing genuine content alignment

### Commentary Performance Insights

Commentary generation appears to be the most challenging component for current LLMs, with scores typically ranging from 68-74%. The reference commentary expects:

- Specific allegorical interpretations
- Historical period references (e.g., 'Ai Kapu era)
- Academic citations
- Bullet-point structure with hierarchical organization

**Grouped Commentary Note**: The reference dataset groups passages 10-14 with identical generic commentary. Models generate individual commentaries for each passage, which can inflate similarity scores. Use `--exclude-grouped-commentary` flag to exclude these passages for fairer evaluation.

### Summary Performance Deep Dive

Investigation of low summary scores revealed a critical insight: The reference summary takes a **colonial historiographical perspective**, arguing the story was potentially invented post-1893 as pro-US annexation propaganda. Models struggle with this because:

1. **DeepSeek R1**: Enhanced few-shot prompting caused it to misinterpret the colonial critique, making the Hawaiian hero represent Western colonialism (43.9% score)
2. **Qwen3-235B**: Correctly adopted colonial-era analysis but reached the opposite conclusion, seeing the story as anti-colonial resistance rather than pro-colonial propaganda (75.8% score)

This highlights how **political interpretation remains subjective** even with clear analytical frameworks, and explicit reasoning models may struggle with nuanced cultural criticism.

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
