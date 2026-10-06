"""JSONL audit logger for NeoMint.

Every agent interaction produces a structured audit event that is
appended to a local JSONL file. Events are human-readable,
inspectable, and deletable by the user. No audit data is transmitted
over any network.

Event types:
    - session_start / session_end
    - plan_generated
    - plan_approved / plan_denied
    - plan_rejected_by_policy
    - action_executed / action_failed
    - clarification / refusal
    - error
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from neomint_agent.config import AUDIT_LOG_PATH

logger = logging.getLogger("neomint-agent.audit")


class AuditLogger:
    """Append-only JSONL audit logger.

    Args:
        log_path: Path to the JSONL audit file. Defaults to config value.
    """

    def __init__(self, log_path: Path | None = None) -> None:
        self.log_path = log_path or AUDIT_LOG_PATH
        self._ensure_directory()

    def _ensure_directory(self) -> None:
        """Create the parent directory if it doesn't exist."""
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log(
        self,
        event_type: str,
        *,
        request: str = "",
        plan_hash: str = "",
        actions: list[dict[str, Any]] | None = None,
        results: list[dict[str, Any]] | None = None,
        violations: list[str] | None = None,
        message: str = "",
        duration_ms: float = 0.0,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Append an audit event to the log file.

        Args:
            event_type: One of the defined event types.
            request: The original user request.
            plan_hash: Hash of the validated plan (for approval binding).
            actions: List of action dicts (tool, arguments, explanation).
            results: List of tool execution results.
            violations: List of policy violations (if any).
            message: Human-readable event message.
            duration_ms: Total duration of the event in milliseconds.
            metadata: Additional metadata (e.g., model name, eval count).

        Returns:
            The audit event dict that was logged.
        """
        event: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "event": event_type,
        }

        if request:
            event["request"] = request
        if plan_hash:
            event["plan_hash"] = plan_hash
        if actions:
            event["actions"] = actions
        if results:
            event["results"] = results
        if violations:
            event["violations"] = violations
        if message:
            event["message"] = message
        if duration_ms > 0:
            event["duration_ms"] = round(duration_ms, 2)
        if metadata:
            event["metadata"] = metadata

        self._append(event)
        return event

    def _append(self, event: dict[str, Any]) -> None:
        """Write a single event line to the JSONL file."""
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")
        except OSError as exc:
            logger.error("Failed to write audit event: %s", exc)

    def read_recent(self, count: int = 50) -> list[dict[str, Any]]:
        """Read the most recent audit events.

        Args:
            count: Maximum number of events to return.

        Returns:
            List of event dicts, most recent first.
        """
        if not self.log_path.exists():
            return []

        events: list[dict[str, Any]] = []
        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            events.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
        except OSError as exc:
            logger.error("Failed to read audit log: %s", exc)
            return []

        return events[-count:][::-1]

    def clear(self) -> None:
        """Delete the audit log file. User-initiated only."""
        try:
            if self.log_path.exists():
                self.log_path.unlink()
                logger.info("Audit log cleared: %s", self.log_path)
        except OSError as exc:
            logger.error("Failed to clear audit log: %s", exc)
