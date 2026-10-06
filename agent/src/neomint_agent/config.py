"""Configuration for the NeoMint agent runtime.

All tunables are loaded from environment variables (with sensible defaults)
so nothing is hardcoded and .env files work out of the box.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ── Ollama model settings ────────────────────────────────────

OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "neomint-planner")

# ── Agent loop limits ────────────────────────────────────────

MAX_ACTIONS_PER_PLAN: int = int(os.getenv("NEOMINT_MAX_ACTIONS_PER_PLAN", "5"))
MAX_LOOP_STEPS: int = int(os.getenv("NEOMINT_MAX_LOOP_STEPS", "3"))
MODEL_TIMEOUT_SECONDS: int = int(os.getenv("NEOMINT_MODEL_TIMEOUT_SECONDS", "60"))
TOOL_TIMEOUT_SECONDS: int = int(os.getenv("NEOMINT_TOOL_TIMEOUT_SECONDS", "30"))

# ── Filesystem scopes ────────────────────────────────────────
# Comma-separated list of allowed filesystem roots.
# Tools accessing paths outside these roots are rejected.

_default_fs_roots = "~/Documents,~/Downloads,~/Desktop,~/Pictures"
ALLOWED_FS_ROOTS: list[Path] = [
    Path(root.strip()).expanduser().resolve()
    for root in os.getenv("NEOMINT_ALLOWED_FS_ROOTS", _default_fs_roots).split(",")
    if root.strip()
]

# ── Audit log ─────────────────────────────────────────────────

AUDIT_LOG_PATH: Path = Path(
    os.getenv(
        "NEOMINT_AUDIT_LOG_PATH",
        str(Path.home() / ".local" / "share" / "neomint" / "audit.jsonl"),
    )
)

# ── API server ────────────────────────────────────────────────

AGENT_HOST: str = os.getenv("NEOMINT_AGENT_HOST", "127.0.0.1")
AGENT_PORT: int = int(os.getenv("NEOMINT_AGENT_PORT", "8420"))

# ── Logging ───────────────────────────────────────────────────

LOG_LEVEL: str = os.getenv("NEOMINT_LOG_LEVEL", "INFO")
