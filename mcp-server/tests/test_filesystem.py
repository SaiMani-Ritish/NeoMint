"""Tests for filesystem tools: list_files, read_file, write_file."""

from __future__ import annotations

from pathlib import Path

import pytest

from neomint_mcp.tools.filesystem import list_files, read_file, write_file


# ── list_files ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_files_returns_entries(nested_dir: Path) -> None:
    resp = await list_files(str(nested_dir))
    assert resp.success is True
    names = {e["name"] for e in resp.result}
    assert "file_a.txt" in names
    assert "file_b.py" in names
    assert "subdir" in names


@pytest.mark.asyncio
async def test_list_files_entry_types(nested_dir: Path) -> None:
    resp = await list_files(str(nested_dir))
    by_name = {e["name"]: e["type"] for e in resp.result}
    assert by_name["subdir"] == "directory"
    assert by_name["file_a.txt"] == "file"


@pytest.mark.asyncio
async def test_list_files_nonexistent(tmp_dir: Path) -> None:
    resp = await list_files(str(tmp_dir / "no_such_dir"))
    assert resp.success is False
    assert "does not exist" in resp.error


@pytest.mark.asyncio
async def test_list_files_on_file(sample_file: Path) -> None:
    resp = await list_files(str(sample_file))
    assert resp.success is False
    assert "not a directory" in resp.error


@pytest.mark.asyncio
async def test_list_files_empty_dir(tmp_dir: Path) -> None:
    empty = tmp_dir / "empty"
    empty.mkdir()
    resp = await list_files(str(empty))
    assert resp.success is True
    assert resp.result == []


# ── read_file ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_read_file_success(sample_file: Path) -> None:
    resp = await read_file(str(sample_file))
    assert resp.success is True
    assert resp.result == "Hello, NeoMint!\n"


@pytest.mark.asyncio
async def test_read_file_nonexistent(tmp_dir: Path) -> None:
    resp = await read_file(str(tmp_dir / "ghost.txt"))
    assert resp.success is False
    assert "does not exist" in resp.error


@pytest.mark.asyncio
async def test_read_file_on_directory(tmp_dir: Path) -> None:
    resp = await read_file(str(tmp_dir))
    assert resp.success is False
    assert "not a file" in resp.error


@pytest.mark.asyncio
async def test_read_file_too_large(tmp_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    big = tmp_dir / "big.txt"
    big.write_text("x" * 100, encoding="utf-8")
    monkeypatch.setattr("neomint_mcp.tools.filesystem.MAX_FILE_READ_BYTES", 50)
    resp = await read_file(str(big))
    assert resp.success is False
    assert "too large" in resp.error.lower()


@pytest.mark.asyncio
async def test_read_file_binary(tmp_dir: Path) -> None:
    binf = tmp_dir / "binary.bin"
    binf.write_bytes(b"\x80\x81\x82\xff\xfe")
    resp = await read_file(str(binf))
    # May succeed (lossy decode) or fail; the important thing is no crash
    assert isinstance(resp.success, bool)


# ── write_file ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_write_file_creates_new(tmp_dir: Path) -> None:
    target = tmp_dir / "new.txt"
    resp = await write_file(str(target), "hello world")
    assert resp.success is True
    assert target.read_text(encoding="utf-8") == "hello world"


@pytest.mark.asyncio
async def test_write_file_overwrites_existing(sample_file: Path) -> None:
    resp = await write_file(str(sample_file), "overwritten")
    assert resp.success is True
    assert sample_file.read_text(encoding="utf-8") == "overwritten"


@pytest.mark.asyncio
async def test_write_file_creates_parent_dirs(tmp_dir: Path) -> None:
    deep = tmp_dir / "a" / "b" / "c" / "file.txt"
    resp = await write_file(str(deep), "deep write")
    assert resp.success is True
    assert deep.read_text(encoding="utf-8") == "deep write"


@pytest.mark.asyncio
async def test_write_file_empty_content(tmp_dir: Path) -> None:
    target = tmp_dir / "empty.txt"
    resp = await write_file(str(target), "")
    assert resp.success is True
    assert target.read_text(encoding="utf-8") == ""
