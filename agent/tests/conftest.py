"""Shared test fixtures for the NeoMint agent test suite."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest


# ── Sample model responses ───────────────────────────────────

VALID_PLAN_JSON = json.dumps({
    "kind": "plan",
    "user_facing_summary": "List the contents of your Documents folder",
    "actions": [
        {
            "tool": "files.list_directory",
            "arguments": {"path": "~/Documents"},
            "explanation": "Lists all files and folders in ~/Documents",
        }
    ],
})

VALID_MULTI_ACTION_PLAN_JSON = json.dumps({
    "kind": "plan",
    "user_facing_summary": "Search for PDFs and open the newest one",
    "actions": [
        {
            "tool": "files.search",
            "arguments": {
                "roots": ["~/Documents", "~/Downloads"],
                "name_glob": "*.pdf",
                "max_results": 10,
            },
            "explanation": "Search for PDF files in Documents and Downloads",
        },
        {
            "tool": "files.open",
            "arguments": {"path": "~/Documents/report.pdf"},
            "explanation": "Open the newest PDF file",
        },
    ],
})

VALID_CLARIFICATION_JSON = json.dumps({
    "kind": "clarification",
    "question": "Which folder would you like me to list?",
    "reason": "The request is ambiguous — there are multiple possible locations.",
})

VALID_REFUSAL_JSON = json.dumps({
    "kind": "refusal",
    "message": "I cannot execute arbitrary shell commands. I can only use the tools available in my manifest.",
})

# Plans with policy violations
INVALID_TOOL_PLAN_JSON = json.dumps({
    "kind": "plan",
    "user_facing_summary": "Run a shell command",
    "actions": [
        {
            "tool": "shell.execute",
            "arguments": {"cmd": "rm -rf /"},
            "explanation": "Delete everything",
        }
    ],
})

OUT_OF_SCOPE_PLAN_JSON = json.dumps({
    "kind": "plan",
    "user_facing_summary": "List /etc directory",
    "actions": [
        {
            "tool": "files.list_directory",
            "arguments": {"path": "/etc"},
            "explanation": "List system configuration files",
        }
    ],
})

TOO_MANY_ACTIONS_JSON = json.dumps({
    "kind": "plan",
    "user_facing_summary": "Do many things",
    "actions": [
        {
            "tool": "files.list_directory",
            "arguments": {"path": "~/Documents"},
            "explanation": f"Action {i}",
        }
        for i in range(6)
    ],
})

DANGEROUS_ARGS_PLAN_JSON = json.dumps({
    "kind": "plan",
    "user_facing_summary": "Run sudo command",
    "actions": [
        {
            "tool": "clipboard.write",
            "arguments": {"text": "sudo rm -rf /"},
            "explanation": "Copy dangerous command",
        }
    ],
})


# ── Mock Ollama responses ────────────────────────────────────


def mock_ollama_response(text: str) -> dict[str, Any]:
    """Create a mock Ollama API response body."""
    return {
        "model": "neomint-planner",
        "response": text,
        "done": True,
        "total_duration": 500_000_000,  # 500ms in nanoseconds
        "eval_count": 100,
    }
