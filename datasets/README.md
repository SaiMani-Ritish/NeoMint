# NeoMint Datasets

OS task instruction datasets for fine-tuning and evaluation.

> **Status:** Phase 2 — complete.

## Files

| File | Description |
|------|-------------|
| `neomint_train.jsonl` | Training dataset (174 examples) |
| `quality_check.py` | Dataset quality validation script |

## Dataset Format

JSONL with the Alpaca instruction format:

```json
{"instruction": "User's natural language request", "input": "Optional context (e.g., previous tool results)", "output": "Model's response with tool_call blocks"}
```

### Tool Call Format

When the model needs to interact with the OS, its output includes a fenced tool_call block:

````
I'll list your home directory contents.

```tool_call
{"tool": "list_files", "args": {"path": "~"}}
```
````

## Categories

The dataset covers 8 categories:

| Category | Count | Description |
|----------|-------|-------------|
| Shell commands | 58 | General command execution (find, grep, tar, etc.) |
| File inspection | 24 | Listing directory contents |
| File write | 23 | Creating and editing files |
| System info | 23 | Disk, memory, CPU, uptime, kernel queries |
| App launch | 15 | Opening GUI applications by name |
| File read | 14 | Reading file contents |
| Multi-step | 9 | Chained operations (read → process → write) |
| Clipboard | 8 | Get/set clipboard operations |

Additionally, 17 entries are clarification/conversation examples (ambiguous requests, help prompts, greetings).

## Quality Checker

Run the quality checker to validate the dataset:

```bash
# Check for issues
python quality_check.py neomint_train.jsonl

# Fix issues and output a cleaned file
python quality_check.py neomint_train.jsonl --fix --output neomint_cleaned.jsonl
```

### What it checks

- JSON parse errors (malformed lines)
- Missing required fields (instruction, input, output)
- Empty fields that should have content
- Exact duplicate entries
- Near-duplicate instructions (label leakage)
- Well-formed tool_call JSON blocks
- Known tool names in tool_call blocks

### Statistics output

```
Total entries:            174
Entries with tool calls:  157
Clarification/convo:      17
With context input:       19
Avg instruction length:   40.2 chars
Avg output length:        153.4 chars
```
