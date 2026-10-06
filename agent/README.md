# NeoMint Agent

Python agentic loop that orchestrates natural language intent into OS actions
via the MCP server.

> **Status:** Phase 3 — implemented.

## Architecture

```
User request
  → local model produces structured candidate plan (via Ollama)
  → schema validation (Pydantic)
  → tool allowlist validation (12 typed tools)
  → argument/scope validation (filesystem roots)
  → risk classification (deterministic, not from model)
  → preview and approval gate (plan hash binding)
  → constrained execution (MCP tool dispatch)
  → result observation
  → durable JSONL audit record
```

## Components

| Module | Purpose |
|--------|---------|
| `schemas.py` | Pydantic models: Plan, Clarification, Refusal, ValidatedPlan |
| `config.py` | Environment-based configuration |
| `policy.py` | Deterministic policy engine (allowlist, scoping, risk) |
| `parser.py` | Model output parser (JSON extraction, validation) |
| `model_adapter.py` | Ollama HTTP client |
| `tool_executor.py` | MCP tool dispatcher |
| `audit.py` | JSONL audit logger |
| `loop.py` | Core agent loop (orchestration) |
| `api.py` | FastAPI + WebSocket server |
| `cli.py` | Interactive CLI for testing |

## Quick Start

```bash
# Create virtual environment and install
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Run the API server (for overlay UI)
python -m neomint_agent

# Or run the interactive CLI
python -m neomint_agent.cli

# Run tests
pytest -v
```

## Tech Stack

- Python 3.11+ (raw async, no LangChain)
- Ollama REST API (`localhost:11434`)
- FastAPI + WebSocket for overlay UI communication
- httpx for async HTTP
- Pydantic v2 for schema validation
