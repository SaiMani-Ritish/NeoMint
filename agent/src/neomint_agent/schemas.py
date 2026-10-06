"""Pydantic schemas for the NeoMint agent.

These mirror the action-plan.schema.json contract:
  - Plan: one or more typed tool calls
  - Clarification: a question for the user
  - Refusal: a rejection with explanation

The policy engine enriches raw plans into ValidatedPlans with
risk levels, plan hashes, and approval state.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field


# ── Risk levels ──────────────────────────────────────────────


class RiskLevel(StrEnum):
    """Deterministic risk tier assigned by the policy engine."""

    READ_ONLY = "read_only"
    REVERSIBLE = "reversible"
    DESTRUCTIVE = "destructive"


# ── Planner output (model response) ─────────────────────────


class Action(BaseModel):
    """A single typed tool call proposed by the model."""

    tool: str
    arguments: dict[str, Any]
    explanation: str


class Plan(BaseModel):
    """A proposed action plan from the model."""

    kind: Literal["plan"]
    user_facing_summary: str
    actions: list[Action] = Field(min_length=1, max_length=5)


class Clarification(BaseModel):
    """The model requests clarification from the user."""

    kind: Literal["clarification"]
    question: str
    reason: str


class Refusal(BaseModel):
    """The model refuses an unsafe or unsupported request."""

    kind: Literal["refusal"]
    message: str


PlannerOutput = Annotated[
    Plan | Clarification | Refusal,
    Field(discriminator="kind"),
]


# ── Validated plan (post-policy) ─────────────────────────────


class ValidatedAction(BaseModel):
    """An action enriched with deterministic risk classification."""

    tool: str
    arguments: dict[str, Any]
    explanation: str
    risk: RiskLevel
    preview: str


class ValidatedPlan(BaseModel):
    """A plan that has passed policy validation."""

    user_facing_summary: str
    actions: list[ValidatedAction]
    plan_hash: str
    needs_approval: bool


class PolicyViolation(BaseModel):
    """A plan that was rejected by the policy engine."""

    violations: list[str]
    message: str


# ── Tool execution results ───────────────────────────────────


class ToolResult(BaseModel):
    """Result of executing a single tool."""

    tool: str
    success: bool
    result: Any = None
    error: str | None = None
    duration_ms: float = 0.0


# ── Agent response envelope ─────────────────────────────────


class AgentResponse(BaseModel):
    """Top-level response from the agent loop to the UI/CLI."""

    status: Literal[
        "plan_proposed",
        "plan_approved",
        "plan_denied",
        "plan_executed",
        "clarification",
        "refusal",
        "policy_violation",
        "error",
    ]
    message: str
    plan: ValidatedPlan | None = None
    results: list[ToolResult] | None = None
    clarification: Clarification | None = None
    refusal: Refusal | None = None
