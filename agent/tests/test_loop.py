"""Tests for neomint_agent.loop — core agent loop with mocked dependencies."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from neomint_agent.audit import AuditLogger
from neomint_agent.loop import AgentLoop
from neomint_agent.model_adapter import ModelResponse, OllamaAdapter, OllamaConnectionError
from neomint_agent.schemas import AgentResponse, ToolResult
from neomint_agent.tool_executor import ToolExecutor

# ── Inline test data ─────────────────────────────────────────

VALID_PLAN_JSON = json.dumps({
    "kind": "plan",
    "user_facing_summary": "List the contents of your Documents folder",
    "actions": [
        {
            "tool": "files.list_directory",
            "arguments": {"path": "~/Documents"},
            "explanation": "Lists all files and folders in ~/Documents",
        }
    ],
})

VALID_CLARIFICATION_JSON = json.dumps({
    "kind": "clarification",
    "question": "Which folder would you like me to list?",
    "reason": "The request is ambiguous.",
})

VALID_REFUSAL_JSON = json.dumps({
    "kind": "refusal",
    "message": "I cannot execute arbitrary shell commands.",
})

INVALID_TOOL_PLAN_JSON = json.dumps({
    "kind": "plan",
    "user_facing_summary": "Run a shell command",
    "actions": [
        {
            "tool": "shell.execute",
            "arguments": {"cmd": "rm -rf /"},
            "explanation": "Delete everything",
        }
    ],
})

OUT_OF_SCOPE_PLAN_JSON = json.dumps({
    "kind": "plan",
    "user_facing_summary": "List /etc directory",
    "actions": [
        {
            "tool": "files.list_directory",
            "arguments": {"path": "/etc"},
            "explanation": "List system configuration files",
        }
    ],
})


@pytest.fixture
def mock_model() -> OllamaAdapter:
    """Create a mocked OllamaAdapter."""
    model = MagicMock(spec=OllamaAdapter)
    model.close = AsyncMock()
    return model


@pytest.fixture
def mock_executor() -> ToolExecutor:
    """Create a mocked ToolExecutor."""
    executor = MagicMock(spec=ToolExecutor)
    executor.is_available = True
    return executor


@pytest.fixture
def audit_log(tmp_path: Path) -> AuditLogger:
    return AuditLogger(log_path=tmp_path / "test_audit.jsonl")


@pytest.fixture
def agent(mock_model, mock_executor, audit_log) -> AgentLoop:
    """Create an AgentLoop with mocked dependencies."""
    return AgentLoop(model=mock_model, executor=mock_executor, audit=audit_log)


def _model_response(text: str) -> ModelResponse:
    return ModelResponse(text=text, model="neomint-planner", total_duration_ms=100.0, eval_count=50)


class TestProcessRequest:
    @pytest.mark.asyncio
    async def test_empty_request(self, agent: AgentLoop):
        response = await agent.process_request("")
        assert response.status == "error"
        assert "empty" in response.message.lower()

    @pytest.mark.asyncio
    async def test_model_returns_clarification(self, agent: AgentLoop, mock_model):
        mock_model.generate = AsyncMock(return_value=_model_response(VALID_CLARIFICATION_JSON))

        response = await agent.process_request("do something")
        assert response.status == "clarification"
        assert response.clarification is not None

    @pytest.mark.asyncio
    async def test_model_returns_refusal(self, agent: AgentLoop, mock_model):
        mock_model.generate = AsyncMock(return_value=_model_response(VALID_REFUSAL_JSON))

        response = await agent.process_request("run sudo rm -rf /")
        assert response.status == "refusal"
        assert response.refusal is not None

    @pytest.mark.asyncio
    async def test_model_returns_read_only_plan_executes_immediately(
        self, agent: AgentLoop, mock_model, mock_executor,
    ):
        mock_model.generate = AsyncMock(return_value=_model_response(VALID_PLAN_JSON))
        mock_executor.execute = AsyncMock(return_value=ToolResult(
            tool="files.list_directory", success=True, result={"files": []}, duration_ms=5.0,
        ))

        response = await agent.process_request("List my Documents")
        # files.list_directory is read-only, should execute without approval
        assert response.status == "plan_executed"
        assert response.results is not None

    @pytest.mark.asyncio
    async def test_model_connection_error(self, agent: AgentLoop, mock_model):
        mock_model.generate = AsyncMock(side_effect=OllamaConnectionError("No connection"))

        response = await agent.process_request("Hello")
        assert response.status == "error"
        assert "ollama" in response.message.lower()

    @pytest.mark.asyncio
    async def test_invalid_tool_rejected_by_policy(self, agent: AgentLoop, mock_model):
        mock_model.generate = AsyncMock(return_value=_model_response(INVALID_TOOL_PLAN_JSON))

        response = await agent.process_request("delete everything")
        assert response.status == "policy_violation"

    @pytest.mark.asyncio
    async def test_out_of_scope_rejected_by_policy(self, agent: AgentLoop, mock_model):
        mock_model.generate = AsyncMock(return_value=_model_response(OUT_OF_SCOPE_PLAN_JSON))

        response = await agent.process_request("list /etc")
        assert response.status == "policy_violation"


class TestApprovalFlow:
    @pytest.mark.asyncio
    async def test_reversible_plan_needs_approval(self, agent: AgentLoop, mock_model):
        plan_json = json.dumps({
            "kind": "plan",
            "user_facing_summary": "Open Firefox",
            "actions": [
                {"tool": "applications.launch", "arguments": {"name": "firefox"}, "explanation": "Launch Firefox"},
            ],
        })
        mock_model.generate = AsyncMock(return_value=_model_response(plan_json))

        response = await agent.process_request("Open Firefox")
        assert response.status == "plan_proposed"
        assert response.plan is not None
        assert response.plan.needs_approval
        assert agent.pending_plan_count == 1

    @pytest.mark.asyncio
    async def test_approve_executes_plan(self, agent: AgentLoop, mock_model, mock_executor):
        plan_json = json.dumps({
            "kind": "plan",
            "user_facing_summary": "Open Firefox",
            "actions": [
                {"tool": "applications.launch", "arguments": {"name": "firefox"}, "explanation": "Launch Firefox"},
            ],
        })
        mock_model.generate = AsyncMock(return_value=_model_response(plan_json))
        mock_executor.execute = AsyncMock(return_value=ToolResult(
            tool="applications.launch", success=True, result={"ok": True}, duration_ms=50.0,
        ))

        # First get the plan
        response = await agent.process_request("Open Firefox")
        plan_hash = response.plan.plan_hash

        # Then approve it
        exec_response = await agent.approve_plan(plan_hash)
        assert exec_response.status == "plan_executed"
        assert agent.pending_plan_count == 0

    @pytest.mark.asyncio
    async def test_cancel_plan(self, agent: AgentLoop, mock_model):
        plan_json = json.dumps({
            "kind": "plan",
            "user_facing_summary": "Open Firefox",
            "actions": [
                {"tool": "applications.launch", "arguments": {"name": "firefox"}, "explanation": "Launch Firefox"},
            ],
        })
        mock_model.generate = AsyncMock(return_value=_model_response(plan_json))

        response = await agent.process_request("Open Firefox")
        plan_hash = response.plan.plan_hash

        cancel_response = await agent.cancel_plan(plan_hash)
        assert cancel_response.status == "plan_denied"
        assert agent.pending_plan_count == 0

    @pytest.mark.asyncio
    async def test_approve_nonexistent_plan(self, agent: AgentLoop):
        response = await agent.approve_plan("nonexistent")
        assert response.status == "error"


class TestExecutionFailure:
    @pytest.mark.asyncio
    async def test_tool_failure_stops_execution(self, agent: AgentLoop, mock_model, mock_executor):
        mock_model.generate = AsyncMock(return_value=_model_response(VALID_PLAN_JSON))
        mock_executor.execute = AsyncMock(return_value=ToolResult(
            tool="files.list_directory", success=False, error="Permission denied", duration_ms=1.0,
        ))

        response = await agent.process_request("List my documents")
        assert response.status == "error"
        assert "failed" in response.message.lower()
        assert response.results is not None
        assert len(response.results) == 1
