#!/usr/bin/env bash
set -euo pipefail

# Run translation using llama3.3_parallel.py with environment variables
python translations/llama3.3_parallel.py

# Auto-discover model folders when extracting translations and computing similarity
export DISCOVER_FOLDERS=true
python translations/extract_translations.py
python benchmarking/semantic_similarity.py
python benchmarking/semantic_similarity_summary.py
