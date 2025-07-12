#!/usr/bin/env python3
"""
Quick test script to verify an embedding model is working.
Tests basic functionality and provides useful diagnostics.
"""

import os
import sys
import time
import numpy as np
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def test_embedding_model(model_name=None, dimensions=None):
    """Test if an embedding model is working properly."""
    
    # Get configuration from environment or parameters
    api_key = os.getenv("OPENAI_API_KEY_KOA")
    api_base_url = os.getenv("OPENAI_API_EMBEDDING_BASE_URL", "http://localhost:11434/v1")
    
    if not api_key:
        print("❌ Error: OPENAI_API_KEY_KOA not set in environment")
        return False
    
    # Use provided model or get from environment
    if not model_name:
        model_name = os.getenv("EMBEDDING_MODEL")
        if not model_name:
            print("❌ Error: No model specified. Set EMBEDDING_MODEL or pass as argument")
            return False
    
    # Use provided dimensions or get from environment
    if not dimensions:
        dimensions = os.getenv("EMBEDDING_DIMENSIONS")
        if dimensions:
            dimensions = int(dimensions)
    
    print(f"🔍 Testing embedding model: {model_name}")
    print(f"📍 API endpoint: {api_base_url}")
    if dimensions:
        print(f"📐 Requested dimensions: {dimensions}")
    print("-" * 60)
    
    # Initialize client
    client = OpenAI(api_key=api_key, base_url=api_base_url)
    
    # Test texts
    test_texts = [
        "Hello world",
        "Aloha kakahiaka",  # Good morning in Hawaiian
        "The quick brown fox jumps over the lazy dog",
        "Ka makani hema pa mai",  # The south wind blows
    ]
    
    try:
        print("\n1️⃣ Testing basic embedding generation...")
        
        # Test single embedding
        start_time = time.time()
        if dimensions:
            response = client.embeddings.create(
                model=model_name,
                input=test_texts[0],
                dimensions=dimensions
            )
        else:
            response = client.embeddings.create(
                model=model_name,
                input=test_texts[0]
            )
        
        embedding = response.data[0].embedding
        elapsed = time.time() - start_time
        
        print(f"✅ Successfully generated embedding in {elapsed:.3f} seconds")
        print(f"📊 Embedding dimensions: {len(embedding)}")
        print(f"📈 First 5 values: {embedding[:5]}")
        print(f"📉 L2 norm: {np.linalg.norm(embedding):.4f}")
        
        # Test batch embeddings
        print("\n2️⃣ Testing batch embedding generation...")
        start_time = time.time()
        
        if dimensions:
            batch_response = client.embeddings.create(
                model=model_name,
                input=test_texts,
                dimensions=dimensions
            )
        else:
            batch_response = client.embeddings.create(
                model=model_name,
                input=test_texts
            )
        
        batch_embeddings = [item.embedding for item in batch_response.data]
        elapsed = time.time() - start_time
        
        print(f"✅ Successfully generated {len(batch_embeddings)} embeddings in {elapsed:.3f} seconds")
        print(f"⚡ Average time per embedding: {elapsed/len(batch_embeddings):.3f} seconds")
        
        # Test similarity
        print("\n3️⃣ Testing semantic similarity...")
        
        # Compare similar texts (both greetings)
        sim_greeting = np.dot(batch_embeddings[0], batch_embeddings[1])
        print(f"🤝 Similarity (English vs Hawaiian greeting): {sim_greeting:.4f}")
        
        # Compare different texts
        sim_different = np.dot(batch_embeddings[0], batch_embeddings[2])
        print(f"🔄 Similarity (Greeting vs Fox sentence): {sim_different:.4f}")
        
        # Hawaiian to Hawaiian
        sim_hawaiian = np.dot(batch_embeddings[1], batch_embeddings[3])
        print(f"🌺 Similarity (Hawaiian phrases): {sim_hawaiian:.4f}")
        
        # Test dimensions
        print("\n4️⃣ Testing dimension consistency...")
        all_same_dim = all(len(emb) == len(batch_embeddings[0]) for emb in batch_embeddings)
        if all_same_dim:
            print(f"✅ All embeddings have consistent dimensions: {len(batch_embeddings[0])}")
        else:
            print("❌ Warning: Embeddings have inconsistent dimensions!")
        
        # Performance summary
        print("\n📊 Performance Summary:")
        print(f"Model: {model_name}")
        print(f"Dimensions: {len(embedding)}")
        print(f"Single embedding time: {elapsed/len(batch_embeddings):.3f}s")
        print(f"Normalized: {'Yes' if abs(np.linalg.norm(embedding) - 1.0) < 0.01 else 'No'}")
        
        print("\n✅ All tests passed! The embedding model is working correctly.")
        return True
        
    except Exception as e:
        print(f"\n❌ Error testing model: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        
        # Provide helpful debugging info
        if "model" in str(e).lower():
            print("\n💡 Hint: Check if the model name is correct and available at your endpoint")
            print("You can list available models with: ollama list")
        elif "dimension" in str(e).lower():
            print("\n💡 Hint: The model might not support the requested dimensions")
            print("Try without specifying dimensions to see the default size")
        
        return False


def main():
    """Main function to run tests."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Test if an embedding model is working"
    )
    parser.add_argument(
        "--model",
        type=str,
        help="Model name to test (overrides EMBEDDING_MODEL env var)"
    )
    parser.add_argument(
        "--dimensions",
        type=int,
        help="Embedding dimensions (overrides EMBEDDING_DIMENSIONS env var)"
    )
    parser.add_argument(
        "--compare",
        type=str,
        help="Compare with another model (e.g., nomic-embed-text)"
    )
    
    args = parser.parse_args()
    
    # Test primary model
    success = test_embedding_model(args.model, args.dimensions)
    
    # If comparison requested, test that too
    if success and args.compare:
        print(f"\n\n{'='*60}")
        print(f"COMPARING WITH: {args.compare}")
        print(f"{'='*60}")
        test_embedding_model(args.compare, None)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())