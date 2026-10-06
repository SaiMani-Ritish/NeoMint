"""Tests for neomint_agent.parser — model output parsing."""

from __future__ import annotations

import json

import pytest

from neomint_agent.parser import parse_model_output
from neomint_agent.schemas import Clarification, Plan, Refusal

# ── Sample JSON strings for testing ──────────────────────────

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
    "reason": "The request is ambiguous — there are multiple possible locations.",
})

VALID_REFUSAL_JSON = json.dumps({
    "kind": "refusal",
    "message": "I cannot execute arbitrary shell commands. I can only use the tools available in my manifest.",
})


class TestParseValidJSON:
    def test_parse_valid_plan(self):
        result = parse_model_output(VALID_PLAN_JSON)
        assert isinstance(result, Plan)
        assert result.kind == "plan"
        assert len(result.actions) == 1
        assert result.actions[0].tool == "files.list_directory"

    def test_parse_valid_clarification(self):
        result = parse_model_output(VALID_CLARIFICATION_JSON)
        assert isinstance(result, Clarification)
        assert result.kind == "clarification"
        assert "folder" in result.question.lower()

    def test_parse_valid_refusal(self):
        result = parse_model_output(VALID_REFUSAL_JSON)
        assert isinstance(result, Refusal)
        assert result.kind == "refusal"


class TestParseJSONInCodeFences:
    def test_json_in_code_fence(self):
        raw = f"Here is my plan:\n```json\n{VALID_PLAN_JSON}\n```"
        result = parse_model_output(raw)
        assert isinstance(result, Plan)

    def test_json_in_bare_code_fence(self):
        raw = f"```\n{VALID_PLAN_JSON}\n```"
        result = parse_model_output(raw)
        assert isinstance(result, Plan)


class TestParseJSONWithSurroundingText:
    def test_json_with_prefix_text(self):
        raw = f"I'll create a plan for you:\n{VALID_PLAN_JSON}"
        result = parse_model_output(raw)
        assert isinstance(result, Plan)

    def test_json_with_suffix_text(self):
        raw = f"{VALID_PLAN_JSON}\nLet me know if you'd like to proceed."
        result = parse_model_output(raw)
        assert isinstance(result, Plan)


class TestParseMalformedOutput:
    def test_empty_string(self):
        result = parse_model_output("")
        assert isinstance(result, Refusal)
        assert "empty" in result.message.lower()

    def test_whitespace_only(self):
        result = parse_model_output("   \n\t  ")
        assert isinstance(result, Refusal)

    def test_no_json_at_all(self):
        result = parse_model_output("I don't know how to help with that.")
        assert isinstance(result, Refusal)

    def test_invalid_json(self):
        result = parse_model_output('{"kind": "plan", "actions": [}')
        assert isinstance(result, Refusal)
        assert "malformed" in result.message.lower()

    def test_json_array_instead_of_object(self):
        result = parse_model_output('[1, 2, 3]')
        assert isinstance(result, Refusal)

    def test_unknown_kind(self):
        raw = json.dumps({"kind": "execute", "command": "rm -rf /"})
        result = parse_model_output(raw)
        assert isinstance(result, Refusal)
        assert "unknown" in result.message.lower()


class TestParseTrailingCommas:
    def test_trailing_comma_in_object(self):
        raw = '{"kind": "refusal", "message": "nope",}'
        result = parse_model_output(raw)
        assert isinstance(result, Refusal)
        assert result.message == "nope"

    def test_trailing_comma_in_array(self):
        raw = json.dumps({
            "kind": "plan",
            "user_facing_summary": "Test",
            "actions": [
                {"tool": "clipboard.read", "arguments": {}, "explanation": "Read"},
            ],
        })
        # Add trailing comma manually
        raw = raw.replace('}]', '},]')
        result = parse_model_output(raw)
        assert isinstance(result, Plan)


class TestParseMissingFields:
    def test_plan_missing_actions(self):
        raw = json.dumps({"kind": "plan", "user_facing_summary": "No actions"})
        result = parse_model_output(raw)
        assert isinstance(result, Refusal)
        assert "validation" in result.message.lower()

    def test_clarification_missing_question(self):
        raw = json.dumps({"kind": "clarification", "reason": "Why not"})
        result = parse_model_output(raw)
        assert isinstance(result, Refusal)
