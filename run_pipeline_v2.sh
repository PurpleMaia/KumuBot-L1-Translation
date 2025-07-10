#!/usr/bin/env bash
set -euo pipefail

# Enhanced pipeline script that supports multiple task types
# Usage:
#   ./run_pipeline_v2.sh simple_translation
#   ./run_pipeline_v2.sh complex_analysis

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
    # TODO: Add evaluation metrics for complex analysis
    echo "Note: Complex analysis evaluation metrics not yet implemented"
    
else
    echo "Unknown task type: $TASK_TYPE"
    exit 1
fi

echo "Pipeline completed successfully!"