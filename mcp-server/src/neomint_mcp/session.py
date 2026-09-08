from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from time import perf_counter
from typing import Any


class RiskLevel(StrEnum):
    READ_ONLY = "read_only"
    REVERSIBLE = "reversible"


@dataclass(frozen=True)
class PlannedAction:
    tool: str
    arguments: dict[str, Any]
    risk: RiskLevel
    explanation: str
    preview: str


@dataclass(frozen=True)
class ActionPlan:
    request: str
    actions: list[PlannedAction]
    needs_confirmation: bool
    clarification: str | None = None


@dataclass
class AuditEvent:
    event: str
    request: str
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    actions: list[dict[str, Any]] = field(default_factory=list)
    result: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(asdict(self), default=str, sort_keys=True)


def plan_request(request: str) -> ActionPlan:
    normalized = request.strip()
    lowered = normalized.lower()

    if lowered in {"find recent pdfs", "find recent pdf", "find my recent pdfs"}:
        return ActionPlan(
            request=normalized,
            actions=[
                PlannedAction(
                    tool="files.search_recent_pdfs",
                    arguments={"roots": ["~/Documents", "~/Downloads"], "days": 7, "max_results": 20},
                    risk=RiskLevel.READ_ONLY,
                    explanation="Searches your Documents and Downloads folders for recently modified PDF files.",
                    preview="Read-only search: ~/Documents, ~/Downloads; PDF files modified in the last 7 days.",
                )
            ],
            needs_confirmation=False,
        )

    if lowered.startswith("open ") and len(normalized.split(maxsplit=1)) == 2:
        application = normalized.split(maxsplit=1)[1].strip()
        return ActionPlan(
            request=normalized,
            actions=[
                PlannedAction(
                    tool="applications.launch",
                    arguments={"application": application},
                    risk=RiskLevel.REVERSIBLE,
                    explanation=f"Launches the local application named '{application}'.",
                    preview=f"Launch request: {application}",
                )
            ],
            needs_confirmation=True,
        )

    if lowered.startswith("copy ") and len(normalized.split(maxsplit=1)) == 2:
        text = normalized.split(maxsplit=1)[1]
        return ActionPlan(
            request=normalized,
            actions=[
                PlannedAction(
                    tool="clipboard.copy",
                    arguments={"text": text},
                    risk=RiskLevel.REVERSIBLE,
                    explanation="Replaces the current clipboard contents with the supplied text.",
                    preview=f"Clipboard replacement: {text!r}",
                )
            ],
            needs_confirmation=True,
        )

    return ActionPlan(
        request=normalized,
        actions=[],
        needs_confirmation=False,
        clarification=(
            "I can currently handle: 'find recent PDFs', 'open <application>', or 'copy <text>'. "
            "I will not guess or run a shell command for an unknown request."
        ),
    )


def render_plan(plan: ActionPlan) -> str:
    if plan.clarification:
        return f"NeoMint needs clarification: {plan.clarification}"

    lines = ["NeoMint plan:"]
    for index, action in enumerate(plan.actions, start=1):
        lines.extend((
            f"{index}. {action.explanation}",
            f"   Tool: {action.tool}",
            f"   Risk: {action.risk.value}",
            f"   Preview: {action.preview}",
        ))
    lines.append("Confirmation required: yes" if plan.needs_confirmation else "Confirmation required: no")
    return "\n".join(lines)


def _search_recent_pdfs(arguments: dict[str, Any]) -> dict[str, Any]:
    cutoff = datetime.now().timestamp() - int(arguments["days"]) * 24 * 60 * 60
    matches: list[dict[str, Any]] = []
    for root_name in arguments["roots"]:
        root = Path(root_name).expanduser()
        if not root.is_dir():
            continue
        try:
            for path in root.rglob("*.pdf"):
                try:
                    stat = path.stat()
                except OSError:
                    continue
                if stat.st_mtime >= cutoff:
                    matches.append({"path": str(path), "modified_at": datetime.fromtimestamp(stat.st_mtime, UTC).isoformat()})
        except OSError:
            continue
    matches.sort(key=lambda item: item["modified_at"], reverse=True)
    return {"count": len(matches), "files": matches[: int(arguments["max_results"])]}


def _launch_application(arguments: dict[str, Any]) -> dict[str, Any]:
    application = arguments["application"]
    if not application or any(character in application for character in ";&|`$\n"):
        return {"ok": False, "error": "Application identifier contains forbidden characters."}
    try:
        completed = subprocess.run(["gtk-launch", application], check=False, capture_output=True, text=True, timeout=10)
    except FileNotFoundError:
        return {"ok": False, "error": "gtk-launch is unavailable; run this inside a Linux desktop session."}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "Application launch timed out."}
    return {"ok": completed.returncode == 0, "returncode": completed.returncode, "stderr": completed.stderr.strip()}


def _copy_to_clipboard(arguments: dict[str, Any]) -> dict[str, Any]:
    text = arguments["text"]
    for command in (["wl-copy"], ["xclip", "-selection", "clipboard"]):
        try:
            completed = subprocess.run(command, input=text, check=False, capture_output=True, text=True, timeout=5)
        except FileNotFoundError:
            continue
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": "Clipboard operation timed out."}
        return {"ok": completed.returncode == 0, "returncode": completed.returncode, "stderr": completed.stderr.strip()}
    return {"ok": False, "error": "No supported clipboard utility found. Install wl-clipboard or xclip."}


def execute_plan(plan: ActionPlan, approved: bool = False) -> AuditEvent:
    action_data = [asdict(action) for action in plan.actions]
    if plan.clarification:
        return AuditEvent(event="clarification", request=plan.request, actions=action_data, result={"message": plan.clarification})
    if plan.needs_confirmation and not approved:
        return AuditEvent(event="awaiting_confirmation", request=plan.request, actions=action_data)

    started = perf_counter()
    results: list[dict[str, Any]] = []
    dispatch = {
        "files.search_recent_pdfs": _search_recent_pdfs,
        "applications.launch": _launch_application,
        "clipboard.copy": _copy_to_clipboard,
    }
    for action in plan.actions:
        handler = dispatch[action.tool]
        try:
            results.append({"tool": action.tool, "result": handler(action.arguments)})
        except Exception as error:
            results.append({"tool": action.tool, "result": {"ok": False, "error": str(error)}})
    return AuditEvent(
        event="executed",
        request=plan.request,
        actions=action_data,
        result={"results": results, "duration_ms": round((perf_counter() - started) * 1000, 2)},
    )


def run_session() -> None:
    print("NeoMint Session 0 — local-first agent shell")
    print("Type 'help' for examples or 'quit' to exit.")
    while True:
        try:
            request = input("\nneomint> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nSession ended.")
            return
        if request.lower() in {"quit", "exit"}:
            print("Session ended.")
            return
        if request.lower() == "help":
            print("Examples: find recent PDFs | open firefox | copy NeoMint stays local-first")
            continue
        if not request:
            continue

        plan = plan_request(request)
        print(render_plan(plan))
        if plan.needs_confirmation:
            approval = input("Approve this plan? [yes/No] ").strip().lower() == "yes"
            event = execute_plan(plan, approved=approval)
            if not approval:
                event = AuditEvent(event="denied", request=plan.request, actions=[asdict(action) for action in plan.actions])
        else:
            event = execute_plan(plan)
        print("Audit event:")
        print(event.to_json())


if __name__ == "__main__":
    run_session()
