#!/usr/bin/env bash
set -euo pipefail

# Compare multiple models using hybrid complex analysis pipeline
# Usage:
#   ./compare_models.sh model1 model2 model3
#   ./compare_models.sh gpt-4 claude-3 llama-3

if [ $# -eq 0 ]; then
    echo "Usage: $0 <model1> [model2] [model3] ..."
    echo "Example: $0 gpt-4 claude-3-sonnet llama-3-70b"
    echo ""
    echo "Note: Make sure to set the appropriate environment variables:"
    echo "  OPENAI_MODEL_NAME=<model_name>"
    echo "  OPENAI_API_BASE_URL=<api_endpoint>"
    echo "  Or use .env file"
    exit 1
fi

echo "🚀 Running hybrid complex analysis pipeline for multiple models..."
echo "Models to compare: $*"
echo ""

# Run pipeline for each model
for model in "$@"; do
    echo "=================================================="
    echo "🔄 Processing model: $model"
    echo "=================================================="
    
    # Set environment and run pipeline
    export OUTPUT_DIR="$model"
    export OPENAI_MODEL_NAME="$model"
    
    # Run the full pipeline
    ./run_pipeline_v2.sh hybrid_complex_analysis
    
    echo "✅ Completed processing for $model"
    echo ""
done

echo "=================================================="
echo "📊 Generating comparison summary..."
echo "=================================================="

# Run benchmarking for all models to show comparison
python benchmarking/complex_semantic_similarity.py --list

echo ""
echo "📈 Individual model results:"
for model in "$@"; do
    echo ""
    echo "🔍 Model: $model"
    if [ -f "benchmarking/complex_analysis/${model}_similarity_summary.csv" ]; then
        echo "Results:"
        cat "benchmarking/complex_analysis/${model}_similarity_summary.csv"
        echo ""
        echo "Detailed results saved to:"
        echo "  - benchmarking/complex_analysis/${model}_similarity_results.json"
        echo "  - benchmarking/complex_analysis/${model}_similarity_summary.csv"
    else
        echo "❌ No results found for $model"
    fi
    echo "---"
done

echo ""
echo "🎉 Model comparison complete!"
echo "Check the benchmarking/complex_analysis/ directory for detailed results."