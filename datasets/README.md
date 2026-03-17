# NeoMint Datasets

OS task instruction datasets for fine-tuning and evaluation.

> **Status:** Phase 2 — not yet built.

## Format

JSONL with the following schema:

```json
{"instruction": "...", "input": "...", "output": "..."}
```

## Categories

- File operations (create, read, move, search)
- Application launching (by name, with arguments)
- System information queries (disk, memory, processes)
- Multi-step tasks (chained operations)
- Clarification dialogues (ambiguous requests)
