Implemented and pushed **NeoMint Session 0** directly to the `main` branch. The new commit is `6e2c459a33d3baf6f5ece92fda3ac28a7e3f8138`. 

This is a deliberately small, local-first proof of the NeoMint interaction model—not yet the graphical OpenCode-inspired shell. It proves the critical flow first:

```text
User request
  → typed action plan
  → human-readable preview
  → confirmation for state-changing actions
  → constrained local execution
  → JSON audit event
```

## What was added

The implementation adds:

- `mcp-server/src/neomint_mcp/session.py`
  - A terminal-based NeoMint interaction session.
  - Typed `ActionPlan`, `PlannedAction`, risk levels, and `AuditEvent` records.
  - Deterministic request planning—no remote API calls and no model inference yet.
  - Explicit confirmation before reversible actions.
  - A safe refusal/clarification path for unknown requests.

- `mcp-server/cli.py`
  - Adds the `session` command to launch the NeoMint terminal experience.

- `mcp-server/tests/test_session.py`
  - Covers read-only classification, confirmation requirements, and refusal of an unsafe/unknown request.

- `mcp-server/README.md`
  - Installation, execution, test instructions, and capability-layer design rules.

- `docs/session-zero.md`
  - Documents the product boundary, safety contract, demo scope, and next development steps.

The implementation intentionally excludes remote LLM calls, root escalation, arbitrary shell execution, networking, package management, and destructive filesystem actions. 

## Run it on Mint

Clone or update your local repository, then run:

```bash
git pull origin main

cd NeoMint/mcp-server

python3 -m venv .venv
source .venv/bin/activate

pip install -e .
python cli.py session
```

You should see:

```text
NeoMint Session 0 — local-first agent shell
Type 'help' for examples or 'quit' to exit.

neomint>
```

Use these first:

```text
help
find recent PDFs
open firefox
copy NeoMint stays local-first
quit
```

### Expected behavior

| Input | Behavior | Confirmation |
|---|---|---|
| `find recent PDFs` | Recursively searches `~/Documents` and `~/Downloads` for PDFs modified in the last seven days | No—read-only |
| `open firefox` | Shows a plan and requests approval before launching the local `.desktop` application via `gtk-launch` | Yes |
| `copy NeoMint stays local-first` | Shows a preview and requests approval before replacing clipboard contents | Yes |
| An unsupported request | Returns a clarification message and does not invoke shell commands | No action taken |

For example:

```text
neomint> open firefox

NeoMint plan:
1. Launches the local application named 'firefox'.
   Tool: applications.launch
   Risk: reversible
   Preview: Launch request: firefox
Confirmation required: yes

Approve this plan? [yes/No] yes
```

Then NeoMint prints a structured JSON audit event with the request, tool, arguments, action risk, result, and duration.

## Test it

While the virtual environment is active:

```bash
cd NeoMint/mcp-server
pytest tests -q
```

The Session 0 tests validate that:

- Searching for recent PDFs is classified as read-only.
- Launching an application requires explicit approval.
- Clipboard replacement requires explicit approval.
- A request such as `remove every file from my home directory` gets a clarification result instead of any execution.

If `pytest` is unavailable in your environment:

```bash
pip install pytest
pytest tests -q
```

## Desktop prerequisites

Run the interactive session from within your active Linux Mint graphical login session.

For clipboard support:

- On an X11 session, install `xclip`:

```bash
sudo apt install xclip
```

- On a Wayland session, install `wl-clipboard`:

```bash
sudo apt install wl-clipboard
```

The demo will safely report an error if neither clipboard utility is present; it does not fall back to arbitrary commands.

For application launching, `open firefox` assumes a desktop-entry identifier recognized by `gtk-launch`. You can inspect available application entries with:

```bash
find /usr/share/applications ~/.local/share/applications -name '*.desktop' -printf '%f\n' | sort
```

If Firefox is represented as `firefox.desktop`, use:

```text
open firefox
```

If needed, try the desktop-file stem, such as:

```text
open org.gnome.Nautilus
```

## What this proves

This session establishes the most important NeoMint invariant:

> The model—or currently the deterministic planner—can propose a typed plan, but it does not receive operating-system authority.

The capability layer owns execution and restricts behavior through:

- Fixed tool names.
- Typed arguments.
- Explicit risk levels.
- Human-readable action previews.
- Confirmation for state-changing actions.
- Local audit records.
- No fallback from unknown natural language to shell execution.

That is the right foundation before adding an OpenCode-style UI or connecting an Ollama-hosted local model. 

## Recommended next session

The next implementation session should build the **OpenCode-style local interface**, while preserving the same plan/preview/approval boundary:

1. Create an `overlay-ui` app with a dark, text-dominant chat/command workspace.
2. Add a plan card that visibly shows tool, risk, arguments, preview, and approval buttons.
3. Stream session events into an activity/audit panel.
4. Add a backend API around `plan_request()` and `execute_plan()`.
5. Integrate Ollama only as a structured planner that outputs the existing `ActionPlan` shape.
6. Reject malformed model output and fall back to a clarifying question.
7. Add a local JSONL audit log plus resource measurements for model/runtime budgets.

The current implementation is on `main` and ready for you to run locally.
