"""Application launcher tool: open_application."""

from __future__ import annotations

import asyncio
import subprocess

from neomint_mcp.config import APP_REGISTRY
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
    normalized = app_name.strip().lower()
    shell_cmd = APP_REGISTRY.get(normalized)

    if shell_cmd is None:
        known = ", ".join(sorted(APP_REGISTRY.keys()))
        return ToolResponse.fail(
            f"Unknown application '{app_name}'. Known applications: {known}"
        )

    try:
        await asyncio.to_thread(
            subprocess.Popen,
            shell_cmd,
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return ToolResponse.ok(f"Launched '{app_name}' via: {shell_cmd}")
    except OSError as exc:
        return ToolResponse.fail(f"Failed to launch '{app_name}': {exc}")
