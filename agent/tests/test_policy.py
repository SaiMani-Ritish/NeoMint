"""Tests for neomint_agent.policy — deterministic policy engine."""

from __future__ import annotations

import json

import pytest

from neomint_agent.policy import (
    DISABLED_TOOLS,
    TOOL_ALLOWLIST,
    TOOL_RISK_MAP,
    _is_path_in_scope,
    compute_plan_hash,
    validate_plan,
)
from neomint_agent.schemas import Action, Plan, PolicyViolation, RiskLevel, ValidatedPlan


def _make_plan(actions: list[Action], summary: str = "Test plan") -> Plan:
    return Plan(kind="plan", user_facing_summary=summary, actions=actions)


class TestToolAllowlist:
    def test_all_12_tools_present(self):
        assert len(TOOL_ALLOWLIST) == 12

    def test_expected_tools(self):
        expected = {
            "files.search", "files.list_directory", "files.open",
            "files.move_to_trash", "applications.list", "applications.launch",
            "clipboard.read", "clipboard.write", "system.status",
            "system.list_processes", "notes.create_draft", "settings.show",
        }
        assert TOOL_ALLOWLIST == expected

    def test_disabled_tools_not_in_allowlist(self):
        for tool in DISABLED_TOOLS:
            assert tool not in TOOL_ALLOWLIST


class TestRiskClassification:
    def test_read_only_tools(self):
        read_only = {"files.search", "files.list_directory", "applications.list",
                      "clipboard.read", "system.status", "system.list_processes"}
        for tool in read_only:
            assert TOOL_RISK_MAP[tool] == RiskLevel.READ_ONLY

    def test_reversible_tools(self):
        reversible = {"files.open", "files.move_to_trash", "applications.launch",
                       "clipboard.write", "notes.create_draft", "settings.show"}
        for tool in reversible:
            assert TOOL_RISK_MAP[tool] == RiskLevel.REVERSIBLE

    def test_every_allowed_tool_has_risk(self):
        for tool in TOOL_ALLOWLIST:
            assert tool in TOOL_RISK_MAP


class TestValidatePlan:
    def test_valid_read_only_plan(self):
        plan = _make_plan([
            Action(tool="files.list_directory", arguments={"path": "~/Documents"}, explanation="List docs"),
        ])
        result = validate_plan(plan)
        assert isinstance(result, ValidatedPlan)
        assert not result.needs_approval
        assert len(result.actions) == 1

    def test_valid_reversible_plan_needs_approval(self):
        plan = _make_plan([
            Action(tool="applications.launch", arguments={"name": "firefox"}, explanation="Open Firefox"),
        ])
        result = validate_plan(plan)
        assert isinstance(result, ValidatedPlan)
        assert result.needs_approval

    def test_unknown_tool_rejected(self):
        plan = _make_plan([
            Action(tool="nonexistent.tool", arguments={}, explanation="Bad tool"),
        ])
        result = validate_plan(plan)
        assert isinstance(result, PolicyViolation)
        assert any("not in the allowlist" in v for v in result.violations)

    def test_disabled_tool_rejected(self):
        plan = _make_plan([
            Action(tool="shell.execute", arguments={"cmd": "ls"}, explanation="Shell"),
        ])
        result = validate_plan(plan)
        assert isinstance(result, PolicyViolation)
        assert any("disabled" in v.lower() for v in result.violations)

    def test_too_many_actions_rejected(self):
        """Plans with >5 actions are rejected at the schema level (Pydantic max_length=5)."""
        from pydantic import ValidationError as PydanticValidationError
        actions = [
            Action(tool="clipboard.read", arguments={}, explanation=f"Action {i}")
            for i in range(6)
        ]
        with pytest.raises(PydanticValidationError):
            _make_plan(actions)

    def test_out_of_scope_path_rejected(self):
        plan = _make_plan([
            Action(
                tool="files.list_directory",
                arguments={"path": "/etc/passwd"},
                explanation="Read passwd",
            ),
        ])
        result = validate_plan(plan)
        assert isinstance(result, PolicyViolation)
        assert any("outside allowed scope" in v for v in result.violations)

    def test_root_path_rejected(self):
        plan = _make_plan([
            Action(
                tool="files.list_directory",
                arguments={"path": "/"},
                explanation="List root",
            ),
        ])
        result = validate_plan(plan)
        assert isinstance(result, PolicyViolation)

    def test_dangerous_arguments_rejected(self):
        plan = _make_plan([
            Action(
                tool="clipboard.write",
                arguments={"text": "sudo rm -rf /"},
                explanation="Copy dangerous text",
            ),
        ])
        result = validate_plan(plan)
        assert isinstance(result, PolicyViolation)
        assert any("dangerous" in v.lower() for v in result.violations)

    def test_mixed_valid_and_invalid(self):
        plan = _make_plan([
            Action(tool="clipboard.read", arguments={}, explanation="Read clipboard"),
            Action(tool="shell.execute", arguments={"cmd": "whoami"}, explanation="Run shell"),
        ])
        result = validate_plan(plan)
        assert isinstance(result, PolicyViolation)


class TestPathScoping:
    def test_documents_in_scope(self):
        assert _is_path_in_scope("~/Documents")
        assert _is_path_in_scope("~/Documents/subfolder/file.txt")

    def test_downloads_in_scope(self):
        assert _is_path_in_scope("~/Downloads")
        assert _is_path_in_scope("~/Downloads/report.pdf")

    def test_desktop_in_scope(self):
        assert _is_path_in_scope("~/Desktop")

    def test_pictures_in_scope(self):
        assert _is_path_in_scope("~/Pictures")

    def test_etc_not_in_scope(self):
        assert not _is_path_in_scope("/etc")
        assert not _is_path_in_scope("/etc/passwd")

    def test_root_not_in_scope(self):
        assert not _is_path_in_scope("/")

    def test_system_dirs_not_in_scope(self):
        assert not _is_path_in_scope("/usr/bin")
        assert not _is_path_in_scope("/var/log")
        assert not _is_path_in_scope("/tmp")


class TestPlanHash:
    def test_same_plan_same_hash(self):
        from neomint_agent.schemas import ValidatedAction
        actions = [
            ValidatedAction(
                tool="clipboard.read", arguments={}, explanation="Read",
                risk=RiskLevel.READ_ONLY, preview="",
            ),
        ]
        h1 = compute_plan_hash(actions)
        h2 = compute_plan_hash(actions)
        assert h1 == h2

    def test_different_plans_different_hash(self):
        from neomint_agent.schemas import ValidatedAction
        actions1 = [
            ValidatedAction(
                tool="clipboard.read", arguments={}, explanation="Read",
                risk=RiskLevel.READ_ONLY, preview="",
            ),
        ]
        actions2 = [
            ValidatedAction(
                tool="clipboard.write", arguments={"text": "hi"}, explanation="Write",
                risk=RiskLevel.REVERSIBLE, preview="",
            ),
        ]
        assert compute_plan_hash(actions1) != compute_plan_hash(actions2)

    def test_hash_is_16_chars(self):
        from neomint_agent.schemas import ValidatedAction
        actions = [
            ValidatedAction(
                tool="clipboard.read", arguments={}, explanation="Read",
                risk=RiskLevel.READ_ONLY, preview="",
            ),
        ]
        assert len(compute_plan_hash(actions)) == 16
