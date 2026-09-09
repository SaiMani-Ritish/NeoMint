# Phase 2, Session 0 — Local-first vertical slice

> Historical implementation record. For the current roadmap, see [roadmap.md](roadmap.md).

## Product boundary

NeoMint is a local-first, AI-native desktop shell for Linux Mint. The model turns a user request into a transparent action plan; a constrained capability layer executes only approved, policy-checked actions.

This session establishes the first usable vertical slice: text request → deterministic local plan → preview → explicit confirmation → execution → audit event. It deliberately does not invoke a model, shell, root privileges, networking, package management, or destructive file operations.

## Included demo actions

- `find recent PDFs`: searches `~/Documents` and `~/Downloads` for PDFs modified in the last seven days.
- `open <application>`: resolves an application with `gtk-launch`; execution is a safe, local launcher operation.
- `copy <text>`: copies supplied text through the existing clipboard tool surface when enabled.

## Safety contract

1. The planner produces typed `ActionPlan` objects; it does not receive system authority.
2. Every action has a risk level, explanation, preview, and audit record.
3. Read-only actions may run immediately. Reversible actions require explicit approval.
4. This demo's planner recognizes a small deterministic command grammar. A future local LLM must emit the same typed plan format and pass the same validation and policy gates.
5. Unknown requests return a clarification response rather than a shell command.

## Run

```bash
cd mcp-server
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
python cli.py session
```

Try:

```text
find recent PDFs
open firefox
copy NeoMint stays local-first
help
quit
```

For a confirmation-required action, type `yes` only after reviewing the plan. The session prints JSON audit events to stdout.

## Next increments

- Wire this session runtime to the overlay UI.
- Replace deterministic intent recognition with local structured model output.
- Add a durable, local audit log and an approval UI.
- Add system-resource measurements and cgroup-backed budgets.
- Expand typed tools only after evaluation cases and permission rules exist.
