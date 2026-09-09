#!/usr/bin/env python3
"""Convert legacy Alpaca-format NeoMint training data to the new structured format.

Reads the old format:
    {"instruction": "...", "input": "...", "output": "..."}

Produces the new format:
    {"id": "...", "messages": [...], "tool_manifest": [...], "target": {...}, "labels": {...}}

This is a best-effort conversion. The old format uses free-text tool_call blocks;
the new format requires structured JSON targets. Manual review is recommended.

Usage:
    python convert_legacy.py ../../datasets/neomint_train.jsonl --output ../data/converted_legacy.jsonl
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SYSTEM_PROMPT = (
    "You are NeoMint Planner. Given a user request about their Linux Mint desktop, "
    "return a JSON object conforming to the NeoMint action-plan schema. You propose "
    "tools from the provided manifest; you never execute tools. If the request is "
    "ambiguous, ask a clarification question. If the request is unsupported or unsafe, "
    "refuse with an explanation."
)

TOOL_MANIFEST = [
    "files.search", "files.list_directory", "files.open", "files.move_to_trash",
    "applications.list", "applications.launch",
    "clipboard.read", "clipboard.write",
    "system.status", "system.list_processes",
    "notes.create_draft", "settings.show",
]

# Map old tool names to new tool names
TOOL_NAME_MAP = {
    "list_files": "files.list_directory",
    "read_file": "files.open",
    "write_file": "notes.create_draft",
    "run_command": None,  # No direct equivalent — needs manual review
    "open_application": "applications.launch",
    "get_clipboard": "clipboard.read",
    "set_clipboard": "clipboard.write",
}

TOOL_CALL_PATTERN = re.compile(r"```tool_call\s*\n\s*(\{.*?\})\s*\n\s*```", re.DOTALL)


def convert_entry(entry: dict, index: int) -> dict | None:
    """Convert a single legacy entry to the new format."""
    instruction = entry.get("instruction", "").strip()
    output = entry.get("output", "").strip()

    if not instruction or not output:
        return None

    # Parse tool_call blocks from the old output
    matches = TOOL_CALL_PATTERN.findall(output)

    if not matches:
        # No tool call — this is either a clarification or a conversation entry
        # Extract the text before any tool call as a clarification/refusal
        target = {
            "kind": "clarification",
            "question": output.split("\n")[0] if output else instruction,
            "reason": "Converted from legacy dataset — requires manual review.",
        }
        category = "ambiguous"
        needs_confirmation = False
    else:
        actions = []
        category = "read_only"
        needs_confirmation = False

        for match_str in matches:
            try:
                old_call = json.loads(match_str)
            except json.JSONDecodeError:
                continue

            old_tool = old_call.get("tool", "")
            old_args = old_call.get("args", {})

            new_tool = TOOL_NAME_MAP.get(old_tool)
            if new_tool is None:
                # run_command and unknown tools — cannot auto-convert
                target = {
                    "kind": "refusal",
                    "message": f"Converted from legacy: original used '{old_tool}' which is not in the new manifest. Requires manual review.",
                }
                return {
                    "id": f"legacy_{index:04d}",
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": instruction},
                    ],
                    "tool_manifest": TOOL_MANIFEST,
                    "target": target,
                    "labels": {"category": "needs_review", "expected_confirmation": False},
                    "_legacy_conversion": True,
                    "_original_tool": old_tool,
                }

            # Map old arguments to new structure
            new_args = _map_arguments(new_tool, old_args)

            # Extract explanation from the text before the tool_call block
            explanation_text = output.split("```tool_call")[0].strip()
            if not explanation_text:
                explanation_text = f"Uses {new_tool} tool."

            actions.append({
                "tool": new_tool,
                "arguments": new_args,
                "explanation": explanation_text,
            })

            # Determine category and confirmation
            if new_tool in ("applications.launch", "clipboard.write", "notes.create_draft", "files.move_to_trash", "files.open"):
                category = "reversible"
                needs_confirmation = True

        if not actions:
            return None

        summary = output.split("```tool_call")[0].strip()
        if not summary:
            summary = f"Performs {len(actions)} action(s) based on your request."

        target = {
            "kind": "plan",
            "user_facing_summary": summary,
            "actions": actions,
        }

    return {
        "id": f"legacy_{index:04d}",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": instruction},
        ],
        "tool_manifest": TOOL_MANIFEST,
        "target": target,
        "labels": {"category": category, "expected_confirmation": needs_confirmation},
        "_legacy_conversion": True,
    }


def _map_arguments(new_tool: str, old_args: dict) -> dict:
    """Map old argument names to new argument structure."""
    if new_tool == "files.list_directory":
        return {"path": old_args.get("path", "~")}
    elif new_tool == "files.open":
        return {"path": old_args.get("path", "")}
    elif new_tool == "applications.launch":
        return {"name": old_args.get("app_name", old_args.get("name", ""))}
    elif new_tool == "clipboard.read":
        return {}
    elif new_tool == "clipboard.write":
        return {"text": old_args.get("text", "")}
    elif new_tool == "notes.create_draft":
        path = old_args.get("path", "")
        content = old_args.get("content", "")
        title = Path(path).stem if path else "untitled"
        return {"title": title, "content": content}
    else:
        return old_args


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert legacy Alpaca-format data to new structured format")
    parser.add_argument("input", type=Path, help="Path to legacy JSONL file")
    parser.add_argument("--output", type=Path, default=None, help="Output path (default: <input>_converted.jsonl)")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: File not found: {args.input}")
        sys.exit(1)

    output_path = args.output or args.input.with_name(args.input.stem + "_converted.jsonl")

    converted = []
    skipped = 0
    needs_review = 0

    with args.input.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                print(f"  Skipping line {i}: JSON parse error")
                skipped += 1
                continue

            result = convert_entry(entry, i)
            if result is None:
                skipped += 1
                continue

            if result.get("labels", {}).get("category") == "needs_review":
                needs_review += 1

            converted.append(result)

    with output_path.open("w", encoding="utf-8") as f:
        for entry in converted:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(f"Conversion complete:")
    print(f"  Input:         {args.input} ({i} lines)")
    print(f"  Output:        {output_path}")
    print(f"  Converted:     {len(converted)}")
    print(f"  Skipped:       {skipped}")
    print(f"  Needs review:  {needs_review} (entries using run_command or unknown tools)")
    print()
    print("Next steps:")
    print("  1. Review entries marked 'needs_review' — they used tools not in the new manifest")
    print("  2. Run validate_dataset.py on the output to check for issues")
    print("  3. Manually improve explanations and summaries")


if __name__ == "__main__":
    main()
