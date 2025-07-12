#!/usr/bin/env bash
set -euo pipefail

# Source .env file if it exists to load environment variables
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Enhanced pipeline script that supports multiple task types
# Usage:
#   ./run_pipeline_v2.sh simple_translation
#   ./run_pipeline_v2.sh complex_analysis
#   OUTPUT_DIR=model-name ./run_pipeline_v2.sh hybrid_complex_analysis
#
# For hybrid complex analysis with different models:
#   OUTPUT_DIR=gpt-4 OPENAI_MODEL_NAME=gpt-4 ./run_pipeline_v2.sh hybrid_complex_analysis
#   OUTPUT_DIR=claude-3 OPENAI_MODEL_NAME=claude-3-sonnet ./run_pipeline_v2.sh hybrid_complex_analysis

# Check if task type is provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 <task_type>"
    echo "Available tasks:"
    python -c "from translations.task_config import get_available_tasks; print('\n'.join([f'  - {t}' for t in get_available_tasks()]))"
    exit 1
fi

TASK_TYPE=$1
echo "Running pipeline for task: $TASK_TYPE"

# Run translation/analysis using the new task-aware script
echo "Step 1: Running translation/analysis..."
python translations/custom-model-parallel-v2.py --task "$TASK_TYPE"

# Task-specific post-processing
if [ "$TASK_TYPE" = "simple_translation" ]; then
    echo "Step 2: Extracting translations..."
    export DISCOVER_FOLDERS=true
    python translations/extract_translations.py
    
    echo "Step 3: Computing semantic similarity..."
    python benchmarking/semantic_similarity.py
    
    echo "Step 4: Generating similarity summary..."
    python benchmarking/semantic_similarity_summary.py
    
elif [ "$TASK_TYPE" = "complex_analysis" ]; then
    echo "Step 2: Extracting complex analysis outputs..."
    python translations/extract_complex_analysis.py
    
    echo "Step 3: Evaluating complex analysis..."
    python benchmarking/complex_semantic_similarity.py
    
elif [[ "$TASK_TYPE" == "hybrid_complex_analysis"* ]]; then
    echo "Step 2: Extracting hybrid complex analysis outputs..."
    if [ -z "${OUTPUT_DIR:-}" ]; then
        echo "Error: OUTPUT_DIR environment variable must be set for hybrid complex analysis"
        echo "Example: OUTPUT_DIR=my-model ./run_pipeline_v2.sh hybrid_complex_analysis"
        exit 1
    fi
    python translations/extract_hybrid_complex_analysis.py --output-dir "$OUTPUT_DIR" --task-name "$TASK_TYPE"
    
    echo "Step 3: Evaluating hybrid complex analysis..."
    python benchmarking/complex_semantic_similarity.py --model "$OUTPUT_DIR" --task-name "$TASK_TYPE"
    
    echo "Step 4: Generating complex analysis summary..."
    python benchmarking/complex_semantic_similarity_summary.py
    
else
    echo "Unknown task type: $TASK_TYPE"
    echo "Available task types: simple_translation, complex_analysis, hybrid_complex_analysis (or variants)"
    exit 1
fi

echo "Pipeline completed successfully!"