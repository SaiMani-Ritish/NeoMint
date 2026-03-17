# NeoMint Agent

Python agentic loop that orchestrates natural language intent into OS actions
via the MCP server.

> **Status:** Phase 3 — not yet implemented.

## Architecture

The agent will:

1. Accept natural language input from the overlay UI (or CLI)
2. Send it to the local Ollama model with a system prompt describing available tools
3. Parse tool-call responses from the model
4. Execute tools via the MCP server
5. Feed results back for multi-step reasoning
6. Repeat until task completion or step limit

## Tech Stack

- Python 3.11+ (raw async, no LangChain)
- Ollama REST API (`localhost:11434`)
- FastAPI wrapper for overlay UI communication
- httpx for async HTTP
