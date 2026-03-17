"""Clipboard tools: get_clipboard, set_clipboard.

Uses ``xclip`` under the hood (installed via install.sh).
"""

from __future__ import annotations

from neomint_mcp.models import ToolResponse


async def get_clipboard() -> ToolResponse:
    """Return the current X11 clipboard text.

    Returns:
        ToolResponse with the clipboard string on success.
    """
    raise NotImplementedError


async def set_clipboard(text: str) -> ToolResponse:
    """Set the X11 clipboard to the given text.

    Args:
        text: The string to place on the clipboard.

    Returns:
        ToolResponse confirming the clipboard was set.
    """
    raise NotImplementedError
