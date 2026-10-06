"""Tests for neomint_agent.schemas — Pydantic model validation."""

from __future__ import annotations

import pytest

from neomint_agent.schemas import (
    Action,
    AgentResponse,
    Clarification,
    Plan,
    PolicyViolation,
    Refusal,
    RiskLevel,
    ToolResult,
    ValidatedAction,
    ValidatedPlan,
)


class TestAction:
    def test_valid_action(self):
        action = Action(
            tool="files.list_directory",
            arguments={"path": "~/Documents"},
            explanation="List files",
        )
        assert action.tool == "files.list_directory"
        assert action.arguments == {"path": "~/Documents"}

    def test_action_empty_arguments(self):
        action = Action(tool="clipboard.read", arguments={}, explanation="Read clipboard")
        assert action.arguments == {}


class TestPlan:
    def test_valid_plan(self):
        plan = Plan(
            kind="plan",
            user_facing_summary="Do something",
            actions=[
                Action(tool="files.list_directory", arguments={"path": "~/Documents"}, explanation="List files"),
            ],
        )
        assert plan.kind == "plan"
        assert len(plan.actions) == 1

    def test_plan_empty_actions_rejected(self):
        with pytest.raises(Exception):
            Plan(
                kind="plan",
                user_facing_summary="Nothing to do",
                actions=[],
            )

    def test_plan_too_many_actions_rejected(self):
        actions = [
            Action(tool="files.list_directory", arguments={"path": "~"}, explanation=f"Action {i}")
            for i in range(6)
        ]
        with pytest.raises(Exception):
            Plan(
                kind="plan",
                user_facing_summary="Too many",
                actions=actions,
            )


class TestClarification:
    def test_valid_clarification(self):
        c = Clarification(
            kind="clarification",
            question="Which folder?",
            reason="Ambiguous request",
        )
        assert c.kind == "clarification"
        assert c.question == "Which folder?"


class TestRefusal:
    def test_valid_refusal(self):
        r = Refusal(kind="refusal", message="Cannot do that")
        assert r.kind == "refusal"
        assert r.message == "Cannot do that"


class TestRiskLevel:
    def test_risk_levels(self):
        assert RiskLevel.READ_ONLY == "read_only"
        assert RiskLevel.REVERSIBLE == "reversible"
        assert RiskLevel.DESTRUCTIVE == "destructive"


class TestValidatedPlan:
    def test_validated_plan(self):
        vp = ValidatedPlan(
            user_facing_summary="List files",
            actions=[
                ValidatedAction(
                    tool="files.list_directory",
                    arguments={"path": "~/Documents"},
                    explanation="List files",
                    risk=RiskLevel.READ_ONLY,
                    preview="files.list_directory\n  path: ~/Documents\n  Risk: Read only",
                ),
            ],
            plan_hash="abc123",
            needs_approval=False,
        )
        assert vp.plan_hash == "abc123"
        assert not vp.needs_approval


class TestToolResult:
    def test_success_result(self):
        tr = ToolResult(tool="files.list_directory", success=True, result={"files": []}, duration_ms=10.5)
        assert tr.success
        assert tr.duration_ms == 10.5

    def test_failure_result(self):
        tr = ToolResult(tool="files.list_directory", success=False, error="Not found", duration_ms=1.0)
        assert not tr.success
        assert tr.error == "Not found"


class TestAgentResponse:
    def test_plan_proposed(self):
        resp = AgentResponse(status="plan_proposed", message="Here's the plan")
        assert resp.status == "plan_proposed"
        assert resp.plan is None

    def test_error_response(self):
        resp = AgentResponse(status="error", message="Something broke")
        assert resp.status == "error"
