# NeoMint Roadmap

> Canonical project roadmap. For implementation details, see the component-level documentation in each directory.

## Naming conventions

| Term | Use it for | Example |
|---|---|---|
| Phase | A shippable architectural milestone | Phase 3: Agentic loop and policy guardrails |
| Session | A bounded coding session or PR-sized deliverable | Phase 3, Session 1: Structured local planner |
| Component | A durable technical subsystem | `policy-engine`, `agent-runtime`, `overlay-ui` |
| Evaluation | Acceptance criteria and regression tests | Tool-selection, safety, latency, and UI-flow benchmarks |

## Phase overview

```text
Phase 2: Local-first capability foundation
  └── Session 0: Typed planning, previews, confirmation, audit events

Phase 3: Agentic loop and safety guardrails
  ├── Session 1: Local structured planner adapter
  ├── Session 2: Policy engine and approval service
  └── Session 3: Audit persistence and recovery behavior

Phase 4: Floating overlay UI
  ├── Session 1: OpenCode-inspired interface shell
  ├── Session 2: Plan/approval cards and activity feed
  └── Session 3: Keyboard-first desktop integration

Phase 5: Evaluation and release readiness
  ├── Session 1: Task and safety benchmark fixtures
  ├── Session 2: Automated regression runner
  └── Session 3: Performance/resource-budget reporting
```

---

## Phase 2 — Capability foundation

**Status:** in progress, with Session 0 complete.

This is the current foundation: typed local actions, readable plans, previews, explicit confirmation for reversible actions, local execution, and JSON audit events.

### Completed in Session 0

- `find recent PDFs` as a read-only tool.
- `open <application>` as an approval-required action.
- `copy <text>` as an approval-required action.
- Clarification instead of shell fallback for unknown prompts.
- Initial unit tests around risk and refusal behavior.

### Phase 2 exit criteria

- Every tool has a typed input/output contract.
- Every tool declares its risk level and permission scope.
- Every state-changing action has a preview and confirmation path.
- No tool uses unrestricted model-generated shell commands.
- The session flow is manually runnable and test-covered.

---

## Phase 3 — Agentic loop and guardrails

**Goal:** replace the current deterministic phrase matcher with a local agent loop while maintaining or strengthening the safety contract.

The local LLM becomes a **planner**, not an executor. It may interpret a user's request and propose one or more typed tool calls, but the capability and policy layers remain deterministic.

```text
User request
  → local model produces structured candidate plan
  → schema validation
  → tool allowlist validation
  → argument/scope validation
  → risk classification
  → preview and approval gate
  → constrained execution
  → result observation
  → optional next safe planning step
  → durable audit record
```

### Phase 3 deliverables

- `agent-runtime` or `agent/` implementation that supports Ollama/local model adapters.
- Strict structured output schema for plans, actions, and tool arguments.
- Model-output parser that rejects malformed JSON, unknown tool names, missing fields, invalid scopes, and attempts to elevate authority.
- Deterministic policy engine that assigns risk independent of model output.
- Tool allowlist and permission scopes—for example, `~/Documents` and `~/Downloads`, rather than all filesystem paths.
- Approval service with exact plan binding: the user approves a specific plan hash, not a vague category of actions.
- Loop limits: maximum actions per request, recursion/iteration limits, timeouts, and resource budgets.
- Durable local JSONL audit log, including plan, approval decision, execution result, timing, and failure reason.
- Graceful recovery: one failed action should yield an explanation and stop/re-plan rather than silently continuing.
- A strict "clarify instead of guess" behavior for ambiguous or high-impact requests.

### Phase 3 guardrails (enforce from day one)

| Guardrail | Default policy |
|---|---|
| Arbitrary shell commands | Disabled; use typed tools first |
| Root / `sudo` | Disabled |
| Permanent deletion | Disabled |
| Network and external accounts | Disabled until separately designed |
| Tool calls per request | Low fixed maximum, e.g. 3–5 |
| Tool execution timeout | Per-tool timeout |
| Model inference time | Bounded and surfaced in UI/audit log |
| Filesystem scope | Explicit roots, never unrestricted home/system access |
| Unknown tools/arguments | Reject and request clarification |
| Write operations | Preview plus explicit confirmation |
| Approval reuse | Never reuse an approval for a modified plan |
| Audit storage | Local-only, inspectable, deletable by the user |

### Phase 3 exit criteria

- A local Ollama model can generate plans matching the typed action schema.
- Invalid or adversarial model output is rejected before execution.
- A user can inspect, approve, deny, and review a plan outcome.
- The system has deterministic time, action-count, and scope limits.
- Safety tests cover prompt injection-like inputs, malformed plans, unsupported tools, risky paths, and cancellation.

---

## Phase 4 — Floating overlay UI

**Goal:** ship the actual NeoMint interaction surface: a keyboard-first, floating AI overlay inspired by OpenCode's information density, clarity, diff/plan visibility, and execution feedback—not a copy of its branding or proprietary assets.

See [ux-spec.md](ux-spec.md) for the full UI specification.

### Phase 4 deliverables

- A separate `overlay-ui/` application, likely a lightweight desktop shell client rather than a browser-only mockup.
- Global keyboard shortcut and a floating, always-on-top window.
- Text-first prompt composer with keyboard navigation and command history.
- Plan cards that show tool name, plain-language explanation, risk category, exact scoped arguments, side-effect preview, and approve/edit/cancel actions.
- Streaming execution/activity log.
- Local history and audit viewer.
- Settings for local model, inference resource budget, permissions, directories, and log retention.
- A persistent but minimal status indicator: model loaded/unloaded, offline state, budget state, and pending confirmation count.
- Clear error cards with retry only when policy permits it.
- An emergency disable/quit mechanism and conventional desktop escape hatch.

### Phase 4 exit criteria

- A user can complete the Session 0 flows without opening a terminal.
- Approval state is visually unambiguous.
- Escape/cancel reliably stops pending plans.
- UI remains responsive when local inference is slow or unavailable.
- The overlay is usable through a keyboard-only flow.

---

## Phase 5 — Evaluation and release readiness

**Goal:** make NeoMint measurable. This is especially important because agents can appear useful while being unreliable, unsafe, slow, or resource-heavy.

See [evaluation.md](evaluation.md) for the full evaluation specification.

### Phase 5 deliverables

- Task fixtures written in JSON or YAML.
- A mock tool executor so safety and plan tests never alter a real machine.
- Golden plans and expected-policy assertions.
- Regression tests for every supported tool.
- A benchmark runner that produces local reports.
- Performance/resource tracking for plan latency, model latency, tool time, peak RAM, CPU, and number of actions.
- Human UX test scripts for plan clarity and confirmation comprehension.
- A test matrix for X11 and Wayland behavior where relevant.

### Phase 5 exit criteria

- Every supported capability has positive, negative, and safety-policy tests.
- Evaluation runs without changing user files or launching user apps.
- The project has a baseline success rate, safety failure rate, latency budget, and resource budget.
- Regressions block expansion of the tool surface.
- The README states what NeoMint does and does not safely support.
