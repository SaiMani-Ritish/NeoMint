"""Shell tool: run_command with allowlist enforcement."""

from __future__ import annotations

import asyncio
import shlex

from neomint_mcp.config import COMMAND_ALLOWLIST, MAX_COMMAND_TIMEOUT
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
    cmd = cmd.strip()
    if not cmd:
        return ToolResponse.fail("Empty command")

    try:
        tokens = shlex.split(cmd)
    except ValueError as exc:
        return ToolResponse.fail(f"Invalid shell syntax: {exc}")

    base_cmd = tokens[0].split("/")[-1]

    if base_cmd not in COMMAND_ALLOWLIST:
        return ToolResponse.fail(
            f"Command '{base_cmd}' is not in the allowlist. "
            f"Allowed commands: {', '.join(sorted(COMMAND_ALLOWLIST))}"
        )

    try:
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(), timeout=MAX_COMMAND_TIMEOUT
        )

        return ToolResponse.ok({
            "stdout": stdout_bytes.decode("utf-8", errors="replace"),
            "stderr": stderr_bytes.decode("utf-8", errors="replace"),
            "returncode": proc.returncode,
        })
    except asyncio.TimeoutError:
        proc.kill()  # type: ignore[union-attr]
        return ToolResponse.fail(
            f"Command timed out after {MAX_COMMAND_TIMEOUT} seconds"
        )
    except OSError as exc:
        return ToolResponse.fail(f"Failed to execute command: {exc}")
