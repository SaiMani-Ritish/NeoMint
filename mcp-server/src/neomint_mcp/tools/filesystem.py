"""Filesystem tools: list_files, read_file, write_file."""

from __future__ import annotations

from neomint_mcp.models import ToolResponse


async def list_files(path: str) -> ToolResponse:
    """List contents of a directory.

    Args:
        path: Absolute or relative path to the directory.

    Returns:
        ToolResponse with a list of entry names on success.
    """
    raise NotImplementedError


async def read_file(path: str) -> ToolResponse:
    """Read text content of a file.

    Args:
        path: Absolute or relative path to the file.

    Returns:
        ToolResponse with the file's text content on success.
    """
    raise NotImplementedError


async def write_file(path: str, content: str) -> ToolResponse:
    """Write or overwrite a file with the given content.

    Args:
        path: Absolute or relative path to the file.
        content: Text content to write.

    Returns:
        ToolResponse confirming the write on success.
    """
    raise NotImplementedError
