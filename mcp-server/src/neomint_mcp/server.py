"""NeoMint MCP server — main entry point.

Registers every OS-level tool with the FastMCP framework and exposes
them over the MCP protocol (stdio transport by default).

Usage:
    neomint-mcp          # via console_scripts entry point
    python -m neomint_mcp.server   # direct invocation
"""

from __future__ import annotations

import logging

from mcp.server.fastmcp import FastMCP

from neomint_mcp import __version__
from neomint_mcp.config import LOG_LEVEL
from neomint_mcp.tools import applications, clipboard, filesystem, shell

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("neomint-mcp")

mcp = FastMCP(
    "neomint-mcp",
    version=__version__,
)


# ── Filesystem tools ─────────────────────────────────────────


@mcp.tool()
async def list_files(path: str) -> str:
    """List contents of a directory at the given path."""
    return (await filesystem.list_files(path)).to_json()


@mcp.tool()
async def read_file(path: str) -> str:
    """Read a file's text content."""
    return (await filesystem.read_file(path)).to_json()


@mcp.tool()
async def write_file(path: str, content: str) -> str:
    """Write or overwrite a file with the given content."""
    return (await filesystem.write_file(path, content)).to_json()


# ── Shell tools ──────────────────────────────────────────────


@mcp.tool()
async def run_command(cmd: str) -> str:
    """Run a shell command (validated against an allowlist) and return stdout/stderr."""
    return (await shell.run_command(cmd)).to_json()


# ── Application tools ────────────────────────────────────────


@mcp.tool()
async def open_application(app_name: str) -> str:
    """Launch a GUI application by its friendly name."""
    return (await applications.open_application(app_name)).to_json()


# ── Clipboard tools ──────────────────────────────────────────


@mcp.tool()
async def get_clipboard() -> str:
    """Return the current clipboard text."""
    return (await clipboard.get_clipboard()).to_json()


@mcp.tool()
async def set_clipboard(text: str) -> str:
    """Set the clipboard to the given text."""
    return (await clipboard.set_clipboard(text)).to_json()


# ── Entry point ──────────────────────────────────────────────


def main() -> None:
    """Run the MCP server."""
    logger.info("Starting NeoMint MCP server v%s", __version__)
    mcp.run()


if __name__ == "__main__":
    main()
