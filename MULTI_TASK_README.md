# Multi-Task Translation/Analysis System

This document describes the enhanced system that supports multiple types of translation and analysis tasks through a flexible configuration system.

## Overview

The system now supports two main task types:
1. **Simple Translation**: Direct Hawaiian to English translation of individual sentences
2. **Complex Analysis**: Multi-passage analysis with translations, commentary, and overall summaries

## Directory Structure

```
├── task_configs/              # Task configuration files
│   ├── simple_translation.json
│   └── complex_analysis.json
├── data/
│   ├── simple_translation/    # Simple translation datasets
│   │   └── dataset.csv
│   └── complex_analysis/      # Complex analysis datasets
│       └── namakaokapaoo_dataset.csv
└── translations/
    ├── task_config.py         # Configuration loader
    ├── custom-model-parallel-v2.py  # Enhanced translation script
    └── extract_complex_analysis.py  # Complex output extractor
```

## Usage

### Running Simple Translation

```bash
# Option 1: Set environment variables directly
export OUTPUT_DIR=gpt4o
export OPENAI_API_KEY_KOA=your_api_key
export OPENAI_API_BASE_URL=https://api.openai.com/v1
export OPENAI_MODEL_NAME=gpt-4o

# Option 2: Use .env file (recommended)
# Set variables in .env file, then:

# Run the pipeline
./run_pipeline_v2.sh simple_translation
```

### Running Complex Analysis

```bash
# Set environment variables (same as above)
export OUTPUT_DIR=gpt4o_analysis
# ... other environment variables ...

# Run the pipeline
./run_pipeline_v2.sh complex_analysis
```

### Running with Custom Model

```bash
# For custom endpoints (e.g., local models)
export OUTPUT_DIR=my_custom_model
export OPENAI_API_BASE_URL=http://localhost:8000/v1
export OPENAI_MODEL_NAME=llama-3.3
export MAX_PARALLEL=1

./run_pipeline_v2.sh simple_translation
```

## Task Configuration

Task configurations are stored in JSON files in the `task_configs/` directory. Each configuration defines:

- **Dataset**: Path, column names, grouping rules
- **Prompts**: System and user prompts, passage formatting
- **Output**: Expected fields and parsing rules
- **Processing**: Batch size and parallelization settings
- **Evaluation**: Metrics to compute

### Simple Translation Config

```json
{
  "task_name": "simple_translation",
  "task_type": "translation",
  "dataset": {
    "path": "data/simple_translation/dataset.csv",
    "source_column": "Hawaiian",
    "reference_column": "English"
  },
  "output": {
    "fields": ["translation"],
    "parsing": {
      "translation": "translation"
    }
  }
}
```

### Complex Analysis Config

```json
{
  "task_name": "complex_analysis",
  "task_type": "analysis",
  "dataset": {
    "path": "data/complex_analysis/namakaokapaoo_dataset.csv",
    "source_column": "hawaiian_text",
    "grouping_columns": ["chapter"]
  },
  "output": {
    "fields": ["translation", "commentary", "overall_summary"]
  }
}
```

## Adding New Tasks

1. Create a new dataset in the appropriate format
2. Create a task configuration in `task_configs/`
3. Define prompts and output parsing rules
4. Run with: `./run_pipeline_v2.sh your_new_task`

## Environment Variables

- `OUTPUT_DIR`: Directory name for saving outputs (required)
- `OPENAI_API_KEY_KOA`: API key for OpenAI-compatible endpoints
- `OPENAI_API_BASE_URL`: Base URL for API endpoints
- `OPENAI_MODEL_NAME`: Model name to use
- `MAX_PARALLEL`: Maximum parallel requests (default: 3)
- `MAX_TOKENS`: Maximum tokens for responses (default: 1024)
- `SELF_REASONING_PARSER`: Strip reasoning tags if true

## Output Structure

### Simple Translation
```
translations/
└── {OUTPUT_DIR}/
    ├── simple_translation_row_0.json
    ├── simple_translation_row_1.json
    └── ...
```

### Complex Analysis
```
translations/
└── {OUTPUT_DIR}/
    ├── complex_analysis_chapter_1.json
    ├── complex_analysis_chapter_2.json
    └── ...
```

## Additional Tools

### Data Conversion
- `convert_namakaokapaoo_to_csv.py`: Convert markdown analysis files to CSV format for complex analysis tasks

### Testing
- `test_real_pipelines.sh`: Test both old and new pipelines with real API calls
- `test_minimal.sh`: Quick test with minimal data

## Backward Compatibility

The original `custom-model-parallel.py` and `run_pipeline.sh` remain unchanged and continue to work as before. The new system (`custom-model-parallel-v2.py` and `run_pipeline_v2.sh`) provides the enhanced functionality.

## Testing

Both pipelines have been tested and verified to work correctly:
- Old pipeline outputs: `{OUTPUT_DIR}_translation` with full tags
- New pipeline outputs: `{OUTPUT_DIR}_translation` with clean extracted text + `raw_response` with full tags