"""Shell tool: run_command with allowlist enforcement."""

from __future__ import annotations

from neomint_mcp.models import ToolResponse


async def run_command(cmd: str) -> ToolResponse:
    """Run a shell command and return its stdout/stderr.

    The command's base name (argv[0]) is validated against
    ``config.COMMAND_ALLOWLIST`` before execution.  Commands
    not on the allowlist are rejected immediately.

    Args:
        cmd: The full shell command string to execute.

    Returns:
        ToolResponse with ``{"stdout": ..., "stderr": ..., "returncode": ...}``
        on success, or an error message if the command is disallowed or fails.
    """
    raise NotImplementedError
