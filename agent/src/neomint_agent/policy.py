"""Deterministic policy engine for NeoMint.

The policy engine is the safety backbone of NeoMint. It assigns risk
levels, validates tool names, checks filesystem scopes, and enforces
action limits — all independently of the model's output.

The model is a PLANNER, not an authority. This module ensures that
even a compromised or hallucinating model cannot bypass safety rules.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

from neomint_agent.config import ALLOWED_FS_ROOTS, MAX_ACTIONS_PER_PLAN
from neomint_agent.schemas import (
    Action,
    Plan,
    PolicyViolation,
    RiskLevel,
    ValidatedAction,
    ValidatedPlan,
)

logger = logging.getLogger("neomint-agent.policy")

# ── Tool allowlist (from tool-manifest.json) ─────────────────
# Only these 12 tools are permitted. Any other tool name is rejected.

TOOL_ALLOWLIST: frozenset[str] = frozenset({
    "files.search",
    "files.list_directory",
    "files.open",
    "files.move_to_trash",
    "applications.list",
    "applications.launch",
    "clipboard.read",
    "clipboard.write",
    "system.status",
    "system.list_processes",
    "notes.create_draft",
    "settings.show",
})

# ── Risk classification (deterministic, never from model) ────

TOOL_RISK_MAP: dict[str, RiskLevel] = {
    # Read-only tools — no side effects
    "files.search": RiskLevel.READ_ONLY,
    "files.list_directory": RiskLevel.READ_ONLY,
    "applications.list": RiskLevel.READ_ONLY,
    "clipboard.read": RiskLevel.READ_ONLY,
    "system.status": RiskLevel.READ_ONLY,
    "system.list_processes": RiskLevel.READ_ONLY,
    # Reversible tools — require approval
    "files.open": RiskLevel.REVERSIBLE,
    "files.move_to_trash": RiskLevel.REVERSIBLE,
    "applications.launch": RiskLevel.REVERSIBLE,
    "clipboard.write": RiskLevel.REVERSIBLE,
    "notes.create_draft": RiskLevel.REVERSIBLE,
    "settings.show": RiskLevel.REVERSIBLE,
}

# ── Explicitly disabled tools ────────────────────────────────

DISABLED_TOOLS: frozenset[str] = frozenset({
    "shell.execute",
    "system.sudo",
    "files.delete_permanently",
    "packages.install",
    "network.configure",
    "users.modify",
    "services.manage",
})

# ── Dangerous patterns in arguments ─────────────────────────

_DANGEROUS_PATTERNS: list[str] = [
    "sudo",
    "rm -rf",
    "rm -r /",
    "mkfs",
    ":(){",         # fork bomb
    "dd if=",
    "> /dev/",
    "chmod 777",
    "chown root",
]


# ── Path scope validation ────────────────────────────────────


def _is_path_in_scope(path_str: str) -> bool:
    """Check if a path is within the allowed filesystem roots."""
    try:
        target = Path(path_str).expanduser().resolve()
    except (ValueError, OSError):
        return False

    for root in ALLOWED_FS_ROOTS:
        try:
            target.relative_to(root)
            return True
        except ValueError:
            continue

    return False


def _extract_paths_from_arguments(tool: str, arguments: dict) -> list[str]:
    """Extract filesystem paths from tool arguments for scope checking."""
    paths: list[str] = []

    if tool in {"files.search"}:
        roots = arguments.get("roots", [])
        if isinstance(roots, list):
            paths.extend(str(r) for r in roots)

    if tool in {"files.list_directory", "files.open", "files.move_to_trash"}:
        path = arguments.get("path")
        if path:
            paths.append(str(path))

    if tool == "notes.create_draft":
        directory = arguments.get("directory")
        if directory:
            paths.append(str(directory))

    return paths


# ── Argument validation ──────────────────────────────────────


def _check_dangerous_arguments(arguments: dict) -> list[str]:
    """Scan arguments for dangerous patterns."""
    violations: list[str] = []
    args_str = json.dumps(arguments).lower()

    for pattern in _DANGEROUS_PATTERNS:
        if pattern in args_str:
            violations.append(f"Dangerous pattern detected in arguments: '{pattern}'")

    return violations


# ── Plan validation ──────────────────────────────────────────


def validate_plan(plan: Plan) -> ValidatedPlan | PolicyViolation:
    """Validate a model-generated plan against safety policies.

    This function is the core safety gate. It checks:
    1. Action count against MAX_ACTIONS_PER_PLAN
    2. Tool names against the allowlist
    3. Dangerous argument patterns
    4. Filesystem paths against ALLOWED_FS_ROOTS
    5. Risk classification (deterministic, not from model)

    Returns a ValidatedPlan if everything passes, or a PolicyViolation
    with a list of reasons if anything fails.
    """
    violations: list[str] = []

    # Check action count
    if len(plan.actions) > MAX_ACTIONS_PER_PLAN:
        violations.append(
            f"Plan has {len(plan.actions)} actions; maximum is {MAX_ACTIONS_PER_PLAN}"
        )

    # Validate each action
    validated_actions: list[ValidatedAction] = []

    for i, action in enumerate(plan.actions, start=1):
        prefix = f"Action {i} ({action.tool})"

        # Check tool name against allowlist
        if action.tool in DISABLED_TOOLS:
            violations.append(f"{prefix}: Tool is explicitly disabled for safety")
            continue

        if action.tool not in TOOL_ALLOWLIST:
            violations.append(f"{prefix}: Unknown tool — not in the allowlist")
            continue

        # Check for dangerous argument patterns
        arg_violations = _check_dangerous_arguments(action.arguments)
        for v in arg_violations:
            violations.append(f"{prefix}: {v}")

        # Check filesystem paths are in scope
        paths = _extract_paths_from_arguments(action.tool, action.arguments)
        for path in paths:
            if not _is_path_in_scope(path):
                violations.append(
                    f"{prefix}: Path '{path}' is outside allowed scope "
                    f"({', '.join(str(r) for r in ALLOWED_FS_ROOTS)})"
                )

        # Assign deterministic risk level
        risk = TOOL_RISK_MAP.get(action.tool, RiskLevel.REVERSIBLE)

        # Build preview string
        preview = _build_preview(action, risk)

        validated_actions.append(
            ValidatedAction(
                tool=action.tool,
                arguments=action.arguments,
                explanation=action.explanation,
                risk=risk,
                preview=preview,
            )
        )

    if violations:
        logger.warning("Plan rejected by policy: %s", violations)
        return PolicyViolation(
            violations=violations,
            message=(
                "This plan was rejected by the safety policy. "
                f"{len(violations)} violation(s) found."
            ),
        )

    # Compute plan hash for approval binding
    plan_hash = compute_plan_hash(validated_actions)

    # Determine if approval is needed
    needs_approval = any(
        a.risk in {RiskLevel.REVERSIBLE, RiskLevel.DESTRUCTIVE}
        for a in validated_actions
    )

    return ValidatedPlan(
        user_facing_summary=plan.user_facing_summary,
        actions=validated_actions,
        plan_hash=plan_hash,
        needs_approval=needs_approval,
    )


def _build_preview(action: Action, risk: RiskLevel) -> str:
    """Build a human-readable preview string for an action."""
    parts = [f"{action.tool}"]

    # Summarize key arguments
    for key, value in action.arguments.items():
        if isinstance(value, str) and len(value) > 80:
            value = value[:77] + "..."
        parts.append(f"  {key}: {value}")

    risk_label = {
        RiskLevel.READ_ONLY: "Read only",
        RiskLevel.REVERSIBLE: "Requires approval",
        RiskLevel.DESTRUCTIVE: "DISABLED",
    }.get(risk, "Unknown")

    parts.append(f"  Risk: {risk_label}")

    return "\n".join(parts)


def compute_plan_hash(actions: list[ValidatedAction]) -> str:
    """Compute a deterministic SHA-256 hash of a validated plan.

    The hash covers tool names, arguments, and explanations — so
    any modification to the plan invalidates a prior approval.
    """
    payload = json.dumps(
        [
            {
                "tool": a.tool,
                "arguments": a.arguments,
                "explanation": a.explanation,
            }
            for a in actions
        ],
        sort_keys=True,
        ensure_ascii=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def needs_approval(validated_plan: ValidatedPlan) -> bool:
    """Check if any action in the plan requires user approval."""
    return validated_plan.needs_approval
