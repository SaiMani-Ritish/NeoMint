"""Tests for shell tool: run_command."""

from __future__ import annotations

import sys

import pytest

from neomint_mcp.tools.shell import run_command


@pytest.mark.asyncio
async def test_run_allowed_command() -> None:
    cmd = "echo hello" if sys.platform != "win32" else "echo hello"
    resp = await run_command(cmd)
    assert resp.success is True
    assert "hello" in resp.result["stdout"]
    assert resp.result["returncode"] == 0


@pytest.mark.asyncio
async def test_run_disallowed_command() -> None:
    resp = await run_command("reboot")
    assert resp.success is False
    assert "not in the allowlist" in resp.error


@pytest.mark.asyncio
async def test_run_empty_command() -> None:
    resp = await run_command("")
    assert resp.success is False
    assert "Empty command" in resp.error


@pytest.mark.asyncio
async def test_run_whitespace_only() -> None:
    resp = await run_command("   ")
    assert resp.success is False
    assert "Empty command" in resp.error


@pytest.mark.asyncio
async def test_run_command_with_args() -> None:
    resp = await run_command("echo foo bar baz")
    assert resp.success is True
    assert "foo bar baz" in resp.result["stdout"]


@pytest.mark.asyncio
async def test_run_command_stderr() -> None:
    resp = await run_command("ls /nonexistent_path_xyz")
    assert resp.success is True
    assert resp.result["returncode"] != 0


@pytest.mark.asyncio
async def test_run_command_invalid_syntax() -> None:
    resp = await run_command("echo 'unterminated")
    # shlex will raise on unmatched quotes
    assert resp.success is False
    assert "syntax" in resp.error.lower() or "no closing" in resp.error.lower()


@pytest.mark.asyncio
async def test_run_command_full_path_disallowed() -> None:
    resp = await run_command("/usr/bin/dangerous_program --delete-all")
    assert resp.success is False
    assert "not in the allowlist" in resp.error


@pytest.mark.asyncio
async def test_run_whoami() -> None:
    resp = await run_command("whoami")
    assert resp.success is True
    assert len(resp.result["stdout"].strip()) > 0


@pytest.mark.asyncio
async def test_run_command_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("neomint_mcp.tools.shell.MAX_COMMAND_TIMEOUT", 1)
    # Use ping with a long count — available cross-platform and in the allowlist
    if sys.platform == "win32":
        resp = await run_command("ping -n 20 127.0.0.1")
    else:
        resp = await run_command("ping -c 20 127.0.0.1")
    assert resp.success is False
    assert "timed out" in resp.error.lower()
