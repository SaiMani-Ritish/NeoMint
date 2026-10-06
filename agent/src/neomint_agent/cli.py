"""Interactive CLI for the NeoMint agent.

A terminal REPL for testing the agent loop without the overlay UI.
Displays plans, handles approval flow, and shows execution results.

Usage:
    python -m neomint_agent.cli
    neomint-agent-cli  (via console_scripts entry point)
"""

from __future__ import annotations

import asyncio
import json
import sys

from neomint_agent.loop import AgentLoop
from neomint_agent.schemas import AgentResponse


# ── ANSI colors ──────────────────────────────────────────────

GREEN = "\033[0;32m"
RED = "\033[0;31m"
YELLOW = "\033[1;33m"
CYAN = "\033[0;36m"
BOLD = "\033[1m"
DIM = "\033[2m"
NC = "\033[0m"


def _banner() -> None:
    print(f"{GREEN}{BOLD}")
    print("  _   _            __  __ _       _   ")
    print(" | \\ | | ___  ___ |  \\/  (_)_ __ | |_ ")
    print(" |  \\| |/ _ \\/ _ \\| |\\/| | | '_ \\| __|")
    print(" | |\\  |  __/ (_) | |  | | | | | | |_ ")
    print(" |_| \\_|\\___|\\___/|_|  |_|_|_| |_|\\__|")
    print(f"{NC}")
    print(f"  {DIM}Agent CLI — Type your intent, or 'help' for guidance{NC}")
    print()


def _print_response(response: AgentResponse) -> None:
    """Pretty-print an agent response."""
    status_colors = {
        "plan_proposed": YELLOW,
        "plan_executed": GREEN,
        "plan_approved": GREEN,
        "plan_denied": DIM,
        "clarification": CYAN,
        "refusal": RED,
        "policy_violation": RED,
        "error": RED,
    }

    color = status_colors.get(response.status, NC)
    print(f"\n{color}{BOLD}[{response.status.upper()}]{NC} {response.message}")

    if response.plan:
        plan = response.plan
        print(f"\n  {BOLD}Plan{NC} {DIM}(hash: {plan.plan_hash}){NC}")
        for i, action in enumerate(plan.actions, 1):
            risk_color = {
                "read_only": GREEN,
                "reversible": YELLOW,
                "destructive": RED,
            }.get(action.risk, NC)

            print(f"  {BOLD}{i}.{NC} {action.explanation}")
            print(f"     Tool: {action.tool}")
            print(f"     Risk: {risk_color}{action.risk}{NC}")
            if action.arguments:
                args_str = json.dumps(action.arguments, indent=2)
                for line in args_str.split("\n"):
                    print(f"     {DIM}{line}{NC}")

        if plan.needs_approval:
            print(f"\n  {YELLOW}⚠ This plan requires your approval.{NC}")

    if response.results:
        print(f"\n  {BOLD}Results{NC}")
        for result in response.results:
            icon = f"{GREEN}✓{NC}" if result.success else f"{RED}✗{NC}"
            print(f"  {icon} {result.tool} ({result.duration_ms:.0f}ms)")
            if result.error:
                print(f"    {RED}Error: {result.error}{NC}")
            elif result.result:
                result_str = json.dumps(result.result, indent=2)
                # Truncate long results
                lines = result_str.split("\n")
                if len(lines) > 10:
                    for line in lines[:8]:
                        print(f"    {DIM}{line}{NC}")
                    print(f"    {DIM}... ({len(lines) - 8} more lines){NC}")
                else:
                    for line in lines:
                        print(f"    {DIM}{line}{NC}")

    if response.clarification:
        print(f"\n  {CYAN}Reason: {response.clarification.reason}{NC}")


async def _run_cli() -> None:
    """Run the interactive CLI loop."""
    _banner()

    agent = AgentLoop()

    try:
        while True:
            try:
                user_input = input(f"\n{GREEN}neomint>{NC} ").strip()
            except (EOFError, KeyboardInterrupt):
                print(f"\n{DIM}Session ended.{NC}")
                break

            if not user_input:
                continue

            if user_input.lower() in {"quit", "exit", "q"}:
                print(f"{DIM}Session ended.{NC}")
                break

            if user_input.lower() == "help":
                print(f"""
  {BOLD}NeoMint Agent CLI{NC}

  {BOLD}Commands:{NC}
    help              Show this help
    status            Check agent and model status
    history           Show recent audit events
    pending           Show pending plans
    approve <hash>    Approve a pending plan
    cancel <hash>     Cancel a pending plan
    quit / exit       Exit the CLI

  {BOLD}Examples:{NC}
    List my Documents folder
    Find PDF files in my Downloads
    Open Firefox
    What's my disk usage?
    Copy "hello world" to clipboard
    Create a note about meeting tomorrow
""")
                continue

            if user_input.lower() == "status":
                available = await agent.model.is_available()
                print(f"  Model: {'✓ available' if available else '✗ unavailable'}")
                print(f"  Tools: {'✓ loaded' if agent.executor.is_available else '✗ not loaded'}")
                print(f"  Pending plans: {agent.pending_plan_count}")
                continue

            if user_input.lower() == "history":
                events = agent.audit.read_recent(10)
                if not events:
                    print(f"  {DIM}No audit events yet.{NC}")
                else:
                    for event in events:
                        ts = event.get("timestamp", "?")[:19]
                        ev = event.get("event", "?")
                        req = event.get("request", "")[:60]
                        print(f"  {DIM}{ts}{NC} [{ev}] {req}")
                continue

            if user_input.lower() == "pending":
                plans = agent.get_pending_plans()
                if not plans:
                    print(f"  {DIM}No pending plans.{NC}")
                else:
                    for hash_, plan in plans.items():
                        print(f"  {YELLOW}{hash_}{NC}: {plan.user_facing_summary}")
                continue

            if user_input.lower().startswith("approve "):
                plan_hash = user_input.split(maxsplit=1)[1].strip()
                response = await agent.approve_plan(plan_hash)
                _print_response(response)
                continue

            if user_input.lower().startswith("cancel "):
                plan_hash = user_input.split(maxsplit=1)[1].strip()
                response = await agent.cancel_plan(plan_hash)
                _print_response(response)
                continue

            # Process as a natural language request
            response = await agent.process_request(user_input)
            _print_response(response)

            # Auto-prompt for approval if needed
            if response.status == "plan_proposed" and response.plan:
                try:
                    choice = input(
                        f"\n  {YELLOW}Approve this plan? "
                        f"[yes/no/edit]{NC} "
                    ).strip().lower()
                except (EOFError, KeyboardInterrupt):
                    print(f"\n{DIM}Cancelled.{NC}")
                    continue

                if choice in {"yes", "y"}:
                    exec_response = await agent.approve_plan(response.plan.plan_hash)
                    _print_response(exec_response)
                elif choice in {"no", "n"}:
                    cancel_response = await agent.cancel_plan(response.plan.plan_hash)
                    _print_response(cancel_response)
                else:
                    print(f"  {DIM}Plan remains pending. Use 'approve {response.plan.plan_hash}' later.{NC}")

    finally:
        await agent.close()


def main() -> None:
    """CLI entry point."""
    try:
        asyncio.run(_run_cli())
    except KeyboardInterrupt:
        print(f"\n{DIM}Interrupted.{NC}")
        sys.exit(0)


if __name__ == "__main__":
    main()
