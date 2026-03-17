"""Tests for clipboard tools: get_clipboard, set_clipboard.

These tests mock the subprocess calls so they work on any platform
(xclip/xsel are Linux-only).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from neomint_mcp.tools.clipboard import get_clipboard, set_clipboard


def _mock_backend(name: str = "xclip"):
    """Patch _clipboard_backend to return a specific tool name."""
    return patch("neomint_mcp.tools.clipboard._clipboard_backend", return_value=name)


def _mock_process(stdout: bytes = b"", stderr: bytes = b"", returncode: int = 0):
    """Create a mock async subprocess."""
    proc = AsyncMock()
    proc.communicate = AsyncMock(return_value=(stdout, stderr))
    proc.returncode = returncode
    return proc


# ── get_clipboard ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_clipboard_no_backend() -> None:
    with patch("neomint_mcp.tools.clipboard._clipboard_backend", return_value=None):
        resp = await get_clipboard()
    assert resp.success is False
    assert "Install xclip" in resp.error


@pytest.mark.asyncio
async def test_get_clipboard_success() -> None:
    proc = _mock_process(stdout=b"copied text")
    with (
        _mock_backend("xclip"),
        patch("asyncio.create_subprocess_exec", return_value=proc),
    ):
        resp = await get_clipboard()
    assert resp.success is True
    assert resp.result == "copied text"


@pytest.mark.asyncio
async def test_get_clipboard_xsel_backend() -> None:
    proc = _mock_process(stdout=b"xsel content")
    with (
        _mock_backend("xsel"),
        patch("asyncio.create_subprocess_exec", return_value=proc),
    ):
        resp = await get_clipboard()
    assert resp.success is True
    assert resp.result == "xsel content"


@pytest.mark.asyncio
async def test_get_clipboard_failure() -> None:
    proc = _mock_process(stderr=b"Error: no display", returncode=1)
    with (
        _mock_backend("xclip"),
        patch("asyncio.create_subprocess_exec", return_value=proc),
    ):
        resp = await get_clipboard()
    assert resp.success is False
    assert "Clipboard read failed" in resp.error


# ── set_clipboard ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_set_clipboard_no_backend() -> None:
    with patch("neomint_mcp.tools.clipboard._clipboard_backend", return_value=None):
        resp = await set_clipboard("text")
    assert resp.success is False
    assert "Install xclip" in resp.error


@pytest.mark.asyncio
async def test_set_clipboard_success() -> None:
    proc = _mock_process()
    with (
        _mock_backend("xclip"),
        patch("asyncio.create_subprocess_exec", return_value=proc),
    ):
        resp = await set_clipboard("hello clipboard")
    assert resp.success is True
    assert "15 chars" in resp.result


@pytest.mark.asyncio
async def test_set_clipboard_xsel_backend() -> None:
    proc = _mock_process()
    with (
        _mock_backend("xsel"),
        patch("asyncio.create_subprocess_exec", return_value=proc),
    ):
        resp = await set_clipboard("xsel test")
    assert resp.success is True


@pytest.mark.asyncio
async def test_set_clipboard_failure() -> None:
    proc = _mock_process(stderr=b"write error", returncode=1)
    with (
        _mock_backend("xclip"),
        patch("asyncio.create_subprocess_exec", return_value=proc),
    ):
        resp = await set_clipboard("fail text")
    assert resp.success is False
    assert "Clipboard write failed" in resp.error


@pytest.mark.asyncio
async def test_set_clipboard_empty_text() -> None:
    proc = _mock_process()
    with (
        _mock_backend("xclip"),
        patch("asyncio.create_subprocess_exec", return_value=proc),
    ):
        resp = await set_clipboard("")
    assert resp.success is True
    assert "0 chars" in resp.result
