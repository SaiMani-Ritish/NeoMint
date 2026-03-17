# NeoMint MCP Server

Python MCP (Model Context Protocol) server that exposes OS-level tools
for the NeoMint agentic loop.

## Tools

| Tool               | Description                          | Parameters              |
|--------------------|--------------------------------------|-------------------------|
| `list_files`       | List directory contents              | `path: str`             |
| `read_file`        | Read a file's text content           | `path: str`             |
| `write_file`       | Write/overwrite a file               | `path: str, content: str` |
| `run_command`      | Run a shell command (allowlisted)    | `cmd: str`              |
| `open_application` | Launch a GUI app by name             | `app_name: str`         |
| `get_clipboard`    | Get current clipboard text           | —                       |
| `set_clipboard`    | Set clipboard text                   | `text: str`             |

## Response Format

All tools return a standardized JSON response:

```json
{
  "success": true,
  "result": "...",
  "error": null
}
```

## Setup

```bash
cd mcp-server
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Running

```bash
# Start the MCP server (stdio transport)
neomint-mcp

# Use the CLI test harness
python cli.py list_files '{"path": "/home"}'
python cli.py run_command '{"cmd": "ls -la"}'
```

## Testing

```bash
pytest
```

## Safety

- `run_command` validates commands against a configurable allowlist before execution
- `write_file` operations are logged and can require confirmation
- All tool calls are logged with timestamps

## Configuration

Copy `.env.example` to `.env` and adjust:

```bash
cp .env.example .env
```

See `.env.example` for available options.
