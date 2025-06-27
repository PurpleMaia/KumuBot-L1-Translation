# Fine-Tuning with MLX‑LM

This guide explains how to fine‑tune a language model with the [MLX‑LM](https://github.com/ml-explore/mlx-lm) library using the Hawaiian→English pairs in this repository.

## Background

The benchmarking workflow measures translation quality by comparing candidate model outputs against the reference English column in `data/dataset.csv`. The script `benchmarking/semantic_similarity.py` computes embeddings for each translation and then calculates cosine similarity with the reference. The higher the similarity, the closer the candidate is to the reference.

For fine‑tuning we will use the same Hawaiian and English pairs located in `finetuning/finetuning_dataset.csv`.

> **Note**: For detailed experimental results and proven configurations, see [MLX_FINETUNING_NOTES.md](MLX_FINETUNING_NOTES.md).

## Preparing the Data

1. Convert the CSV to the JSONL format expected by MLX‑LM. A helper script `finetuning/convert_to_jsonl.py` reads `finetuning_dataset.csv` and produces `hawaiian_english_training.jsonl`:

   ```bash
   python finetuning/convert_to_jsonl.py
   ```

   Each line in the resulting file has a `messages` list with a system prompt, a user message containing the Hawaiian text, and the assistant response containing the reference translation.

2. Prepare the data for MLX‑LM by splitting it into train/validation/test sets. The script `finetuning/prepare_mlx_data.py` reads `hawaiian_english_training.jsonl` and creates the required files:

   ```bash
   cd finetuning/
   python prepare_mlx_data.py
   ```

   This creates:

   - `train.jsonl` (80% of the data)
   - `valid.jsonl` (10% of the data)
   - `test.jsonl` (10% of the data)

3. The JSONL files are now ready for MLX‑LM training. The `--data` parameter should point to the `finetuning/` directory containing these files.

   **Memory considerations**: If you encounter OOM errors with `--batch-size=2`, use `--batch-size=1 --grad-checkpoint` instead (proven to work with ~100GB RAM).

## Running LoRA Fine-Tuning

The MLX‑LM package ships a command `mlx_lm.lora` that performs LoRA or QLoRA fine‑tuning. A minimal command to fine‑tune a base model is:

```bash
mlx_lm.lora \
  --model <path_to_model_or_repo> \
  --train \
  --data finetuning/ \
  --iters 600 \
  --batch-size=2
```

**Recommended settings based on extensive testing:**

```bash
# For large datasets (2000+ examples) with memory constraints
mlx_lm.lora \
  --model mlx-community/gemma-3-4b-it-4bit \
  --train \
  --data finetuning/ \
  --iters 2000 \
  --batch-size 1 \
  --grad-checkpoint \
  --steps-per-eval 200 \
  --save-every 200  # Important for finding best checkpoint
```

Replace `<path_to_model_or_repo>` with the Hugging Face model name or a local path. When the model is quantized MLX‑LM automatically switches to QLoRA. The learned adapters are saved in the `adapters/` directory by default; you can change this with `--adapter-path`.

Common options:

- `--wandb <project>` – log metrics to Weights & Biases.
- `--fine-tune-type full` – train the entire model instead of using LoRA adapters.
- `--mask-prompt` – ignore prompt tokens when computing loss for chat datasets.

For more details see `mlx_lm.lora --help` or the [LoRA documentation](https://github.com/ml-explore/mlx-lm/blob/main/mlx_lm/LORA.md).

## Evaluating and Using the Model

After training finishes you can evaluate perplexity with:

```bash
mlx_lm.lora \
  --model <path_to_model_or_repo> \
  --adapter-path adapters/ \
  --data finetuning/ \
  --test
```

To generate translations with the fine‑tuned model:

```bash
mlx_lm.generate \
  --model <path_to_model_or_repo> \
  --adapter-path adapters/ \
  --prompt "<Hawaiian sentence>"
```

If you wish to fuse the adapters with the base model, run:

```bash
mlx_lm.fuse \
  --model <path_to_model_or_repo> \
  --adapter-path adapters/ \
  --save-path fused_model/
```

The fused model is placed in `fused_model/` and can optionally be uploaded to the Hugging Face Hub.

**Tip**: If you saved checkpoints during training, test them to find the best one. In our experiments, iteration 1800 outperformed the final iteration 2000.

## Troubleshooting

### Model Loading Errors

If you encounter errors like `Exception: data did not match any variant of untagged enum ModelWrapper` when using models from LM Studio, this is likely due to tokenizer incompatibility.

**Why this happens:**

- LM Studio may modify model files for its own optimizations
- These modifications can make tokenizer files incompatible with MLX‑LM
- MLX‑LM expects models in their original Hugging Face format

**Solutions:**

1. **Download models using huggingface-cli instead of LM Studio:**

   ```bash
   # Install huggingface-cli if needed
   pip install huggingface-hub

   # Download an MLX-compatible model
   huggingface-cli download mlx-community/Llama-3.2-1B-Instruct-4bit --local-dir ./models/llama-3.2-1b
   ```

## Proven Results

Based on extensive experimentation with Hawaiian-English translation:
- **Best model**: `mlx-community/gemma-3-4b-it-4bit` with 2,831 training pairs
- **Optimal iterations**: 1800 (not more!)
- **Performance**: 0.8296 semantic similarity (3.6% improvement over base model)
- **Key settings**: `--batch-size 1 --grad-checkpoint` for memory efficiency

See [MLX_FINETUNING_NOTES.md](MLX_FINETUNING_NOTES.md) for detailed experimental results and analysis.

## References

- [LoRA Fine-Tuning with MLX‑LM](https://github.com/ml-explore/mlx-lm/blob/main/mlx_lm/LORA.md)
- [LoRA fine‑tuning example notebook](https://gist.github.com/awni/773e2a12079da40a1cbc566686c84c8f)
- “Fine‑tuning Phi models with MLX” _(Strathweb, 2025)_ for additional tips on training phi‑based models.
