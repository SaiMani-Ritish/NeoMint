"""Clipboard tools: get_clipboard, set_clipboard.

Uses ``xclip`` under the hood (installed via install.sh).
Falls back to ``xsel`` if ``xclip`` is unavailable.
"""

from __future__ import annotations

import asyncio
import shutil

from neomint_mcp.models import ToolResponse


def _clipboard_backend() -> str | None:
    """Return the name of an available clipboard CLI tool, or None."""
    if shutil.which("xclip"):
        return "xclip"
    if shutil.which("xsel"):
        return "xsel"
    return None


async def get_clipboard() -> ToolResponse:
    """Return the current X11 clipboard text.

    Returns:
        ToolResponse with the clipboard string on success.
    """
    backend = _clipboard_backend()
    if backend is None:
        return ToolResponse.fail(
            "No clipboard tool found. Install xclip or xsel."
        )

    if backend == "xclip":
        cmd = ["xclip", "-selection", "clipboard", "-o"]
    else:
        cmd = ["xsel", "--clipboard", "--output"]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            err = stderr.decode("utf-8", errors="replace").strip()
            return ToolResponse.fail(f"Clipboard read failed: {err}")

        return ToolResponse.ok(stdout.decode("utf-8", errors="replace"))
    except OSError as exc:
        return ToolResponse.fail(f"Clipboard error: {exc}")


async def set_clipboard(text: str) -> ToolResponse:
    """Set the X11 clipboard to the given text.

    Args:
        text: The string to place on the clipboard.

    Returns:
        ToolResponse confirming the clipboard was set.
    """
    backend = _clipboard_backend()
    if backend is None:
        return ToolResponse.fail(
            "No clipboard tool found. Install xclip or xsel."
        )

    if backend == "xclip":
        cmd = ["xclip", "-selection", "clipboard"]
    else:
        cmd = ["xsel", "--clipboard", "--input"]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate(input=text.encode("utf-8"))

        if proc.returncode != 0:
            err = stderr.decode("utf-8", errors="replace").strip()
            return ToolResponse.fail(f"Clipboard write failed: {err}")

        return ToolResponse.ok(f"Clipboard set ({len(text)} chars)")
    except OSError as exc:
        return ToolResponse.fail(f"Clipboard error: {exc}")
