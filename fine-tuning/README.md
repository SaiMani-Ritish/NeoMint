# NeoMint Fine-Tuning

LoRA fine-tuning pipeline for creating the NeoMint-3B model using Unsloth.

> **Status:** Phase 2 — not yet implemented.

## Plan

- Google Colab notebook (`train.ipynb`) for LoRA fine-tuning of Qwen2.5-3B-Instruct
- GGUF Q4_K_M export for Ollama deployment
- Dataset quality checker script (duplicates, format errors, label leakage)
- Ollama `Modelfile` for loading the fine-tuned model
