# Fine-Tuning with Unsloth.ai

This guide explains how to fine-tune an open‑source model using the [Unsloth.ai](https://docs.unsloth.ai/) library and the Hawaiian–English pairs that are provided in this repository. It assumes you have already translated the dataset and reviewed the benchmarking scripts. The `benchmarking/semantic_similarity.py` script computes sentence‑embedding cosine similarity between each model output and the reference English text, as shown below:

```python
# snippet from benchmarking/semantic_similarity.py
for i, (model_translation, ref_embedding) in enumerate(tqdm(zip(df[model], reference_embeddings))):
    if pd.isna(model_translation) or model_translation == "" or ref_embedding is None:
        similarities.append(np.nan)
    else:
        model_embedding = get_embedding(model_translation)
        similarity = cosine_similarity(model_embedding, ref_embedding)
        similarities.append(similarity)
```

The reference translations are stored in `data/dataset.csv` and a smaller subset for training is under `finetuning/hawaiian_english_training.jsonl`.

## 1. Install Dependencies

Create a virtual environment and install the dependencies, including `unsloth`:

```bash
uv venv  # or python -m venv .venv
source .venv/bin/activate
uv pip install -r requirements.txt
pip install unsloth  # install the fine-tuning library
```

## 2. Prepare the Dataset

`finetuning/hawaiian_english_training.jsonl` already contains the pairs in ChatML format. Each line looks like:

```json
{"messages": [{"role": "system", "content": "You are a helpful assistant that translates Hawaiian text to English."}, {"role": "user", "content": "<Hawaiian>"}, {"role": "assistant", "content": "<English>"}]}
```

If you add more examples, keep this structure so they can be loaded directly with `datasets.load_dataset`.

## 3. Loading a Base Model

Unsloth provides the `FastLanguageModel` helper. Pick an open‑source checkpoint that fits your GPU memory. The snippet below uses the Llama‑3 8B 4‑bit model (see the [Unsloth docs](https://docs.unsloth.ai/) for other options):

```python
from unsloth import FastLanguageModel
from trl import SFTTrainer
from datasets import load_dataset

model_name = "unsloth/llama-3-8b-Instruct-bnb-4bit"
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name=model_name,
    max_seq_length=2048,
)
```

## 4. Configure LoRA Training

Wrap the model with `get_peft_model` to apply LoRA adapters. A common configuration is:

```python
model = FastLanguageModel.get_peft_model(
    model,
    r=16,
    lora_alpha=16,
    lora_dropout=0.05,
)
```

Enable gradient checkpointing for memory efficiency:

```python
FastLanguageModel.for_inference(model, dtype=None, use_gradient_checkpointing=True)
```

## 5. Format the Dataset

Load the JSONL file and turn each example into a single text string for SFT (Supervised Fine-Tuning). The `formatting_func` builds a ChatML conversation from the messages:

```python
def formatting_func(example):
    messages = example["messages"]
    text = ""
    for m in messages:
        role = m["role"]
        content = m["content"]
        if role == "system":
            text += f"<|im_start|>system\n{content}<|im_end|>\n"
        elif role == "user":
            text += f"<|im_start|>user\n{content}<|im_end|>\n"
        else:  # assistant
            text += f"<|im_start|>assistant\n{content}<|im_end|>"
    return {"text": text}

raw_ds = load_dataset("json", data_files="finetuning/hawaiian_english_training.jsonl")
dataset = raw_ds.map(formatting_func)
```

## 6. Train with `SFTTrainer`

Instantiate the trainer and run fine‑tuning:

```python
trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=dataset["train"],
    dataset_text_field="text",
    max_seq_length=2048,
    packing=True,
)

trainer.train()
trainer.save_model("unsloth_finetuned_hawaiian")
```

The resulting adapter weights will be saved in `unsloth_finetuned_hawaiian/`.

## 7. Inference

Load the fine‑tuned model for inference:

```python
from unsloth import FastLanguageModel
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="unsloth/llama-3-8b-Instruct-bnb-4bit",
    max_seq_length=2048,
)
model.load_adapter("unsloth_finetuned_hawaiian")
FastLanguageModel.for_inference(model)

prompt = "He wahi ʻāpana ʻōlelo Hawaiʻi"
print(tokenizer.decode(model.generate(**tokenizer(prompt, return_tensors="pt")).tolist()[0]))
```

This workflow allows you to build a customized translator using the reference pairs already in this repository. Refer to [Unsloth.ai documentation](https://docs.unsloth.ai/) for advanced tuning options such as quantization levels, optimizer settings, and multi‑GPU training.
