# NeoMint project setup and MCP server
_Exported on 3/16/2026 at 23:34:56 PDT from Cursor (2.6.19)_

---

**User**

You are a senior full-stack systems engineer and ML engineer helping me build 
an LLM-integrated Linux OS interaction layer — a project I'm calling "NeoMint". The goal: take Linux Mint as the base OS, add a locally-running 
fine-tuned small LLM (via Ollama), connect it to a custom MCP server that exposes 
OS-level tools, and wrap it in a floating natural language input overlay — so the 
primary way a user interacts with the OS is by typing intent in plain English, 
not clicking around.

This is my MSCS Capstone project. I need you to build this with me step by step, 
file by file, in a clean monorepo. Every time I say "next", move to the next phase. 
Never skip ahead. Always explain what you're building and why before writing code.

---

## TECH STACK

- Base OS: Linux Mint (Debian-based, assume it's already installed)
- LLM Runtime: Ollama (local, REST API on localhost:11434)
- Model: Qwen2.5-3B-Instruct or Phi-3-mini (GGUF Q4_K_M quantized)
- MCP Server: Python, using the official `mcp` SDK (pip install mcp)
- Agentic loop: Python orchestrator (LangChain or raw async Python — your call, 
  justify the choice)
- Overlay UI: Tauri v2 (Rust backend, React + TypeScript frontend)
- Fine-tuning: LoRA via Unsloth (to be run on Google Colab, generate the scripts)
- Evaluation: Python test suite with task completion rate, latency, and safety metrics
- Packaging: Bash install script + optional Docker dev environment

---

## MONOREPO STRUCTURE TO BUILD TOWARD

neomint-os/
├── mcp-server/          # Python MCP server exposing OS tools
├── agent/               # Python agentic loop (LLM ↔ MCP orchestrator)
├── overlay-ui/          # Tauri v2 app (floating NL input bar)
├── fine-tuning/         # LoRA fine-tuning scripts (Unsloth, Colab-ready)
├── eval/                # Evaluation suite and benchmarks
├── datasets/            # OS task instruction datasets (raw + processed)
├── docs/                # Architecture diagrams, capstone paper outline
├── install.sh           # One-shot setup script for Linux Mint
└── README.md

---

## PHASES — WE GO ONE AT A TIME

### PHASE 1 — Foundation & MCP Server skeleton (Weeks 1–3)
Goals:
- Set up the monorepo and dev environment
- Get Ollama running and confirm a base model responds
- Build the MCP server with these initial tools:
    - list_files(path): list directory contents
    - read_file(path): read a file's text content
    - write_file(path, content): write/overwrite a file
    - run_command(cmd): run a shell command, return stdout/stderr 
      (with a hardcoded allowlist for safety)
    - open_application(app_name): launch a GUI application by name
    - get_clipboard(): return current clipboard text
    - set_clipboard(text): set clipboard text
- Write a simple CLI test harness to call each tool manually
- No LLM integration yet — just the tool layer working cleanly

Constraints:
- MCP server must be async (use asyncio)
- All tools must return structured JSON responses with 
  { "success": bool, "result": any, "error": str | null }
- run_command must validate against an allowlist before executing
- Write a pytest suite for every tool

### PHASE 2 — Fine-tuning pipeline (Weeks 4–7)
Goals:
- Generate/curate a dataset of OS task instruction pairs in JSONL format:
    { "instruction": "...", "input": "...", "output": "..." }
  covering: file ops, app launching, system info queries, 
  multi-step tasks, clarification dialogues
- Write a Google Colab notebook (fine-tuning/train.ipynb) using Unsloth 
  to LoRA fine-tune Qwen2.5-3B-Instruct
- Export the fine-tuned model to GGUF Q4_K_M format
- Write instructions for loading it into Ollama as a custom modelfile
- Include a dataset quality checker script (checks for duplicates, 
  label leakage, format errors)

### PHASE 3 — Agentic loop (Weeks 8–11)
Goals:
- Build the Python orchestrator that:
    1. Takes a user's natural language input
    2. Sends it to the local Ollama model with a system prompt 
       that describes the available MCP tools
    3. Parses the model's tool-call response (handle both 
       JSON tool-call format and free-text fallback)
    4. Executes the tool via the MCP server
    5. Feeds the result back to the model for the next step
    6. Repeats until the model signals task completion 
       or hits a max-step limit
- Add safety layer: before any write_file or run_command, 
  print the action and require user confirmation (y/n) in the CLI
- Add conversation memory (sliding window, last 10 turns)
- Add a --dry-run flag that shows what the agent WOULD do without executing
- Write integration tests covering 5 end-to-end task scenarios

### PHASE 4 — Overlay UI (Weeks 12–14)
Goals:
- Build the Tauri v2 overlay app:
    - Always-on-top floating window, anchored bottom-center
    - Single text input field, clean minimal design
    - Keyboard shortcut to show/hide (e.g. Super+Space)
    - Sends user input to the Python agent via local HTTP (FastAPI wrapper)
    - Streams the agent's response tokens back and shows them above the input
    - Shows tool call activity (e.g. "Running: list_files('/home/user/docs')")
    - Light/dark mode following system theme
- Wrap the Python agent in a FastAPI server with:
    - POST /chat — send a message, get streaming SSE response
    - GET /health — liveness check
    - POST /confirm — send y/n for pending confirmations
- Write a systemd service file so the agent + UI start on login

### PHASE 5 — Evaluation suite (Weeks 15–16)
Goals:
- Build eval/benchmark.py with 20 standardized tasks across 4 categories:
    1. File operations (e.g. "find all .py files in ~/projects and list them")
    2. App control (e.g. "open Firefox and Spotify")
    3. System info (e.g. "how much disk space is free on /home?")
    4. Multi-step (e.g. "read the contents of notes.txt and save a 
       summary to summary.txt")
- Metrics: task_success_rate, avg_steps_to_completion, 
  avg_latency_ms, safety_violations
- Run the same tasks against:
    a. Your fine-tuned model
    b. The base model (no fine-tuning)
    c. Baseline: user manually typing shell commands
- Output a results JSON and a markdown report
- Write the capstone paper outline in docs/paper-outline.md 
  (abstract, intro, related work, system design, experiments, results, conclusion)

---

## CONSTRAINTS ACROSS ALL PHASES

- Python 3.11+, typed with type hints everywhere
- All secrets/paths in .env files, never hardcoded
- Every module gets a README.md explaining what it does and how to run it
- Git-committable at the end of every phase (clean, no debug prints)
- Assume the dev machine is Linux Mint with 16GB RAM, no dedicated GPU 
  (model runs CPU-only via Ollama)
- Prioritize correctness and clarity over cleverness
- If you hit an architectural decision, explain the tradeoff and 
  recommend one option before proceeding

---

## HOW TO WORK WITH ME

- Start with Phase 1
- Build one file or component at a time
- After each file, wait for me to say "next" or ask questions
- If you need to make an assumption, state it explicitly
- If something I've asked for is technically wrong or suboptimal, 
  push back and explain why before proceeding

---

## FINAL DELIVERABLE 1 — NEOMINT OS (the product)

The end product is a fully functioning, redistributable Linux-based OS layer 
called NeoMint. By the end of Phase 5, I must be able to:

- Run install.sh on a fresh Linux Mint machine and have the entire 
  NeoMint stack running within 30 minutes
- Press Super+Space anywhere on the desktop and get the NeoMint overlay
- Type a natural language instruction and have the agent execute it 
  on the real OS
- The fine-tuned model (NeoMint-3B) must be bundled or downloadable 
  via a single command in the install script

Package this as:
  neomint-os/
  ├── install.sh              # one-shot installer for Linux Mint
  ├── neomint.modelfile       # Ollama modelfile for NeoMint-3B
  ├── mcp-server/
  ├── agent/
  ├── overlay-ui/
  ├── fine-tuning/
  ├── eval/
  ├── datasets/
  ├── docs/
  └── README.md               # full user-facing setup guide

The README.md must read like a real open-source project — installation 
instructions, demo GIF placeholder, architecture overview, 
known limitations, and a roadmap section.

---

## FINAL DELIVERABLE 2 — CAPSTONE PAPER (neomint-paper.txt)

At the end of Phase 5, generate docs/neomint-paper.txt — a complete, 
submittable MSCS capstone paper in plain text format. 

The paper must include ALL of the following sections, written in full 
(no placeholders, no "insert result here" stubs — use actual numbers 
from the eval suite):

  Title: NeoMint: A Locally-Deployed Agentic LLM Interface Layer 
         for Natural Language OS Interaction
  Author:  Sai Mani Ritish
  Institution: City University of Seattle
  Program: Master of Science in Computer Science

  Sections:
  1. Abstract (250 words)
  2. Introduction
     - Problem statement: GUI-centric OS interaction as a bottleneck
     - Motivation for local, private, agentic LLM integration
     - Contributions of this work
  3. Related Work
     - Existing NL-to-shell systems (NL2Bash, ShellGPT)
     - OS agent benchmarks (OSWorld, AgentBench, ShellBench)
     - MCP protocol and tool-augmented LLMs
     - Small model fine-tuning (LoRA, QLoRA, Unsloth)
  4. System Architecture
     - Overview of the 4-layer stack (Base OS, Ollama runtime, 
       MCP server, overlay UI)
     - MCP tool design decisions and safety constraints
     - Agentic loop design (plan → tool call → observe → repeat)
     - Fine-tuning approach (dataset curation, LoRA config, 
       GGUF export)
  5. Dataset
     - Dataset composition (how many examples, what categories)
     - Collection methodology
     - Quality filtering process
     - Sample instruction-output pairs (at least 5 examples in the paper)
  6. Experiments & Results
     - Evaluation setup (20 benchmark tasks, 4 categories)
     - Results table: fine-tuned NeoMint-3B vs base model vs 
       manual baseline across all 4 metrics
     - Analysis: where did the fine-tuned model improve most? 
       Where did it still fail?
     - Latency breakdown: overlay input → agent response → 
       OS action complete
  7. Discussion
     - What worked, what didn't
     - Safety considerations (destructive command guardrails)
     - Privacy advantages of fully local deployment
     - Limitations of the current system
  8. Future Work
     - Vision model integration (screenshot understanding)
     - Voice input layer
     - Multi-agent task decomposition
     - Packaging as a full ISO (bootable NeoMint OS image)
  9. Conclusion
  10. References (minimum 15 academic/technical citations, 
      formatted in APA)

The paper must be 6,000–9,000 words. Write it as if submitting 
to a real MSCS committee. Use formal academic tone throughout. 
Every claim about system performance must be backed by a number 
from the eval suite results.

Generate this file automatically at the end of Phase 5, 
after the benchmark has run and results are available. 
Write real numbers, real analysis, real conclusions.

Start now: scaffold the monorepo structure and create the 
install.sh and the mcp-server/ skeleton. Go.

---

**Cursor**

Alright, let's build NeoMint. Before I write any code, here's what I'm doing in this first step and the key decisions I'm making:

**What we're building now:**
1. The full monorepo directory scaffold with placeholder READMEs for every module
2. `install.sh` — a production-quality one-shot installer for Linux Mint (working sections for Phase 1, stubs for future phases)
3. The `mcp-server/` skeleton — complete package structure with typed stubs for all 7 tools, a CLI test harness, and the MCP server entry point

**One architectural decision up front:** For the agent loop (Phase 3), I'm recommending **raw async Python over LangChain**. Reasons:
- The agentic loop (prompt LLM → parse tool call → execute → feed back) is a ~100-line async loop, not a complex chain
- LangChain adds ~50MB of transitive dependencies for abstractions you won't use
- Direct Ollama REST calls are simpler to debug and profile than LangChain's wrappers
- For a capstone paper, demonstrating you understand the mechanics matters more than using a framework
- Fewer dependencies = faster install, easier to package, fewer breaking changes

I'll use `httpx` for async HTTP to Ollama when we get to Phase 3. For now, Phase 1 is tool-layer only.

Let me scaffold everything.

Now the mcp-server skeleton — package config, dependencies, and the module structure.

Now the core Python modules — models, config, and tool stubs.

Now the server entry point, CLI harness, and test scaffolding.

Now let me initialize the git repo.

All 26 files staged cleanly. Let me verify the tree structure matches the spec.

Everything is scaffolded. Here's a summary of what was created and the key decisions baked in.

---

## What was built — 26 files across 8 directories

```
neomint-os/
├── .env.example              # Root config template (Ollama host, model name, log level)
├── .gitignore                # Python + Node + Rust + model files
├── README.md                 # Full open-source-style project README
├── install.sh                # One-shot Linux Mint installer (8 phases, stub-safe)
├── agent/README.md           # Phase 3 placeholder
├── overlay-ui/README.md      # Phase 4 placeholder
├── fine-tuning/README.md     # Phase 2 placeholder
├── eval/README.md            # Phase 5 placeholder
├── datasets/README.md        # Phase 2 placeholder
├── docs/README.md            # Docs index
└── mcp-server/
    ├── .env.example          # MCP-specific config (allowlist tunables, timeouts)
    ├── README.md             # Tool reference, setup, safety docs
    ├── pyproject.toml        # Package config: deps, console script, pytest/ruff/mypy
    ├── requirements.txt      # Flat deps for pip install -r
    ├── cli.py                # Manual tool test harness
    ├── src/neomint_mcp/
    │   ├── __init__.py       # Package marker + __version__
    │   ├── models.py         # ToolResponse dataclass (ok/fail factory methods)
    │   ├── config.py         # COMMAND_ALLOWLIST, APP_REGISTRY, env-loaded settings
    │   ├── server.py         # FastMCP entry point, wires all tools
    │   └── tools/
    │       ├── __init__.py
    │       ├── filesystem.py # list_files, read_file, write_file (stubs)
    │       ├── shell.py      # run_command (stub)
    │       ├── applications.py # open_application (stub)
    │       └── clipboard.py  # get_clipboard, set_clipboard (stubs)
    └── tests/
        ├── __init__.py
        └── conftest.py       # Shared fixtures (tmp_dir, sample_file, nested_dir)
```

## Key design decisions

1. **Tool logic is separated from MCP wiring.** Each `tools/*.py` module contains pure async functions returning `ToolResponse`. `server.py` is a thin layer that wraps them with `@mcp.tool()` decorators. This means the CLI and pytest can call tools directly without the MCP transport layer.

2. **`ToolResponse` is a frozen dataclass** with `.ok()` and `.fail()` factory methods, always serializing to `{"success": bool, "result": any, "error": str|null}` as specified.

3. **`config.py` loads everything from env vars** via `python-dotenv`. The command allowlist and app registry are defined as code constants (not env vars) since they're structural, not deployment-specific.

4. **`install.sh` is phase-aware.** It checks for the existence of `pyproject.toml` / `package.json` in each module directory before attempting setup. Phases that don't exist yet get a clean "Skipping" message. This means the script works today and will progressively do more as we build each phase.

5. **All tool stubs raise `NotImplementedError`.** The CLI catches this gracefully. When we implement each tool, we just replace the function body — signatures, types, and docstrings are already complete.

---

## What's next

When you say **"next"**, I'll implement `mcp-server/src/neomint_mcp/tools/filesystem.py` — the first real tool with full async file I/O, error handling, path validation, and its pytest suite. Then we'll work through `shell.py`, `applications.py`, and `clipboard.py` one at a time.

