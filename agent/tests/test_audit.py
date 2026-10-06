"""Tests for neomint_agent.audit — JSONL audit logger."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from neomint_agent.audit import AuditLogger


@pytest.fixture
def audit_log(tmp_path: Path) -> AuditLogger:
    """Create an AuditLogger writing to a temp directory."""
    log_path = tmp_path / "test_audit.jsonl"
    return AuditLogger(log_path=log_path)


class TestAuditLogger:
    def test_log_creates_file(self, audit_log: AuditLogger):
        audit_log.log("session_start", message="Test session")
        assert audit_log.log_path.exists()

    def test_log_appends_json_lines(self, audit_log: AuditLogger):
        audit_log.log("session_start", message="Start")
        audit_log.log("plan_generated", request="Find PDFs", plan_hash="abc123")
        audit_log.log("session_end", message="End")

        lines = audit_log.log_path.read_text().strip().split("\n")
        assert len(lines) == 3

        for line in lines:
            event = json.loads(line)
            assert "timestamp" in event
            assert "event" in event

    def test_log_includes_all_fields(self, audit_log: AuditLogger):
        event = audit_log.log(
            "plan_generated",
            request="List files",
            plan_hash="abc123",
            actions=[{"tool": "files.list_directory"}],
            message="Plan created",
            duration_ms=42.5,
            metadata={"model": "neomint-planner"},
        )

        assert event["event"] == "plan_generated"
        assert event["request"] == "List files"
        assert event["plan_hash"] == "abc123"
        assert event["actions"] == [{"tool": "files.list_directory"}]
        assert event["message"] == "Plan created"
        assert event["duration_ms"] == 42.5
        assert event["metadata"]["model"] == "neomint-planner"

    def test_log_omits_empty_fields(self, audit_log: AuditLogger):
        event = audit_log.log("session_start")
        assert "request" not in event
        assert "plan_hash" not in event
        assert "actions" not in event

    def test_read_recent(self, audit_log: AuditLogger):
        for i in range(10):
            audit_log.log("test_event", message=f"Event {i}")

        recent = audit_log.read_recent(5)
        assert len(recent) == 5
        # Most recent first
        assert recent[0]["message"] == "Event 9"
        assert recent[4]["message"] == "Event 5"

    def test_read_recent_empty_log(self, audit_log: AuditLogger):
        recent = audit_log.read_recent()
        assert recent == []

    def test_clear(self, audit_log: AuditLogger):
        audit_log.log("test_event", message="Something")
        assert audit_log.log_path.exists()

        audit_log.clear()
        assert not audit_log.log_path.exists()

    def test_clear_nonexistent(self, audit_log: AuditLogger):
        # Should not raise
        audit_log.clear()

    def test_creates_parent_directory(self, tmp_path: Path):
        log_path = tmp_path / "nested" / "dirs" / "audit.jsonl"
        logger = AuditLogger(log_path=log_path)
        logger.log("test", message="Works")
        assert log_path.exists()
