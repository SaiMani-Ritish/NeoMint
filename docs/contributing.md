# Contributing to NeoMint

> Guidelines for adding tools, tests, and policy rules to NeoMint.

## Code standards

- **Python 3.11+** — all Python code uses type hints everywhere.
- **Async** — all tool functions are `async` and use `asyncio.to_thread` for blocking I/O.
- **No hardcoded values** — all secrets and paths go in `.env` files.
- **Typed responses** — every tool returns `ToolResponse` via `.ok()` or `.fail()` factories.
- **Clean commits** — no debug prints, no commented-out code, no temporary hacks.

## How to add a tool

### 1. Define the tool function

Create or update a file in `mcp-server/src/neomint_mcp/tools/`:

```python
async def my_tool(arg: str) -> ToolResponse:
    """One-line description of what this tool does.

    Args:
        arg: Description of the argument.

    Returns:
        ToolResponse with the result on success.
    """
    # Implementation
    return ToolResponse.ok(result)
```

### 2. Declare risk level and permission scope

In `session.py` (or the future policy engine), declare:

- **Risk level:** `read_only` or `reversible`. Destructive operations are disabled.
- **Permission scope:** which filesystem roots, registries, or resources the tool may access.
- **Preview text:** a human-readable description of what the tool will do with the given arguments.

### 3. Register with the MCP server

Add a wrapper in `mcp-server/src/neomint_mcp/server.py`:

```python
@mcp.tool()
async def my_tool(arg: str) -> str:
    """Tool description for MCP clients."""
    return (await tools_module.my_tool(arg)).to_json()
```

### 4. Write tests

Add a test file or test functions in `mcp-server/tests/`:

- **Positive test:** tool works correctly with valid input.
- **Negative test:** tool returns a clear error with invalid input.
- **Safety test:** tool rejects out-of-scope or forbidden input.

```python
@pytest.mark.asyncio
async def test_my_tool_success():
    result = await my_tool("valid_input")
    assert result.success is True

@pytest.mark.asyncio
async def test_my_tool_rejects_bad_input():
    result = await my_tool("")
    assert result.success is False
    assert "error" in result.error.lower()
```

### 5. Add evaluation fixtures

Add fixtures in `eval/fixtures/` (once Phase 5 is implemented):

```json
{
  "id": "intent-my-tool",
  "category": "intent_planning",
  "description": "User asks for my_tool functionality",
  "input": "natural language request that should trigger my_tool",
  "expected": {
    "plan_tools": ["my_tool"],
    "needs_confirmation": true,
    "risk_level": "reversible"
  }
}
```

### 6. Update documentation

- Add the tool to the MCP server README's tool reference table.
- If the tool introduces a new capability category, update `docs/roadmap.md` and `docs/safety-model.md`.

## How to add a test fixture

1. Create a JSON file in `eval/fixtures/` with a unique `id`.
2. Declare the `category` from the evaluation categories in [evaluation.md](evaluation.md).
3. Define `input` (user prompt) and `expected` (golden plan assertions).
4. Tag the fixture for filtering.
5. Run the benchmark runner to verify the fixture passes.

## How to add a policy rule

1. Identify the guardrail from [safety-model.md](safety-model.md).
2. Implement the check in the policy engine (currently `session.py`, future `agent/policy.py`).
3. Add a **positive test** (allowed input passes) and a **negative test** (blocked input is rejected).
4. Add the guardrail to the safety-model documentation.
5. Add adversarial evaluation fixtures.

## Pull request checklist

- [ ] All new tools have typed contracts (`ToolResponse`).
- [ ] All new tools declare risk level and permission scope.
- [ ] All state-changing tools have preview and confirmation paths.
- [ ] Tests pass: `cd mcp-server && pytest tests -q`.
- [ ] No capstone/academic framing in product documentation.
- [ ] No hardcoded secrets or paths.
- [ ] Documentation updated if the tool surface changed.
