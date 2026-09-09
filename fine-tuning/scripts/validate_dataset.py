#!/usr/bin/env python3
"""Validate NeoMint structured training data against the action-plan schema and tool manifest.

Checks:
  - JSON parse validity on every line
  - Required fields: id, messages, tool_manifest, target, labels
  - Target conforms to action-plan schema (kind: plan/clarification/refusal)
  - Tool names in targets exist in the tool manifest
  - Plan actions have required fields: tool, arguments, explanation
  - No duplicate IDs
  - Category distribution statistics

Usage:
    python validate_dataset.py ../data/train.jsonl
    python validate_dataset.py ../data/train.jsonl ../data/validation.jsonl ../data/test.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

# Resolve paths relative to this script
SCRIPT_DIR = Path(__file__).resolve().parent
SCHEMAS_DIR = SCRIPT_DIR.parent / "schemas"

REQUIRED_FIELDS = {"id", "messages", "tool_manifest", "target", "labels"}
VALID_KINDS = {"plan", "clarification", "refusal"}


def load_manifest_tools() -> set[str]:
    """Load tool names from the tool manifest."""
    manifest_path = SCHEMAS_DIR / "tool-manifest.json"
    if not manifest_path.exists():
        print(f"Warning: Tool manifest not found at {manifest_path}")
        return set()
    with manifest_path.open("r", encoding="utf-8") as f:
        manifest = json.load(f)
    return {tool["name"] for tool in manifest.get("tools", [])}


def validate_target(target: dict, manifest_tools: set[str], line_num: int) -> list[str]:
    """Validate a target object against the action-plan schema."""
    issues: list[str] = []

    kind = target.get("kind")
    if kind not in VALID_KINDS:
        issues.append(f"Line {line_num}: Invalid target kind '{kind}' (expected: {VALID_KINDS})")
        return issues

    if kind == "plan":
        if "user_facing_summary" not in target:
            issues.append(f"Line {line_num}: Plan missing 'user_facing_summary'")
        if "actions" not in target:
            issues.append(f"Line {line_num}: Plan missing 'actions'")
            return issues
        actions = target["actions"]
        if not isinstance(actions, list) or len(actions) == 0:
            issues.append(f"Line {line_num}: Plan 'actions' must be a non-empty list")
            return issues
        if len(actions) > 5:
            issues.append(f"Line {line_num}: Plan has {len(actions)} actions (max 5)")

        for i, action in enumerate(actions):
            prefix = f"Line {line_num}, action[{i}]"
            if "tool" not in action:
                issues.append(f"{prefix}: Missing 'tool' field")
            elif manifest_tools and action["tool"] not in manifest_tools:
                issues.append(f"{prefix}: Unknown tool '{action['tool']}' (not in manifest)")
            if "arguments" not in action:
                issues.append(f"{prefix}: Missing 'arguments' field")
            elif not isinstance(action["arguments"], dict):
                issues.append(f"{prefix}: 'arguments' must be an object")
            if "explanation" not in action:
                issues.append(f"{prefix}: Missing 'explanation' field")

        # Check for policy fields the model should NOT produce
        forbidden_fields = {"requires_confirmation", "permission", "risk", "execute", "risk_level"}
        for field in forbidden_fields:
            if field in target:
                issues.append(f"Line {line_num}: Plan contains forbidden field '{field}' (owned by policy engine)")
            for action in actions:
                if field in action:
                    issues.append(f"Line {line_num}: Action contains forbidden field '{field}' (owned by policy engine)")

    elif kind == "clarification":
        if "question" not in target:
            issues.append(f"Line {line_num}: Clarification missing 'question'")
        if "reason" not in target:
            issues.append(f"Line {line_num}: Clarification missing 'reason'")

    elif kind == "refusal":
        if "message" not in target:
            issues.append(f"Line {line_num}: Refusal missing 'message'")

    return issues


def validate_entry(entry: dict, manifest_tools: set[str], line_num: int) -> list[str]:
    """Validate a single dataset entry."""
    issues: list[str] = []

    # Check required fields
    for field in REQUIRED_FIELDS:
        if field not in entry:
            issues.append(f"Line {line_num}: Missing required field '{field}'")

    if issues:
        return issues  # Can't validate further without required fields

    # Validate messages
    messages = entry["messages"]
    if not isinstance(messages, list) or len(messages) < 2:
        issues.append(f"Line {line_num}: 'messages' must have at least 2 entries (system + user)")
    else:
        if messages[0].get("role") != "system":
            issues.append(f"Line {line_num}: First message must have role 'system'")
        if messages[-1].get("role") != "user":
            issues.append(f"Line {line_num}: Last message must have role 'user'")

    # Validate tool_manifest
    tm = entry["tool_manifest"]
    if not isinstance(tm, list) or len(tm) == 0:
        issues.append(f"Line {line_num}: 'tool_manifest' must be a non-empty list")

    # Validate target
    target = entry["target"]
    if not isinstance(target, dict):
        issues.append(f"Line {line_num}: 'target' must be an object")
    else:
        issues.extend(validate_target(target, manifest_tools, line_num))

    # Validate labels
    labels = entry["labels"]
    if not isinstance(labels, dict):
        issues.append(f"Line {line_num}: 'labels' must be an object")
    else:
        if "category" not in labels:
            issues.append(f"Line {line_num}: Labels missing 'category'")

    # Validate id is a string
    if not isinstance(entry["id"], str) or len(entry["id"].strip()) == 0:
        issues.append(f"Line {line_num}: 'id' must be a non-empty string")

    return issues


def validate_file(path: Path, manifest_tools: set[str]) -> tuple[list[str], dict, list[str]]:
    """Validate an entire JSONL file. Returns (issues, stats, ids)."""
    issues: list[str] = []
    ids: list[str] = []
    categories: Counter[str] = Counter()
    kinds: Counter[str] = Counter()
    tools_used: Counter[str] = Counter()
    total = 0

    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                issues.append(f"Line {i}: Empty line")
                continue

            try:
                entry = json.loads(line)
            except json.JSONDecodeError as exc:
                issues.append(f"Line {i}: JSON parse error: {exc}")
                continue

            total += 1
            entry_issues = validate_entry(entry, manifest_tools, i)
            issues.extend(entry_issues)

            if not entry_issues:
                ids.append(entry["id"])
                categories[entry["labels"]["category"]] += 1
                kind = entry["target"]["kind"]
                kinds[kind] += 1
                if kind == "plan":
                    for action in entry["target"]["actions"]:
                        tools_used[action["tool"]] += 1

    # Check for duplicate IDs
    id_counts = Counter(ids)
    for eid, count in id_counts.items():
        if count > 1:
            issues.append(f"Duplicate ID: '{eid}' appears {count} times")

    stats = {
        "total_entries": total,
        "valid_entries": total - len([i for i in issues if "Line" in i]),
        "kinds": dict(kinds.most_common()),
        "categories": dict(categories.most_common()),
        "tools_used": dict(tools_used.most_common()),
    }

    return issues, stats, ids


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate NeoMint structured training data")
    parser.add_argument("files", type=Path, nargs="+", help="JSONL files to validate")
    args = parser.parse_args()

    manifest_tools = load_manifest_tools()
    if manifest_tools:
        print(f"Loaded {len(manifest_tools)} tools from manifest: {', '.join(sorted(manifest_tools))}\n")

    all_ids: list[str] = []
    total_issues = 0

    for path in args.files:
        if not path.exists():
            print(f"Error: File not found: {path}")
            sys.exit(1)

        print(f"{'=' * 60}")
        print(f"Validating: {path}")
        print(f"{'=' * 60}")

        issues, stats, ids = validate_file(path, manifest_tools)
        all_ids.extend(ids)

        print(f"\n  Total entries:  {stats['total_entries']}")
        print(f"  Valid entries:  {stats['valid_entries']}")

        print(f"\n  Response kinds:")
        for kind, count in stats["kinds"].items():
            print(f"    {kind}: {count}")

        print(f"\n  Categories:")
        for cat, count in stats["categories"].items():
            print(f"    {cat}: {count}")

        print(f"\n  Tools used:")
        for tool, count in stats["tools_used"].items():
            print(f"    {tool}: {count}")

        if issues:
            print(f"\n  Issues ({len(issues)}):")
            for issue in issues:
                print(f"    [!] {issue}")
            total_issues += len(issues)
        else:
            print(f"\n  No issues found!")

        print()

    # Cross-file duplicate check
    if len(args.files) > 1:
        id_counts = Counter(all_ids)
        cross_dups = {eid: count for eid, count in id_counts.items() if count > 1}
        if cross_dups:
            print("Cross-file duplicate IDs:")
            for eid, count in cross_dups.items():
                print(f"  [!] '{eid}' appears in {count} files")
                total_issues += 1

    sys.exit(1 if total_issues > 0 else 0)


if __name__ == "__main__":
    main()
