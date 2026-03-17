"""CLI test harness for manually calling NeoMint MCP tools.

Usage:
    python cli.py --help
    python cli.py list_files '{"path": "/home/user"}'
    python cli.py run_command '{"cmd": "ls -la"}'
    python cli.py get_clipboard '{}'
"""

from __future__ import annotations

import asyncio
import json
import sys

from neomint_mcp.models import ToolResponse
from neomint_mcp.tools import applications, clipboard, filesystem, shell

TOOLS: dict[str, object] = {
    "list_files": filesystem.list_files,
    "read_file": filesystem.read_file,
    "write_file": filesystem.write_file,
    "run_command": shell.run_command,
    "open_application": applications.open_application,
    "get_clipboard": clipboard.get_clipboard,
    "set_clipboard": clipboard.set_clipboard,
}


def print_help() -> None:
    print("NeoMint MCP Tool Test Harness")
    print("=" * 45)
    print()
    print("Available tools:")
    for name in TOOLS:
        print(f"  {name}")
    print()
    print("Usage:")
    print("  python cli.py <tool_name> '<json_args>'")
    print()
    print("Examples:")
    print('  python cli.py list_files \'{"path": "/home/user"}\'')
    print('  python cli.py run_command \'{"cmd": "uname -a"}\'')
    print('  python cli.py get_clipboard \'{}\'')


async def run_tool(name: str, args: dict[str, object]) -> None:
    tool_fn = TOOLS.get(name)
    if tool_fn is None:
        print(f"Error: unknown tool '{name}'")
        print(f"Available: {', '.join(TOOLS)}")
        sys.exit(1)

    try:
        result: ToolResponse = await tool_fn(**args)  # type: ignore[operator]
        print(json.dumps(json.loads(result.to_json()), indent=2))
    except NotImplementedError:
        print(json.dumps({"error": f"Tool '{name}' is not yet implemented."}, indent=2))
    except TypeError as exc:
        print(f"Argument error: {exc}")
        sys.exit(1)
    except Exception as exc:
        print(f"Unexpected error: {exc}")
        sys.exit(1)


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print_help()
        sys.exit(0)

    tool_name = sys.argv[1]

    args: dict[str, object] = {}
    if len(sys.argv) >= 3:
        try:
            args = json.loads(sys.argv[2])
        except json.JSONDecodeError as exc:
            print(f"Invalid JSON arguments: {exc}")
            sys.exit(1)

    asyncio.run(run_tool(tool_name, args))


if __name__ == "__main__":
    main()
