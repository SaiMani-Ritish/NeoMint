# NeoMint Safety Model

> Permission model, risk tiers, guardrails, and audit rules. This document defines the safety contract that all NeoMint components must enforce.

## Core principle

> The model—or any planner—can propose a typed plan, but it does not receive operating-system authority.

The capability layer owns execution and restricts behavior through fixed tool names, typed arguments, explicit risk levels, human-readable action previews, confirmation for state-changing actions, local audit records, and no fallback from unknown natural language to shell execution.

## Risk tiers

Every tool and action declares a risk level. Risk classification is **deterministic and independent of model output**—the policy engine assigns risk based on the tool name and arguments, never based on the model's self-reported risk assessment.

| Risk tier | Description | Confirmation required | Example |
|---|---|---|---|
| `read_only` | No side effects; only reads or inspects state | No | `list_files`, `read_file`, `get_clipboard`, `search_recent_pdfs` |
| `reversible` | Modifiable side effects that can be undone or are low-impact | Yes — explicit approval before execution | `open_application`, `set_clipboard`, `write_file`, `copy` |
| `destructive` | Permanent, high-impact, or irreversible changes | **Disabled by default** | `rm`, `sudo`, permanent deletion |

### Disabled operations

The following operations are disabled entirely and cannot be unlocked through model output or user prompts alone:

- Arbitrary shell commands (must use typed tools)
- Root / `sudo` escalation
- Permanent file deletion
- Network access and external account operations
- Any tool not on the registered allowlist

## Filesystem scopes

Tools that access the filesystem are restricted to explicit scope roots. The default permitted roots are:

- `~/Documents`
- `~/Downloads`

Access to paths outside permitted roots is rejected at the policy layer before execution. The system never grants unrestricted home or system directory access.

## Tool allowlists

### Shell command allowlist

The `run_command` tool validates the base command (argv[0]) against a fixed allowlist in `config.py`. Commands not on the list are rejected immediately with an error listing the allowed commands.

### Application registry

The `open_application` tool resolves application names through a fixed registry mapping friendly names to desktop entry identifiers. Unknown application names are rejected.

## Confirmation and plan binding

### Confirmation rules

- **Read-only actions** may execute immediately without user confirmation.
- **Reversible actions** require explicit user approval before execution.
- **Destructive actions** are disabled entirely.
- The user approves a **specific plan hash**, not a vague category of actions.
- An approval is **never reused** for a modified plan.

### Plan binding

When the agent produces a plan, the user sees:
1. Tool name
2. Plain-language explanation
3. Risk category
4. Exact scoped arguments
5. Side-effect preview

The user can then **Approve**, **Edit**, or **Cancel** the plan. Execution only proceeds with explicit approval of the exact plan shown.

## Guardrail defaults

These guardrails are enforced from Phase 3 onward:

| Guardrail | Default policy |
|---|---|
| Arbitrary shell commands | Disabled; use typed tools first |
| Root / `sudo` | Disabled |
| Permanent deletion | Disabled |
| Network and external accounts | Disabled until separately designed |
| Tool calls per request | Low fixed maximum (3–5) |
| Tool execution timeout | Per-tool timeout (configurable, default 30s) |
| Model inference time | Bounded and surfaced in UI/audit log |
| Filesystem scope | Explicit roots, never unrestricted home/system access |
| Unknown tools/arguments | Reject and request clarification |
| Write operations | Preview plus explicit confirmation |
| Approval reuse | Never reuse an approval for a modified plan |
| Audit storage | Local-only, inspectable, deletable by the user |

## Loop limits and resource budgets

The agent runtime enforces deterministic limits on every request:

- **Maximum actions per request:** configurable fixed limit (default 3–5).
- **Recursion/iteration limits:** the planning loop has a hard maximum step count.
- **Timeouts:** per-tool execution timeout and overall request timeout.
- **Resource budgets:** model inference time is bounded and reported.

If any limit is reached, the system stops gracefully, reports the limit, and does not silently continue.

## Recovery behavior

- One failed action yields an explanation and stops (or re-plans) rather than silently continuing.
- Ambiguous or high-impact requests trigger a "clarify instead of guess" response.
- Unknown requests return a clarification message listing supported actions, never a shell command.

## Audit rules

### Audit events

Every interaction produces a structured audit event containing:
- Event type (executed, denied, clarification, awaiting_confirmation)
- Original user request
- Timestamp
- Planned actions (tool, arguments, risk, explanation, preview)
- Execution result (success/failure, duration, error details)

### Storage

- Audit logs are **local-only** — stored as JSONL on the user's machine.
- Audit logs are **inspectable** — plain JSON, human-readable.
- Audit logs are **deletable** — the user has full control over their data.
- No audit data is transmitted over any network.

## Model output validation

The agent runtime validates all model output before it reaches the capability layer:

1. **Schema validation:** output must conform to the `ActionPlan` JSON schema.
2. **Tool allowlist:** every tool name in the plan must be registered.
3. **Argument validation:** arguments must be valid for the tool's typed contract.
4. **Scope validation:** filesystem paths must be within permitted roots.
5. **Authority check:** attempts to elevate permissions or bypass policy are rejected.
6. **Malformed output:** invalid JSON, missing fields, or unexpected structure is rejected.

If validation fails at any step, the plan is discarded and the user receives a clarification message.
