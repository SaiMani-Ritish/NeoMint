# NeoMint Evaluation Suite

Benchmark suite measuring task success rate, latency, and safety across
20 standardized OS tasks in 4 categories.

> **Status:** Phase 5 — not yet implemented.

## Metrics

- `task_success_rate` — fraction of tasks completed correctly
- `avg_steps_to_completion` — mean number of agent loop iterations
- `avg_latency_ms` — end-to-end response time
- `safety_violations` — count of attempts to bypass command allowlist

## Comparisons

1. Fine-tuned NeoMint-3B
2. Base Qwen2.5-3B-Instruct (no fine-tuning)
3. Manual baseline (user typing shell commands directly)
