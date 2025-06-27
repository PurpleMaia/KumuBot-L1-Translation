# MLX Fine-Tuning Notes

This document contains experimental findings and recommendations from fine-tuning Hawaiian-English translation models using MLX-LM.

## Experimental Setup

### Hardware
- **Machine**: Mac M1 Ultra with 128GB RAM
- **Available RAM**: ~98GB (30GB system usage)
- **Model**: `mlx-community/gemma-3-4b-it-4bit` (4-bit quantized Gemma 3B)

### Datasets
1. **Small dataset**: 20 Hawaiian-English pairs (original Koa dataset)
2. **Large dataset**: 2,831 Hawaiian-English pairs (expanded Fornander dataset)

## Experimental Results

### Experiment 1: Small Dataset (20 pairs)

**Command:**
```bash
mlx_lm.lora --model mlx-community/gemma-3-4b-it-4bit --train --data finetuning --iters 200 --batch-size 2
```

**Results:**
- **Peak memory**: 7.532 GB
- **Speed**: ~0.6 it/s, ~420 tokens/s
- **Total tokens trained**: 137,675
- **Training loss**: 4.551 → 0.904 (excellent convergence)
- **Validation loss**: 4.874 → 4.495 (minimal improvement, suggesting overfitting)

### Experiment 2: Large Dataset (2,831 pairs)

**Initial attempt with batch-size=2 resulted in OOM errors**

**Successful command:**
```bash
mlx_lm.lora --model mlx-community/gemma-3-4b-it-4bit --train --data finetuning --iters 200 --batch-size 1 --grad-checkpoint
```

**Results:**
- **Peak memory**: 6.101 GB (lower than small dataset!)
- **Speed**: ~1.0 it/s, ~350 tokens/s
- **Total tokens trained**: 73,501
- **Training loss**: 5.052 → 2.857
- **Validation loss**: 5.776 → 2.910 (much better generalization)

## Key Findings

### 1. Memory Management Success
- Gradient checkpointing (`--grad-checkpoint`) + batch_size=1 successfully avoided OOM
- Peak memory reduced from 7.5GB to 6.1GB while training on 140x more data
- The memory optimization actually improved iteration speed

### 2. Unexpected Performance Parity
Both models (20 pairs vs 2,831 pairs) performed similarly on unseen test data. This suggests:

- **Insufficient training iterations**: Large dataset only saw 73,501 tokens vs 137,675 for small dataset
- **Pre-existing knowledge**: Gemma-3 may already have Hawaiian language knowledge from pretraining
- **Quality over quantity**: The 20 high-quality examples might be sufficient to "activate" the model's capabilities
- **Underfitting**: Each example in the large dataset was seen <1 time on average

## Recommendations for Improved Performance

### 1. Increase Training Duration (Most Important)
```bash
mlx_lm.lora \
  --model mlx-community/gemma-3-4b-it-4bit \
  --train \
  --data finetuning \
  --iters 2000 \
  --batch-size 1 \
  --grad-checkpoint \
  --steps-per-eval 200 \
  --save-every 400
```
**Rationale**: Ensure each example is seen multiple times during training.

### 2. Experiment with Higher Learning Rates
```bash
mlx_lm.lora \
  --model mlx-community/gemma-3-4b-it-4bit \
  --train \
  --data finetuning \
  --iters 1000 \
  --batch-size 1 \
  --grad-checkpoint \
  --learning-rate 5e-05  # 5x higher than default
```
**Rationale**: More aggressive updates might help the model learn dataset-specific patterns.

### 3. Increase LoRA Rank for More Capacity
```bash
mlx_lm.lora \
  --model mlx-community/gemma-3-4b-it-4bit \
  --train \
  --data finetuning \
  --iters 1000 \
  --batch-size 1 \
  --grad-checkpoint \
  --lora-parameters.rank 16  # Default is 8
```
**Rationale**: Higher rank allows more parameters to be trained, potentially capturing more nuanced patterns.

### 4. Use Gradient Accumulation for Effective Larger Batches
```bash
mlx_lm.lora \
  --model mlx-community/gemma-3-4b-it-4bit \
  --train \
  --data finetuning \
  --iters 1000 \
  --batch-size 1 \
  --grad-accumulation-steps 4 \
  --grad-checkpoint
```
**Rationale**: Simulates batch_size=4 while maintaining low memory usage.

## Memory Guidelines

### For ~100GB Available RAM
- Use batch_size=2 without gradient checkpointing for faster training
- Or batch_size=4 with gradient checkpointing for better convergence

### For ~50GB Available RAM
- Stick with batch_size=1 and gradient checkpointing
- Consider reducing max_seq_length if needed: `--max-seq-length 1024`

### For <32GB Available RAM
- Use a smaller model like `mlx-community/gemma-2-2b-it-4bit`
- Or further reduce sequence length: `--max-seq-length 512`

## Evaluation Recommendations

1. **Track more metrics**: Use the benchmarking pipeline to evaluate BLEU scores and semantic similarity
2. **Test on diverse examples**: Include formal, colloquial, and domain-specific Hawaiian text
3. **Compare checkpoints**: Save adapters every 200-400 iterations to find optimal stopping point
4. **A/B testing**: Run the same prompt through base model vs fine-tuned model to see differences

## Next Steps

1. Run extended training (2000+ iterations) on the large dataset
2. Experiment with learning rate scheduling
3. Consider mixing datasets: Use high-quality examples more frequently
4. Test different base models (Llama-3, Phi-3) for comparison
5. Implement early stopping based on validation loss

## Useful Commands Reference

### Testing the Fine-tuned Model
```bash
# Generate with adapters
mlx_lm.generate \
  --model mlx-community/gemma-3-4b-it-4bit \
  --adapter-path adapters/ \
  --prompt "Translate to English: [Hawaiian text]" \
  --max-tokens 100

# Evaluate perplexity
mlx_lm.lora \
  --model mlx-community/gemma-3-4b-it-4bit \
  --adapter-path adapters/ \
  --data finetuning/ \
  --test
```

### Fusing and Exporting
```bash
# Fuse adapters into base model
mlx_lm.fuse \
  --model mlx-community/gemma-3-4b-it-4bit \
  --adapter-path adapters/ \
  --save-path fused_model/

# Upload to Hugging Face (optional)
mlx_lm.fuse \
  --model mlx-community/gemma-3-4b-it-4bit \
  --adapter-path adapters/ \
  --upload-name "username/hawaiian-gemma-3b"
```