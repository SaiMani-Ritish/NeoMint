# NeoMint Fine-Tuning

LoRA fine-tuning pipeline for creating the NeoMint-3B model using Unsloth.

> **Status:** Phase 2 — complete.

## Overview

This directory contains the Google Colab notebook that fine-tunes **Qwen2.5-3B-Instruct** using LoRA (Low-Rank Adaptation) on the NeoMint OS task instruction dataset, then exports the result to GGUF format for Ollama deployment.

## Files

| File | Description |
|------|-------------|
| `train.ipynb` | Colab notebook — full training + export pipeline |

## How to Fine-Tune

### Prerequisites

- Google account with access to Colab
- GPU runtime enabled (T4 free tier is sufficient)
- The dataset file `datasets/neomint_train.jsonl` from this repo

### Steps

1. **Open the notebook** — Upload `train.ipynb` to Google Colab (or open directly from GitHub)

2. **Enable GPU runtime** — Runtime → Change runtime type → T4 GPU

3. **Upload the dataset** — When prompted, upload `datasets/neomint_train.jsonl`

4. **Run all cells** — The notebook will:
   - Install Unsloth and dependencies
   - Load Qwen2.5-3B-Instruct with 4-bit quantization
   - Apply LoRA adapters (rank 32, alpha 64)
   - Train for 3 epochs (~15-30 min on T4)
   - Test the model with sample prompts
   - Export to GGUF Q4_K_M format (~1.8 GB)

5. **Download the GGUF file** — The notebook auto-downloads the file at the end

### Loading into Ollama

After downloading the GGUF file:

```bash
# Copy the GGUF to the repo root (next to neomint.modelfile)
cp ~/Downloads/neomint-3b-unsloth-Q4_K_M.gguf /path/to/neomint-os/

# Create the Ollama model
cd /path/to/neomint-os/
ollama create neomint-3b -f neomint.modelfile

# Test it
ollama run neomint-3b
```

## Training Configuration

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Base model | Qwen2.5-3B-Instruct | Small enough for CPU inference, strong instruction following |
| LoRA rank | 32 | Good balance of capacity vs. VRAM for a 3B model |
| LoRA alpha | 64 | Standard 2x rank scaling |
| Target modules | q,k,v,o_proj + gate,up,down_proj | Full attention + MLP coverage |
| Epochs | 3 | Sufficient for 174 examples without overfitting |
| Effective batch size | 8 | 2 per-device × 4 gradient accumulation |
| Learning rate | 2e-4 | Standard for LoRA fine-tuning |
| Scheduler | Cosine | Smooth decay prevents late-training instability |
| Quantization | Q4_K_M | Best quality/size tradeoff for CPU inference |

## Output

- **LoRA adapters**: `neomint-3b-lora/` (~50-100 MB)
- **GGUF model**: `neomint-3b-unsloth-Q4_K_M.gguf` (~1.8 GB)
- **Training summary**: `training_summary.json` (metrics for the capstone paper)
