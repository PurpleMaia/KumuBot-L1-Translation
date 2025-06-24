#!/usr/bin/env python3
"""
Test script to verify MLX model loading and identify tokenizer issues.
"""

import sys
import json
from pathlib import Path
from mlx_lm import load

def test_model_loading(model_path):
    """Test if a model can be loaded successfully."""
    print(f"Testing model: {model_path}")
    print("-" * 50)
    
    model_dir = Path(model_path)
    
    # Check if model directory exists
    if not model_dir.exists():
        print(f"❌ Error: Model directory does not exist: {model_path}")
        return False
    
    # Check for required files
    required_files = ["config.json", "model.safetensors"]
    tokenizer_files = ["tokenizer.json", "tokenizer_config.json", "tokenizer.model"]
    
    print("Checking for required files:")
    for file in required_files:
        if (model_dir / file).exists():
            print(f"✓ {file}")
        else:
            print(f"❌ {file} - MISSING")
    
    print("\nChecking for tokenizer files:")
    found_tokenizer = False
    for file in tokenizer_files:
        if (model_dir / file).exists():
            print(f"✓ {file}")
            found_tokenizer = True
        else:
            print(f"- {file} - not found")
    
    if not found_tokenizer:
        print("❌ No tokenizer files found!")
        return False
    
    # Try to load the model
    print("\nAttempting to load model...")
    try:
        model, tokenizer = load(model_path)
        print("✓ Model loaded successfully!")
        
        # Test tokenizer
        test_text = "Aloha"
        tokens = tokenizer.encode(test_text)
        decoded = tokenizer.decode(tokens)
        print(f"\nTokenizer test:")
        print(f"  Input: {test_text}")
        print(f"  Tokens: {tokens}")
        print(f"  Decoded: {decoded}")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to load model: {type(e).__name__}: {e}")
        
        # Check if it's a tokenizer issue
        if "tokenizer" in str(e).lower() or "ModelWrapper" in str(e):
            print("\n💡 This appears to be a tokenizer compatibility issue.")
            print("Possible solutions:")
            print("1. Re-download the model from a reliable source")
            print("2. Try a different model (see suggestions below)")
            print("3. Convert a Hugging Face model to MLX format")
        
        return False

def suggest_alternative_models():
    """Suggest alternative MLX models that are known to work."""
    print("\n" + "="*50)
    print("Note that LM-Studio downloaded model folders may be broken. Suggested MLX models that should work:")
    print("="*50)
    
    models = [
        {
            "name": "Llama-3.2-1B-Instruct",
            "repo": "mlx-community/Llama-3.2-1B-Instruct-4bit",
            "size": "~1GB",
            "notes": "Small, fast, good for testing"
        },
        {
            "name": "Phi-3.5-mini",
            "repo": "mlx-community/Phi-3.5-mini-instruct-4bit",
            "size": "~2GB",
            "notes": "Microsoft's efficient model"
        },
        {
            "name": "Qwen2.5-1.5B",
            "repo": "mlx-community/Qwen2.5-1.5B-Instruct-4bit",
            "size": "~1.5GB",
            "notes": "Good multilingual support"
        }
    ]
    
    for model in models:
        print(f"\n{model['name']}:")
        print(f"  Repo: {model['repo']}")
        print(f"  Size: {model['size']}")
        print(f"  Notes: {model['notes']}")
        print(f"  Install: huggingface-cli download {model['repo']}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_mlx_model.py <model_path>")
        print("\nExample:")
        print("  python test_mlx_model.py ./mlx-community/Qwen3-4B-6bit")
        sys.exit(1)
    
    model_path = sys.argv[1]
    success = test_model_loading(model_path)
    
    if not success:
        suggest_alternative_models()
        
        print("\n" + "="*50)
        print("Converting a Hugging Face model to MLX:")
        print("="*50)
        print("If you have a specific model you want to use, convert it:")
        print("  mlx_lm.convert --model <hf_model_id> --quantize")
        print("\nExample:")
        print("  mlx_lm.convert --model microsoft/Phi-3.5-mini-instruct --quantize")

if __name__ == "__main__":
    main()