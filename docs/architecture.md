# NeoMint Architecture

> System architecture and component design. For the development roadmap, see [roadmap.md](roadmap.md).

## System overview

NeoMint is a local-first, AI-native desktop shell for Linux Mint. It converts user intent into transparent, policy-checked local actions through a text-first overlay, small local models, constrained capabilities, explicit previews, confirmations, local audit logs, and resource budgets.

## Four-layer stack

```text
┌──────────────────────────────────────────────────┐
│              Overlay UI  (Tauri v2)              │
│        Floating input bar + response stream      │
├──────────────────────────────────────────────────┤
│             Agentic Loop  (Python)               │
│   Intent → Plan → Tool Call → Observe → Loop     │
├──────────────────────────────────────────────────┤
│              MCP Server  (Python)                │
│ list_files│run_command│open_app│clipboard│…      │
├──────────────────────────────────────────────────┤
│         Ollama + NeoMint-3B  (Local LLM)         │
├──────────────────────────────────────────────────┤
│              Linux Mint  (Base OS)               │
└──────────────────────────────────────────────────┘
```

### Layer responsibilities

| Layer | Component | Responsibility |
|---|---|---|
| **5 — Overlay UI** | `overlay-ui/` (Tauri v2, Rust + React + TypeScript) | User-facing floating window; prompt input, plan display, approval buttons, activity feed, audit viewer |
| **4 — Agent runtime** | `agent/` (Python, async) | Receives user intent; invokes local model to produce structured plans; validates plans against policy; orchestrates tool calls |
| **3 — MCP Server** | `mcp-server/` (Python, FastMCP) | Exposes typed OS-level tools over the MCP protocol; each tool has a typed contract and structured response |
| **2 — Local LLM** | Ollama + NeoMint-3B (LoRA fine-tuned Qwen2.5-3B, GGUF Q4_K_M) | Generates structured candidate plans; runs entirely on-device; no network calls |
| **1 — Base OS** | Linux Mint (Debian-based, Cinnamon DE) | Target operating system; provides the desktop, filesystem, and system services |

## Data flow

```text
User types intent
  │
  ▼
Overlay UI ──HTTP/SSE──► Agent Runtime
                              │
                              ├── Sends prompt to Ollama (localhost:11434)
                              │   └── Model returns structured JSON plan
                              │
                              ├── Validates plan:
                              │   ├── Schema validation
                              │   ├── Tool allowlist check
                              │   ├── Argument/scope validation
                              │   ├── Risk classification (deterministic)
                              │   └── Reject if malformed or out-of-scope
                              │
                              ├── Returns plan preview to UI
                              │   └── User approves / edits / cancels
                              │
                              ├── Executes approved tools via MCP Server
                              │   └── MCP Server calls OS primitives
                              │
                              ├── Observes result
                              │   └── Optionally plans next safe step
                              │
                              └── Writes audit event to local JSONL log
```

## Component map

### `mcp-server/`

The MCP server is the **capability layer**. It exposes OS-level tools with typed contracts.

```text
mcp-server/
├── src/neomint_mcp/
│   ├── models.py          # ToolResponse dataclass (ok/fail factory)
│   ├── config.py          # Allowlists, app registry, runtime settings
│   ├── server.py          # FastMCP entry point, tool registration
│   ├── session.py         # Session 0: typed plans, audit events, deterministic planner
│   └── tools/
│       ├── filesystem.py  # list_files, read_file, write_file
│       ├── shell.py       # run_command (allowlist-validated)
│       ├── applications.py# open_application (registry-validated)
│       └── clipboard.py   # get_clipboard, set_clipboard
├── tests/                 # pytest suite for every tool
├── cli.py                 # CLI entry point (session command)
└── pyproject.toml         # Package config, dependencies
```

**Key design decisions:**
- Tool logic is separated from MCP wiring — tools are pure async functions returning `ToolResponse`.
- `ToolResponse` is a frozen dataclass with `.ok()` and `.fail()` factories, serializing to `{"success": bool, "result": any, "error": str|null}`.
- Shell commands are validated against a fixed allowlist (`config.COMMAND_ALLOWLIST`) before execution.
- Application launches resolve through a fixed registry (`config.APP_REGISTRY`).

### `agent/`

The agent runtime is the **planning and orchestration layer**. It bridges the local model and the capability layer.

> Phase 3 — not yet implemented. Currently, `session.py` contains a deterministic phrase-matching planner as a stand-in.

**Planned architecture:**
- Raw async Python with `httpx` for Ollama REST API calls (no LangChain).
- Structured output parser that enforces the `ActionPlan` schema.
- Deterministic policy engine that classifies risk independent of model output.
- Approval service with plan-hash binding.
- Loop limits and resource budgets.

### `overlay-ui/`

The overlay UI is the **interaction surface**. It is a keyboard-first, floating desktop overlay.

> Phase 4 — not yet implemented. See [ux-spec.md](ux-spec.md) for the design specification.

**Planned technology:** Tauri v2 (Rust backend, React + TypeScript frontend).

### `eval/`

The evaluation suite provides **measurable quality and safety assurance**.

> Phase 5 — not yet implemented. See [evaluation.md](evaluation.md) for the specification.

### `fine-tuning/`

LoRA fine-tuning scripts for creating the NeoMint-3B model from Qwen2.5-3B-Instruct using Unsloth on Google Colab. Exports to GGUF Q4_K_M for Ollama.

### `datasets/`

OS task instruction datasets (raw and processed JSONL) used for fine-tuning.

## Technology choices

| Layer | Technology | Rationale |
|---|---|---|
| Base OS | Linux Mint (Debian-based) | Target platform; stable, widely used, Cinnamon DE |
| LLM Runtime | Ollama (local, CPU inference) | Simple local model serving; REST API; no cloud dependency |
| Model | NeoMint-3B (LoRA fine-tuned Qwen2.5-3B, GGUF Q4_K_M) | Small enough for CPU; fine-tuned for tool-call generation |
| MCP Server | Python 3.11+, `mcp` SDK, asyncio | Official MCP SDK; async for non-blocking tool execution |
| Agent Loop | Raw async Python, httpx | Minimal dependencies; direct Ollama REST calls; transparent |
| Overlay UI | Tauri v2 (Rust + React + TypeScript) | Lightweight native desktop app; floating window support |
| Fine-Tuning | Unsloth, LoRA, GGUF quantization | Efficient fine-tuning on free Colab T4; compact export |

### Why raw async Python over LangChain

- The agentic loop (prompt → parse → execute → observe) is a ~100-line async loop, not a complex chain.
- LangChain adds ~50MB of transitive dependencies for abstractions that are not used.
- Direct Ollama REST calls are simpler to debug and profile.
- Fewer dependencies = faster install, easier to package, fewer breaking changes.
