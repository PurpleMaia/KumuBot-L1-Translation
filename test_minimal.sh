#!/usr/bin/env bash
set -eo pipefail

# Source the .env file to load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

echo "=== Minimal Pipeline Test ==="
echo "API URL: ${OPENAI_API_BASE_URL:-not set}"
echo ""

# Test NEW pipeline for simple translation with just 1 row
echo "Test 1: Testing new pipeline with minimal data..."
export OUTPUT_DIR="test_minimal_simple"

# Create a minimal valid dataset
mkdir -p data/test_minimal
cat > data/test_minimal/dataset.csv << 'EOF'
Hawaiian,English
"Aloha kakahiaka.","Good morning."
EOF

# Temporarily update the config to use test dataset
cp task_configs/simple_translation.json task_configs/simple_translation_backup.json
sed -i '' 's|data/simple_translation/dataset.csv|data/test_minimal/dataset.csv|' task_configs/simple_translation.json

# Run the new pipeline
echo "Running simple translation..."
python translations/custom-model-parallel-v2.py --task simple_translation

# Check results
echo ""
echo "Checking results..."
if ls translations/${OUTPUT_DIR}/simple_translation_*.json 1> /dev/null 2>&1; then
    echo "✓ Translation completed successfully"
    echo "Output:"
    python -c "
import json
import os
files = sorted([f for f in os.listdir('translations/${OUTPUT_DIR}') if f.endswith('.json')])
if files:
    with open(os.path.join('translations/${OUTPUT_DIR}', files[0]), 'r') as f:
        data = json.load(f)
        print(json.dumps(data, indent=2, ensure_ascii=False))
"
else
    echo "✗ No output files created"
fi

# Restore config
mv task_configs/simple_translation_backup.json task_configs/simple_translation.json

# Clean up
rm -rf data/test_minimal
rm -rf translations/test_minimal_simple

echo ""
echo "=== Test Complete ==="
