# NeoMint UX Specification

> Overlay UI behavior, keyboard flows, plan cards, and interaction states. For the implementation roadmap, see [roadmap.md](roadmap.md).

## Design identity

The NeoMint UI is a focused command workspace, not a traditional chatbot and not a replacement for every desktop application. It feels like a keyboard-first, text-heavy, high-density tool overlay that explains every action before execution.

## Core interaction model

```text
Global shortcut (Super+Space)
  → floating overlay opens at desktop center/bottom
  → input stays focused
  → user states intent
  → proposed action plan appears as an inspectable card
  → user chooses Approve / Edit / Cancel
  → live activity output streams below
  → audit/history remains locally available
  → Esc always closes or cancels safely
```

## UI layout

```text
┌───────────────────────────────────────────────────────────┐
│ NeoMint                                      Local • Safe  │
├───────────────────────────────────────────────────────────┤
│ > Find recent PDFs and open the newest one                 │
├───────────────────────────────────────────────────────────┤
│ Plan                                                       │
│  1  Search ~/Documents + ~/Downloads     Read only         │
│  2  Open newest result                   Requires approval │
│                                                           │
│ Preview: Search up to 20 PDFs modified in the last 7 days │
│                                                           │
│ [Approve]  [Edit plan]  [Cancel]                          │
├───────────────────────────────────────────────────────────┤
│ Activity                                                   │
│ ✓ Searched 14 PDFs in 91 ms                                │
│ ○ Awaiting approval to open the newest result              │
├───────────────────────────────────────────────────────────┤
│ Esc close/cancel  •  Ctrl+Enter approve  •  ↑ history      │
└───────────────────────────────────────────────────────────┘
```

### Layout sections

| Section | Purpose |
|---|---|
| **Header bar** | Application name, local/safe status indicator |
| **Prompt input** | Text-first input field, always focused on overlay open |
| **Plan card** | Inspectable action plan with tool names, risk levels, previews, and approval actions |
| **Activity feed** | Streaming execution log showing completed, pending, and failed actions |
| **Status bar** | Keyboard shortcuts, model state, budget state |

## Plan cards

Every proposed plan is rendered as an inspectable card showing:

1. **Tool name** — the specific typed tool to be called
2. **Plain-language explanation** — what the action does in human terms
3. **Risk category** — read-only, reversible, or (disabled) destructive
4. **Exact scoped arguments** — the specific parameters being passed
5. **Side-effect preview** — what will change and where
6. **Actions** — Approve, Edit plan, Cancel

Plan cards use **color as reinforcement, not the only risk signal**. Risk levels are always shown as text labels alongside any color coding.

## Keyboard flows

The overlay is **keyboard-first, mouse-optional**.

| Shortcut | Action |
|---|---|
| `Super+Space` | Open/focus the overlay |
| `Esc` | Close overlay, or cancel pending plan |
| `Ctrl+Enter` | Approve the current plan |
| `↑` / `↓` | Navigate command history |
| `Tab` | Cycle through plan card actions |
| `Enter` | Submit prompt or confirm focused action |

## Interaction states

```text
┌─────────┐     user types      ┌──────────┐     model responds     ┌────────────┐
│  Idle   │ ──────────────────► │ Planning │ ────────────────────► │ Reviewing  │
└─────────┘                     └──────────┘                       └────────────┘
     ▲                                                                   │
     │                               ┌──────────────┐                   │
     │         cancel                │  Executing   │◄──── approve ─────┘
     │◄──────────────────────────────┤              │
     │                               └──────┬───────┘
     │                                      │
     │              ┌────────┐              │ done
     └──────────────┤ Result ├◄─────────────┘
                    └────────┘
```

| State | Description | User can |
|---|---|---|
| **Idle** | Overlay open, input focused, waiting for user | Type intent, browse history, close |
| **Planning** | Model is generating a structured plan | Wait, cancel |
| **Reviewing** | Plan card is displayed | Approve, edit, cancel, inspect details |
| **Executing** | Approved plan is being executed | Watch activity feed, cancel (if safe) |
| **Result** | Execution complete, result displayed | Review, start new request, close |
| **Error** | An action failed or was rejected | Read error, retry (if policy permits), start new request |

## Status indicators

The overlay shows a persistent but minimal status bar:

- **Model state:** loaded / unloaded / loading
- **Offline indicator:** shown when Ollama is unavailable
- **Budget state:** inference time remaining / used
- **Pending confirmations:** count of plans awaiting approval

## Error handling

- **Error cards** display clear, actionable error messages.
- Retry is offered **only when policy permits it** (e.g., a transient timeout, not a policy rejection).
- Policy rejections show what was rejected and why, with no retry option.
- Missing system dependencies (e.g., `xclip` not installed) produce actionable local error messages.

## Emergency controls

- **Esc always works** — closes the overlay or cancels the current operation.
- **Emergency disable/quit** — a conventional desktop mechanism to fully stop NeoMint.
- The ordinary Mint desktop is always preserved behind the overlay.
- No hidden autonomous behavior — every action is visible in the UI before execution.

## Design principles

1. **Keyboard-first, mouse-optional** — every flow is completable without a mouse.
2. **Text-heavy but not terminal-only** — structured cards and visual hierarchy, not raw text.
3. **Compact, high signal, minimal chrome** — no wasted space, no decorative elements.
4. **Every action explains itself before execution** — no surprise side effects.
5. **Use color as reinforcement, not the only risk signal** — text labels accompany all color coding.
6. **Avoid hidden autonomous behavior** — the user sees everything before it happens.
7. **Preserve the ordinary Mint desktop** — the overlay is additive, not a replacement.

## Responsiveness

- The UI must remain responsive when local inference is slow or unavailable.
- A loading/planning indicator is shown during model inference.
- If the model is unavailable, the UI clearly indicates this and does not hang.
- All animations and transitions should be smooth and not block interaction.
