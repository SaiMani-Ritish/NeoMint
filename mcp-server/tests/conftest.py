"""Shared test fixtures for NeoMint MCP server tests."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture()
def tmp_dir(tmp_path: Path) -> Path:
    """Provide a clean temporary directory for filesystem tests."""
    return tmp_path


@pytest.fixture()
def sample_file(tmp_path: Path) -> Path:
    """Create a sample text file for read/write tests."""
    f = tmp_path / "sample.txt"
    f.write_text("Hello, NeoMint!\n", encoding="utf-8")
    return f


@pytest.fixture()
def nested_dir(tmp_path: Path) -> Path:
    """Create a nested directory tree for list_files tests."""
    (tmp_path / "subdir").mkdir()
    (tmp_path / "file_a.txt").write_text("a", encoding="utf-8")
    (tmp_path / "file_b.py").write_text("b", encoding="utf-8")
    (tmp_path / "subdir" / "file_c.md").write_text("c", encoding="utf-8")
    return tmp_path
