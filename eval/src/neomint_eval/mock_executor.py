"""Mock tool executor for the NeoMint evaluation suite.

Provides a mock tool executor that never touches the real system.
Records all tool calls for assertion and returns configurable results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MockToolCall:
    """A recorded tool call."""

    tool: str
    arguments: dict[str, Any]


@dataclass
class MockToolResult:
    """A mock result to return for a tool call."""

    success: bool = True
    result: Any = None
    error: str | None = None
    duration_ms: float = 5.0


class MockToolExecutor:
    """Mock tool executor for evaluation — never touches the real system.

    Records all tool calls and returns configurable mock results.
    Can simulate failures and timeouts for recovery testing.

    Usage:
        executor = MockToolExecutor()
        executor.set_result("files.list_directory", MockToolResult(
            success=True,
            result={"files": [{"name": "test.pdf", "type": "file"}]},
        ))
        result = await executor.execute("files.list_directory", {"path": "~/Documents"})
    """

    def __init__(self) -> None:
        self.calls: list[MockToolCall] = []
        self._results: dict[str, MockToolResult] = {}
        self._default_result = MockToolResult(
            success=True,
            result={"mock": True, "message": "Mock execution successful"},
        )
        self.is_available = True

    def set_result(self, tool: str, result: MockToolResult) -> None:
        """Configure the result to return for a specific tool."""
        self._results[tool] = result

    def set_default_result(self, result: MockToolResult) -> None:
        """Configure the default result for unconfigured tools."""
        self._default_result = result

    def set_failure(self, tool: str, error: str = "Mock failure") -> None:
        """Configure a tool to always fail."""
        self._results[tool] = MockToolResult(success=False, error=error)

    async def execute(self, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute a mock tool call. Records the call and returns configured result.

        Args:
            tool: Tool name.
            arguments: Tool arguments.

        Returns:
            Dict with success, result/error, and duration_ms fields.
        """
        self.calls.append(MockToolCall(tool=tool, arguments=arguments))

        mock_result = self._results.get(tool, self._default_result)

        return {
            "tool": tool,
            "success": mock_result.success,
            "result": mock_result.result,
            "error": mock_result.error,
            "duration_ms": mock_result.duration_ms,
        }

    def reset(self) -> None:
        """Clear all recorded calls and configured results."""
        self.calls.clear()
        self._results.clear()

    @property
    def call_count(self) -> int:
        return len(self.calls)

    def get_calls_for(self, tool: str) -> list[MockToolCall]:
        """Get all recorded calls for a specific tool."""
        return [c for c in self.calls if c.tool == tool]

    def was_called(self, tool: str) -> bool:
        """Check if a specific tool was called."""
        return any(c.tool == tool for c in self.calls)
