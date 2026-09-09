# NeoMint Fine-Tuning

QLoRA fine-tuning pipeline for creating the **NeoMint-Planner-1.7B** model.

> **Status:** Phase 2 — in progress (Session 0: action schema and taxonomy complete).

## Overview

This directory contains the full pipeline for fine-tuning **Qwen/Qwen3-1.7B** into a narrow, structured local desktop action planner using QLoRA. The model produces typed JSON plans, clarification questions, or refusals — never free-text tool calls.

For design rationale and model strategy, see [docs/model.md](../docs/model.md).

## Directory Structure

```
fine-tuning/
├── schemas/
│   ├── action-plan.schema.json     # Model output contract (plan/clarification/refusal)
│   └── tool-manifest.json          # 12-tool typed vocabulary with argument schemas
├── data/
│   ├── train.jsonl                 # Training dataset (structured trajectories)
│   ├── validation.jsonl            # Held-out validation set
│   └── test.jsonl                  # Held-out test set (never used for training)
├── configs/
│   ├── qwen3-1.7b-neomint-qlora.yaml    # Primary QLoRA training config
│   └── smollm2-1.7b-baseline.yaml       # Control baseline config
├── notebooks/
│   ├── 01_dataset_validation.ipynb       # Validate and inspect training data
│   ├── 02_qwen3_1_7b_qlora.ipynb         # QLoRA training on Colab T4
│   ├── 03_evaluate_planner.ipynb         # Offline structured-output evaluation
│   ├── 04_export_quantize.ipynb          # Merge adapter, export to GGUF
│   └── legacy_train_qwen25.ipynb         # [Historical] Old Qwen2.5-3B LoRA notebook
├── scripts/
│   ├── validate_dataset.py               # Schema-aware dataset validator
│   └── convert_legacy.py                 # Convert old Alpaca format to new format
├── outputs/
│   └── README.md                         # Training output directory
└── README.md                             # This file
```

## Model Strategy

| Role | Model | License |
|------|-------|---------|
| **Production planner base** | Qwen/Qwen3-1.7B | Apache 2.0 |
| **Product adapter** | NeoMint-Planner-1.7B | Apache 2.0 |
| **Control baseline** | HuggingFaceTB/SmolLM2-1.7B-Instruct | Apache 2.0 |
| **Quality benchmark** | Qwen/Qwen3-4B | Apache 2.0 |
| **Safety authority** | NeoMint policy engine (deterministic) | — |

## Model Output Contract

The model returns **only one of three outcomes**:

1. **Plan** — typed actions with tool name, arguments, and explanation
2. **Clarification** — question + reason when intent is ambiguous
3. **Refusal** — decline message when request is unsupported/unsafe

The model must NOT produce: `requires_confirmation`, `permission`, `risk`, `execute`. Those are owned by the deterministic policy engine.

See [schemas/action-plan.schema.json](schemas/action-plan.schema.json) for the full schema.

## Tool Vocabulary

12 typed tools for the initial planner (see [schemas/tool-manifest.json](schemas/tool-manifest.json)):

| Tool | Description |
|------|-------------|
| `files.search` | Search files within allowed roots |
| `files.list_directory` | List directory contents |
| `files.open` | Open file with default application |
| `files.move_to_trash` | Move to Trash (recoverable) |
| `applications.list` | List installed GUI applications |
| `applications.launch` | Launch application by name |
| `clipboard.read` | Read clipboard text |
| `clipboard.write` | Write text to clipboard |
| `system.status` | System status (disk, memory, CPU, uptime, OS) |
| `system.list_processes` | List running processes |
| `notes.create_draft` | Create a note file |
| `settings.show` | Open system settings |

## Dataset Format

JSONL with structured trajectories (not Alpaca format):

```json
{
  "id": "files_search_recent_pdfs_001",
  "messages": [
    {"role": "system", "content": "You are NeoMint Planner..."},
    {"role": "user", "content": "Find PDFs modified this week."}
  ],
  "tool_manifest": ["files.search", "files.list_directory", ...],
  "target": {
    "kind": "plan",
    "user_facing_summary": "I'll search for recent PDFs.",
    "actions": [
      {
        "tool": "files.search",
        "arguments": {"roots": ["~/Documents"], "name_glob": "*.pdf", "max_results": 20},
        "explanation": "Searches Documents for recently modified PDF files."
      }
    ]
  },
  "labels": {"category": "read_only", "expected_confirmation": false}
}
```

## Validation

```bash
cd fine-tuning
python scripts/validate_dataset.py data/train.jsonl data/validation.jsonl data/test.jsonl
```

## Training Configuration

| Parameter | Value | Rationale |
|-----------|-------|-----------| 
| Base model | Qwen/Qwen3-1.7B | Small, Apache 2.0, tool-calling oriented, 32K context |
| Training method | QLoRA (4-bit quantized base) | Fits on Colab T4; base weights frozen |
| LoRA rank | 32 | Good balance of capacity vs. VRAM |
| LoRA alpha | 64 | Standard 2x rank scaling |
| Target modules | q,k,v,o_proj + gate,up,down_proj | Full attention + MLP coverage |
| Epochs | 3 | Adjustable based on dataset size |
| Effective batch size | 8 | 2 per-device × 4 gradient accumulation |
| Learning rate | 2e-4 | Standard for LoRA fine-tuning |
| Quantization (export) | Q4_K_M | Best quality/size tradeoff for CPU inference |

## Loading into Ollama

After training and export:

```bash
# Copy the GGUF to the repo root (next to neomint.modelfile)
cp outputs/neomint-planner-1.7b-Q4_K_M.gguf /path/to/NeoMint/

# Create the Ollama model
cd /path/to/NeoMint/
ollama create neomint-planner -f neomint.modelfile

# Test it
ollama run neomint-planner
```

## Output

- **QLoRA adapter**: `outputs/neomint-planner-1.7b-lora/` (~50-100 MB)
- **GGUF model**: `outputs/neomint-planner-1.7b-Q4_K_M.gguf` (~1.0-1.2 GB)
- **Training summary**: `outputs/training_summary.json` (metrics for project documentation)
- **Evaluation report**: `outputs/evaluation_report.json` (held-out test results)
