"""Application launcher tool: open_application."""

from __future__ import annotations

from neomint_mcp.models import ToolResponse


async def open_application(app_name: str) -> ToolResponse:
    """Launch a GUI application by its friendly name.

    The *app_name* is looked up in ``config.APP_REGISTRY`` to resolve
    the actual shell command.  If the name is not recognised, the tool
    returns a failure response listing the known application names.

    Args:
        app_name: Human-friendly application name (e.g. "firefox", "terminal").

    Returns:
        ToolResponse confirming the application was launched, or an error
        if the name is unknown.
    """
    raise NotImplementedError
