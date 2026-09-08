# NeoMint MCP Server

NeoMint's MCP server is the constrained capability layer between an agent and the local Linux desktop. It is intentionally not a general shell-control interface: tools should be typed, scoped, inspectable, policy-checked, and auditable.

## Session 0 demo

Session 0 provides a terminal-based, local-first proof of the NeoMint user flow:

```text
request → typed action plan → preview → approval when required → execution → JSON audit event
```

It contains no remote-model calls, no root escalation, no package management, no networking, and no destructive file actions.

### Install

```bash
cd mcp-server
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Run

```bash
python cli.py session
```

Then try:

```text
find recent PDFs
open firefox
copy NeoMint stays local-first
help
quit
```

`find recent PDFs` is read-only. `open <application>` and `copy <text>` require you to type `yes` after a plan preview. Unknown requests return a clarification response; they are never transformed into shell commands.

For GUI actions, run the session from your active Mint desktop session. Clipboard support uses `wl-copy` (Wayland) or `xclip` (X11).

### Test

```bash
pytest tests -q
```

## Design rules

- The UI and model have no direct system authority.
- The capability layer owns validation, permissions, previews, execution, and audit events.
- Risk classification is deterministic policy, not a model decision.
- Shell access is a narrow compatibility fallback, never the default action format.
- Every new tool must include a typed contract, permission scope, preview, audit event, and evaluation case.
