"""Filesystem tools: list_files, read_file, write_file."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from neomint_mcp.config import MAX_FILE_READ_BYTES
from neomint_mcp.models import ToolResponse


async def list_files(path: str) -> ToolResponse:
    """List contents of a directory.

    Args:
        path: Absolute or relative path to the directory.

    Returns:
        ToolResponse with a list of entry names on success.
    """
    try:
        target = Path(path).expanduser().resolve()
        if not target.exists():
            return ToolResponse.fail(f"Path does not exist: {target}")
        if not target.is_dir():
            return ToolResponse.fail(f"Path is not a directory: {target}")

        entries = await asyncio.to_thread(_list_dir, target)
        return ToolResponse.ok(entries)
    except PermissionError:
        return ToolResponse.fail(f"Permission denied: {path}")
    except OSError as exc:
        return ToolResponse.fail(f"OS error listing '{path}': {exc}")


def _list_dir(target: Path) -> list[dict[str, str]]:
    """Synchronous helper — called via ``asyncio.to_thread``."""
    results: list[dict[str, str]] = []
    for entry in sorted(target.iterdir()):
        kind = "directory" if entry.is_dir() else "file"
        results.append({"name": entry.name, "type": kind})
    return results


async def read_file(path: str) -> ToolResponse:
    """Read text content of a file.

    Args:
        path: Absolute or relative path to the file.

    Returns:
        ToolResponse with the file's text content on success.
    """
    try:
        target = Path(path).expanduser().resolve()
        if not target.exists():
            return ToolResponse.fail(f"File does not exist: {target}")
        if not target.is_file():
            return ToolResponse.fail(f"Path is not a file: {target}")

        size = target.stat().st_size
        if size > MAX_FILE_READ_BYTES:
            return ToolResponse.fail(
                f"File too large ({size} bytes); limit is {MAX_FILE_READ_BYTES} bytes"
            )

        content = await asyncio.to_thread(target.read_text, "utf-8")
        return ToolResponse.ok(content)
    except PermissionError:
        return ToolResponse.fail(f"Permission denied: {path}")
    except UnicodeDecodeError:
        return ToolResponse.fail(f"File is not valid UTF-8 text: {path}")
    except OSError as exc:
        return ToolResponse.fail(f"OS error reading '{path}': {exc}")


async def write_file(path: str, content: str) -> ToolResponse:
    """Write or overwrite a file with the given content.

    Creates parent directories if they do not exist.

    Args:
        path: Absolute or relative path to the file.
        content: Text content to write.

    Returns:
        ToolResponse confirming the write on success.
    """
    try:
        target = Path(path).expanduser().resolve()
        target.parent.mkdir(parents=True, exist_ok=True)

        await asyncio.to_thread(target.write_text, content, "utf-8")
        return ToolResponse.ok(f"Wrote {len(content)} bytes to {target}")
    except PermissionError:
        return ToolResponse.fail(f"Permission denied: {path}")
    except OSError as exc:
        return ToolResponse.fail(f"OS error writing '{path}': {exc}")
