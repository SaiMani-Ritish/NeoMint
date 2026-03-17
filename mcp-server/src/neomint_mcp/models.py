"""Shared response models for NeoMint MCP tools."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ToolResponse:
    """Standardized response envelope returned by every MCP tool.

    Schema:
        { "success": bool, "result": <any>, "error": <str | null> }
    """

    success: bool
    result: Any = None
    error: str | None = None

    def to_json(self) -> str:
        """Serialize to a JSON string."""
        return json.dumps(
            {"success": self.success, "result": self.result, "error": self.error},
            ensure_ascii=False,
        )

    @staticmethod
    def ok(result: Any) -> ToolResponse:
        """Create a successful response."""
        return ToolResponse(success=True, result=result)

    @staticmethod
    def fail(error: str) -> ToolResponse:
        """Create a failure response."""
        return ToolResponse(success=False, error=error)
