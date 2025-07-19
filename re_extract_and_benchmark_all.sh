#!/bin/bash

# Script to re-extract and re-benchmark all models due to grouped commentary fix
# Based on exact model-task combinations from complex_semantic_similarity_summary.py output

echo "Re-extracting and re-benchmarking all models..."
echo "================================================"

# Enhanced few-shot models (16 models)
echo -e "\n### Processing enhanced_fewshot models ###"
models_enhanced=(
    "llama4-maverick-fireworks"
    "gemma-3-4b-qat-gguf-maui"
    "qwen3-235b-a22b-exp-no_think-fireworks"
    "deepseek-v3-0324-fireworks"
    "llama-3.3-70B-Instruct_exl2_6.0bpw-maui"
    "gemma-3-27b-it-qat-mlx-maui"
    "gpt-4_1"
    "llama4-scout-fireworks"
    "o4-mini"
    "gpt-4_1-nano"
    "gemma-3-27b-1temp-cli-manual-aistudio"
    "gpt-4_1-mini"
    "gpt-4o-mini"
    "qwen3-235b-a22b-think-parser-fireworks"
    "gemma-3n-e4b-it-gguf-q4kxl-32k-maui"
    "qwen3-30b-a3b-awq-128k-maui"
    "deepseek-r1-0528-fireworks"
)

for model in "${models_enhanced[@]}"; do
    echo -e "\nProcessing $model (enhanced_fewshot)..."
    python translations/extract_hybrid_complex_analysis.py --output-dir "$model" --task-name hybrid_complex_analysis_enhanced_fewshot
    python benchmarking/complex_semantic_similarity.py --model "$model" --task hybrid_complex_analysis_enhanced_fewshot --exclude-grouped-commentary
done

# Original prompt models (10 models)
echo -e "\n### Processing original prompt models ###"
models_original=(
    "qwen3-235b-a22b-think-parser-fireworks"
    # "llama4-maverick-fireworks"
    "qwen3-32b-fp8-think-parser-deepinfra"
    # "o4-mini"
    # "llama-3.3-70B-Instruct_exl2_6.0bpw-maui"
    "deepseek-r1-0528-fireworks"
    # "llama4-scout-fireworks"
    # "gemma-3-27b-it-qat-mlx-maui"
    "qwen3-30b-a3b-awq-128k-maui"
    "qwen3-4b-awq-40k-maui"
)

for model in "${models_original[@]}"; do
    echo -e "\nProcessing $model (original)..."
    python translations/extract_hybrid_complex_analysis.py --output-dir "$model" --task-name hybrid_complex_analysis_original
    python benchmarking/complex_semantic_similarity.py --model "$model" --task hybrid_complex_analysis_original --exclude-grouped-commentary
done

# # Fewshot models (2 models)
# echo -e "\n### Processing fewshot models ###"
# models_fewshot=(
#     "llama-3.3-70B-Instruct_exl2_6.0bpw-maui"
#     "qwen3-30b-a3b-awq-128k-maui"
# )

# for model in "${models_fewshot[@]}"; do
#     echo -e "\nProcessing $model (fewshot)..."
#     python translations/extract_hybrid_complex_analysis.py --output-dir "$model" --task-name hybrid_complex_analysis_fewshot
#     python benchmarking/complex_semantic_similarity.py --model "$model" --task hybrid_complex_analysis_fewshot
# done

# # Improved prompt models (4 models)
# echo -e "\n### Processing improved prompt models ###"
# models_improved=(
#     "gpt-4_1-mini"
#     "qwen3-30b-a3b-awq-128k-maui"
#     "gpt-4_1-nano"
#     "llama-3.3-70B-Instruct_exl2_6.0bpw-maui"
# )

# for model in "${models_improved[@]}"; do
#     echo -e "\nProcessing $model (improved)..."
#     python translations/extract_hybrid_complex_analysis.py --output-dir "$model" --task-name hybrid_complex_analysis_improved
#     python benchmarking/complex_semantic_similarity.py --model "$model" --task hybrid_complex_analysis_improved
# done

# Regenerate summary
echo -e "\n### Regenerating complex similarity summary ###"
python benchmarking/complex_semantic_similarity_summary.py --detailed

echo -e "\n================================================"
echo "Re-extraction and re-benchmarking complete!"
echo "Total model-task combinations processed: 33"