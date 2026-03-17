"""Tests for application launcher tool: open_application."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from neomint_mcp.tools.applications import open_application


@pytest.mark.asyncio
async def test_unknown_app_returns_failure() -> None:
    resp = await open_application("definitely_not_an_app")
    assert resp.success is False
    assert "Unknown application" in resp.error
    assert "definitely_not_an_app" in resp.error


@pytest.mark.asyncio
async def test_unknown_app_lists_known() -> None:
    resp = await open_application("no_such_app")
    assert resp.success is False
    assert "firefox" in resp.error


@pytest.mark.asyncio
async def test_known_app_launches() -> None:
    with patch("neomint_mcp.tools.applications.subprocess.Popen") as mock_popen:
        mock_popen.return_value = MagicMock()
        resp = await open_application("firefox")
        assert resp.success is True
        assert "firefox" in resp.result.lower()
        mock_popen.assert_called_once()


@pytest.mark.asyncio
async def test_case_insensitive_lookup() -> None:
    with patch("neomint_mcp.tools.applications.subprocess.Popen") as mock_popen:
        mock_popen.return_value = MagicMock()
        resp = await open_application("  Firefox  ")
        assert resp.success is True


@pytest.mark.asyncio
async def test_launch_failure_returns_error() -> None:
    with patch(
        "neomint_mcp.tools.applications.subprocess.Popen",
        side_effect=OSError("spawn failed"),
    ):
        resp = await open_application("firefox")
        assert resp.success is False
        assert "Failed to launch" in resp.error


@pytest.mark.asyncio
async def test_multiple_known_apps() -> None:
    apps_to_test = ["terminal", "files", "calculator"]
    for app_name in apps_to_test:
        with patch("neomint_mcp.tools.applications.subprocess.Popen") as mock_popen:
            mock_popen.return_value = MagicMock()
            resp = await open_application(app_name)
            assert resp.success is True, f"Failed to launch {app_name}"
