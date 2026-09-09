# NeoMint

> A local-first, AI-native desktop shell for Linux Mint. NeoMint converts user intent into transparent, policy-checked local actions through a text-first overlay, small local models, constrained capabilities, explicit previews, confirmations, local audit logs, and resource budgets.

NeoMint transforms Linux Mint into an intent-driven operating system. Instead of
navigating menus, clicking icons, and memorizing terminal commands, you press
**Super+Space** and describe what you want in plain English. A locally-running
fine-tuned language model interprets your intent and executes it — privately,
offline, on your hardware.

![NeoMint Demo](docs/demo-placeholder.gif)

---

## Architecture

```
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

## Quick Start

```bash
# Clone the repository
git clone https://github.com/SaiMani-Ritish/NeoMint.git
cd NeoMint

# Run the one-shot installer (Linux Mint / Ubuntu-based only)
chmod +x install.sh
./install.sh

# Press Super+Space anywhere on the desktop to open the NeoMint overlay
```

## Project Structure

| Directory       | Description                                       |
|-----------------|---------------------------------------------------|
| `mcp-server/`   | Python MCP server exposing OS-level tools         |
| `agent/`        | Python agentic loop (LLM ↔ MCP orchestrator)      |
| `overlay-ui/`   | Tauri v2 floating natural language input bar      |
| `fine-tuning/`  | LoRA fine-tuning scripts (Unsloth, Colab-ready)   |
| `eval/`         | Evaluation suite and benchmarks                   |
| `datasets/`     | OS task instruction datasets (raw + processed)    |
| `docs/`         | Architecture, safety model, UX spec, and project documentation |

## Requirements

- **OS:** Linux Mint 21.x+ (or any Ubuntu/Debian derivative)
- **RAM:** 16 GB minimum (model runs CPU-only)
- **Disk:** 10 GB free space
- **Python:** 3.11+
- **Network:** Internet connection for initial setup only (model download, packages)

## Development

Each component has its own README with setup instructions. For local development:

```bash
# MCP Server
cd mcp-server
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest

# Agent (Phase 3)
cd agent
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Tech Stack

| Layer          | Technology                                |
|----------------|-------------------------------------------|
| Base OS        | Linux Mint (Debian-based)                 |
| LLM Runtime    | Ollama (local, CPU inference)             |
| Model          | NeoMint-3B (LoRA fine-tuned Qwen2.5-3B)   |
| MCP Server     | Python 3.11+, `mcp` SDK, asyncio          |
| Agent Loop     | Raw async Python, httpx                   |
| Overlay UI     | Tauri v2 (Rust + React + TypeScript)      |
| Fine-Tuning    | Unsloth, LoRA, GGUF Q4_K_M quantization   |

## Known Limitations

- **CPU-only inference** — expect 2–5 second response latency per turn
- **Conservative command allowlist** — destructive commands require explicit user confirmation
- **Text-only interaction** — no vision/screenshot understanding yet
- **Single-user, single-session** — no multi-user or concurrent session support
- **Linux Mint only** — installer assumes Debian/Ubuntu package manager and Cinnamon DE

## Roadmap

- [x] Phase 2, Session 0: Typed planning, previews, confirmation, audit events
- [ ] Phase 3: Agentic loop and safety guardrails
- [ ] Phase 4: Floating overlay UI
- [ ] Phase 5: Evaluation and release readiness
- [ ] Future: Vision model, voice input, multi-agent decomposition, bootable ISO

See [docs/roadmap.md](docs/roadmap.md) for the full roadmap.

## Safety

NeoMint enforces a strict safety model: every action has a typed contract, risk classification, and audit record. State-changing actions require explicit user approval. Destructive operations are disabled by default. See [docs/safety-model.md](docs/safety-model.md) for details.

## License

MIT
