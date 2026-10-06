"""MCP tool dispatcher for NeoMint.

Maps validated tool names to the actual MCP server tool functions.
In standalone mode, tools are imported directly from the MCP server
package. For remote mode, tools could be called via HTTP (future).

Each tool execution is timed and returns a ToolResult with
success/failure status, result data, and duration.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path
from time import perf_counter
from typing import Any, Callable, Coroutine

from neomint_agent.config import TOOL_TIMEOUT_SECONDS
from neomint_agent.schemas import ToolResult

logger = logging.getLogger("neomint-agent.executor")

# Type alias for async tool functions
ToolFunction = Callable[..., Coroutine[Any, Any, Any]]


class ToolExecutor:
    """Dispatches validated tool calls to MCP server implementations.

    In standalone mode, imports tool functions directly from the
    neomint_mcp package. Falls back to a no-op executor if the
    MCP server package is not installed.

    Args:
        timeout: Per-tool execution timeout in seconds.
    """

    def __init__(self, timeout: int = TOOL_TIMEOUT_SECONDS) -> None:
        self.timeout = timeout
        self._dispatch: dict[str, ToolFunction] = {}
        self._mcp_available = False
        self._load_tools()

    def _load_tools(self) -> None:
        """Try to import MCP server tools for direct execution."""
        try:
            # Add the mcp-server/src to the path if needed
            mcp_src = Path(__file__).resolve().parents[3] / "mcp-server" / "src"
            if mcp_src.exists() and str(mcp_src) not in sys.path:
                sys.path.insert(0, str(mcp_src))

            from neomint_mcp.tools import applications, clipboard, filesystem

            self._dispatch = {
                # Filesystem tools
                "files.search": self._wrap_files_search,
                "files.list_directory": self._wrap_list_directory(filesystem),
                "files.open": self._wrap_files_open(filesystem),
                "files.move_to_trash": self._wrap_files_move_to_trash,

                # Application tools
                "applications.list": self._wrap_applications_list,
                "applications.launch": self._wrap_applications_launch(applications),

                # Clipboard tools
                "clipboard.read": self._wrap_clipboard_read(clipboard),
                "clipboard.write": self._wrap_clipboard_write(clipboard),

                # System tools
                "system.status": self._wrap_system_status,
                "system.list_processes": self._wrap_system_list_processes,

                # Notes tools
                "notes.create_draft": self._wrap_notes_create_draft(filesystem),

                # Settings tools
                "settings.show": self._wrap_settings_show(applications),
            }
            self._mcp_available = True
            logger.info("MCP server tools loaded successfully")

        except ImportError as exc:
            logger.warning("MCP server package not available: %s", exc)
            logger.warning("Tool execution will return mock responses")
            self._mcp_available = False

    # ── Tool wrappers ────────────────────────────────────────
    # Each wrapper adapts the tool-manifest argument schema
    # to the actual MCP server function signatures.

    @staticmethod
    async def _wrap_files_search(**kwargs: Any) -> dict[str, Any]:
        """Search for files. Uses filesystem tools internally."""
        import json as _json

        from neomint_mcp.tools import filesystem

        roots = kwargs.get("roots", ["~/Documents"])
        name_glob = kwargs.get("name_glob", "*")
        max_results = kwargs.get("max_results", 20)

        all_results: list[dict[str, Any]] = []
        for root in roots:
            resp = await filesystem.list_files(root)
            data = _json.loads(resp.to_json())
            if data.get("success") and data.get("result"):
                for entry in data["result"]:
                    if _match_glob(entry.get("name", ""), name_glob):
                        all_results.append({"path": f"{root}/{entry['name']}", **entry})

        return {"count": len(all_results), "files": all_results[:max_results]}

    @staticmethod
    def _wrap_list_directory(fs_mod: Any) -> ToolFunction:
        async def _call(**kwargs: Any) -> dict[str, Any]:
            import json as _json
            path = kwargs.get("path", ".")
            resp = await fs_mod.list_files(path)
            return _json.loads(resp.to_json())
        return _call

    @staticmethod
    def _wrap_files_open(fs_mod: Any) -> ToolFunction:
        async def _call(**kwargs: Any) -> dict[str, Any]:
            import subprocess
            path = kwargs.get("path", "")
            try:
                subprocess.Popen(
                    ["xdg-open", path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
                return {"success": True, "message": f"Opened {path}"}
            except OSError as exc:
                return {"success": False, "error": str(exc)}
        return _call

    @staticmethod
    async def _wrap_files_move_to_trash(**kwargs: Any) -> dict[str, Any]:
        """Move a file to trash using gio trash."""
        import subprocess
        path = kwargs.get("path", "")
        try:
            result = subprocess.run(
                ["gio", "trash", path],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                return {"success": True, "message": f"Moved {path} to trash"}
            return {"success": False, "error": result.stderr.strip()}
        except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
            return {"success": False, "error": str(exc)}

    @staticmethod
    async def _wrap_applications_list(**kwargs: Any) -> dict[str, Any]:
        """List installed applications from the registry."""
        from neomint_mcp.config import APP_REGISTRY
        return {"applications": sorted(APP_REGISTRY.keys())}

    @staticmethod
    def _wrap_applications_launch(app_mod: Any) -> ToolFunction:
        async def _call(**kwargs: Any) -> dict[str, Any]:
            import json as _json
            name = kwargs.get("name", "")
            resp = await app_mod.open_application(name)
            return _json.loads(resp.to_json())
        return _call

    @staticmethod
    def _wrap_clipboard_read(clip_mod: Any) -> ToolFunction:
        async def _call(**kwargs: Any) -> dict[str, Any]:
            import json as _json
            resp = await clip_mod.get_clipboard()
            return _json.loads(resp.to_json())
        return _call

    @staticmethod
    def _wrap_clipboard_write(clip_mod: Any) -> ToolFunction:
        async def _call(**kwargs: Any) -> dict[str, Any]:
            import json as _json
            text = kwargs.get("text", "")
            resp = await clip_mod.set_clipboard(text)
            return _json.loads(resp.to_json())
        return _call

    @staticmethod
    async def _wrap_system_status(**kwargs: Any) -> dict[str, Any]:
        """Get system status via standard commands."""
        import subprocess
        include = kwargs.get("include", ["disk", "memory", "cpu", "uptime", "os"])
        status: dict[str, Any] = {}

        if "disk" in include:
            try:
                result = subprocess.run(["df", "-h", "/"], capture_output=True, text=True, timeout=5)
                status["disk"] = result.stdout.strip()
            except Exception:
                status["disk"] = "unavailable"

        if "memory" in include:
            try:
                result = subprocess.run(["free", "-h"], capture_output=True, text=True, timeout=5)
                status["memory"] = result.stdout.strip()
            except Exception:
                status["memory"] = "unavailable"

        if "uptime" in include:
            try:
                result = subprocess.run(["uptime", "-p"], capture_output=True, text=True, timeout=5)
                status["uptime"] = result.stdout.strip()
            except Exception:
                status["uptime"] = "unavailable"

        if "os" in include:
            try:
                result = subprocess.run(["lsb_release", "-d", "-s"], capture_output=True, text=True, timeout=5)
                status["os"] = result.stdout.strip()
            except Exception:
                status["os"] = "unavailable"

        return {"success": True, "status": status}

    @staticmethod
    async def _wrap_system_list_processes(**kwargs: Any) -> dict[str, Any]:
        """List running processes."""
        import subprocess
        sort_by = kwargs.get("sort_by", "cpu")
        limit = kwargs.get("limit", 10)

        sort_flag = {"cpu": "-pcpu", "memory": "-pmem", "name": "-comm"}.get(sort_by, "-pcpu")

        try:
            result = subprocess.run(
                ["ps", "aux", "--sort", sort_flag],
                capture_output=True, text=True, timeout=5,
            )
            lines = result.stdout.strip().split("\n")
            return {"success": True, "processes": lines[:limit + 1]}  # +1 for header
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    @staticmethod
    def _wrap_notes_create_draft(fs_mod: Any) -> ToolFunction:
        async def _call(**kwargs: Any) -> dict[str, Any]:
            import json as _json
            title = kwargs.get("title", "untitled")
            content = kwargs.get("content", "")
            directory = kwargs.get("directory", "~/Documents")
            filename = title.replace(" ", "_").lower() + ".txt"
            path = f"{directory}/{filename}"
            resp = await fs_mod.write_file(path, content)
            return _json.loads(resp.to_json())
        return _call

    @staticmethod
    def _wrap_settings_show(app_mod: Any) -> ToolFunction:
        async def _call(**kwargs: Any) -> dict[str, Any]:
            panel = kwargs.get("panel", "")
            cmd = "cinnamon-settings"
            if panel:
                cmd = f"cinnamon-settings {panel}"
            import subprocess
            try:
                subprocess.Popen(
                    cmd, shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
                return {"success": True, "message": f"Opened settings{f' ({panel})' if panel else ''}"}
            except OSError as exc:
                return {"success": False, "error": str(exc)}
        return _call

    # ── Main execution method ────────────────────────────────

    async def execute(self, tool: str, arguments: dict[str, Any]) -> ToolResult:
        """Execute a validated tool call with timeout enforcement.

        Args:
            tool: Tool name from the allowlist.
            arguments: Tool-specific arguments.

        Returns:
            ToolResult with success/failure, result data, and timing.
        """
        start = perf_counter()

        handler = self._dispatch.get(tool)
        if handler is None:
            return ToolResult(
                tool=tool,
                success=False,
                error=f"No handler registered for tool '{tool}'",
                duration_ms=0.0,
            )

        try:
            result = await asyncio.wait_for(
                handler(**arguments),
                timeout=self.timeout,
            )
            duration_ms = (perf_counter() - start) * 1000

            # Normalize result
            success = True
            if isinstance(result, dict):
                success = result.get("success", True)

            return ToolResult(
                tool=tool,
                success=success,
                result=result,
                duration_ms=round(duration_ms, 2),
            )

        except asyncio.TimeoutError:
            duration_ms = (perf_counter() - start) * 1000
            return ToolResult(
                tool=tool,
                success=False,
                error=f"Tool execution timed out after {self.timeout}s",
                duration_ms=round(duration_ms, 2),
            )
        except Exception as exc:
            duration_ms = (perf_counter() - start) * 1000
            logger.error("Tool execution error for '%s': %s", tool, exc)
            return ToolResult(
                tool=tool,
                success=False,
                error=str(exc),
                duration_ms=round(duration_ms, 2),
            )

    @property
    def is_available(self) -> bool:
        """Check if MCP tools are available for execution."""
        return self._mcp_available


def _match_glob(name: str, pattern: str) -> bool:
    """Simple glob matching for file search."""
    import fnmatch
    return fnmatch.fnmatch(name.lower(), pattern.lower())
