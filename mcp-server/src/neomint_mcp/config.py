"""Configuration for the NeoMint MCP server.

All tunables are loaded from environment variables (with sensible defaults)
so nothing is hardcoded and .env files work out of the box.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ── Shell command allowlist ───────────────────────────────────
# Only base command names in this set may be executed by run_command.
# Arguments are allowed freely; the check is on argv[0] only.

COMMAND_ALLOWLIST: frozenset[str] = frozenset({
    # filesystem inspection
    "ls", "cat", "head", "tail", "wc", "file", "stat", "find",
    "grep", "sort", "uniq", "cut", "tr",
    # filesystem mutation
    "mkdir", "rmdir", "cp", "mv", "touch", "rm", "chmod", "chown",
    # system info
    "df", "du", "free", "uname", "whoami", "hostname",
    "date", "cal", "uptime", "ps", "top", "kill",
    # navigation / identity
    "echo", "pwd", "which",
    # packages
    "apt", "dpkg",
    # services
    "systemctl",
    # networking
    "ping", "curl", "wget",
    # dev tools
    "git", "python3", "pip",
    # text processing
    "sed", "awk",
    # archives
    "tar", "gzip", "gunzip", "zip", "unzip",
})

# ── Application registry ─────────────────────────────────────
# Friendly name → shell command used by open_application.
# This is Linux Mint / Cinnamon-centric; extend as needed.

APP_REGISTRY: dict[str, str] = {
    "firefox": "firefox",
    "chrome": "google-chrome",
    "chromium": "chromium-browser",
    "terminal": "x-terminal-emulator",
    "files": "nemo",
    "file manager": "nemo",
    "text editor": "xed",
    "calculator": "gnome-calculator",
    "spotify": "spotify",
    "vlc": "vlc",
    "gimp": "gimp",
    "libreoffice": "libreoffice",
    "writer": "libreoffice --writer",
    "calc": "libreoffice --calc",
    "impress": "libreoffice --impress",
    "settings": "cinnamon-settings",
    "system monitor": "gnome-system-monitor",
}

# ── Runtime settings ──────────────────────────────────────────

LOG_LEVEL: str = os.getenv("NEOMINT_LOG_LEVEL", "INFO")

CONFIRM_DESTRUCTIVE: bool = (
    os.getenv("NEOMINT_CONFIRM_DESTRUCTIVE", "true").lower() == "true"
)

MAX_FILE_READ_BYTES: int = int(
    os.getenv("NEOMINT_MAX_FILE_READ_BYTES", str(1024 * 1024))
)

MAX_COMMAND_TIMEOUT: int = int(
    os.getenv("NEOMINT_MAX_COMMAND_TIMEOUT", "30")
)

# Resolve the user's home directory for path validation helpers.
HOME_DIR: Path = Path.home()
