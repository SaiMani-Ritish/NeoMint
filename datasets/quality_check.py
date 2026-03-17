#!/usr/bin/env python3
"""Dataset quality checker for NeoMint training data.

Validates JSONL files for:
  - JSON parse errors (malformed lines)
  - Missing required fields (instruction, input, output)
  - Empty fields that should have content
  - Exact duplicate entries
  - Near-duplicate instructions (label leakage)
  - Format consistency (tool_call blocks well-formed)
  - Basic statistics (category distribution, avg lengths)

Usage:
    python quality_check.py datasets/neomint_train.jsonl
    python quality_check.py datasets/neomint_train.jsonl --fix --output datasets/cleaned.jsonl
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path


REQUIRED_FIELDS = {"instruction", "input", "output"}

TOOL_CALL_PATTERN = re.compile(r"```tool_call\s*\n\s*(\{.*?\})\s*\n\s*```", re.DOTALL)
TOOL_NAMES = {
    "list_files", "read_file", "write_file",
    "run_command", "open_application",
    "get_clipboard", "set_clipboard",
}


def load_jsonl(path: Path) -> list[tuple[int, dict | None, str | None]]:
    """Load a JSONL file, returning (line_num, parsed_dict_or_None, error_or_None)."""
    results: list[tuple[int, dict | None, str | None]] = []
    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                results.append((i, None, "Empty line"))
                continue
            try:
                obj = json.loads(line)
                results.append((i, obj, None))
            except json.JSONDecodeError as exc:
                results.append((i, None, f"JSON parse error: {exc}"))
    return results


def check_fields(entry: dict, line_num: int) -> list[str]:
    """Check that all required fields exist and are non-empty where expected."""
    issues: list[str] = []
    for field in REQUIRED_FIELDS:
        if field not in entry:
            issues.append(f"Line {line_num}: Missing field '{field}'")
        elif not isinstance(entry[field], str):
            issues.append(f"Line {line_num}: Field '{field}' is not a string")

    if "instruction" in entry and isinstance(entry["instruction"], str):
        if len(entry["instruction"].strip()) == 0:
            issues.append(f"Line {line_num}: 'instruction' is empty")

    if "output" in entry and isinstance(entry["output"], str):
        if len(entry["output"].strip()) == 0:
            issues.append(f"Line {line_num}: 'output' is empty")

    return issues


def check_tool_calls(entry: dict, line_num: int) -> list[str]:
    """Validate tool_call blocks in the output."""
    issues: list[str] = []
    output = entry.get("output", "")
    if not isinstance(output, str):
        return issues

    matches = TOOL_CALL_PATTERN.findall(output)
    for match in matches:
        try:
            call = json.loads(match)
        except json.JSONDecodeError:
            issues.append(f"Line {line_num}: Malformed JSON in tool_call block")
            continue

        if "tool" not in call:
            issues.append(f"Line {line_num}: tool_call missing 'tool' field")
        elif call["tool"] not in TOOL_NAMES:
            issues.append(
                f"Line {line_num}: Unknown tool '{call['tool']}' in tool_call"
            )

        if "args" not in call:
            issues.append(f"Line {line_num}: tool_call missing 'args' field")
        elif not isinstance(call["args"], dict):
            issues.append(f"Line {line_num}: tool_call 'args' is not a dict")

    return issues


def find_duplicates(
    entries: list[tuple[int, dict]],
) -> tuple[list[str], set[int]]:
    """Find exact duplicate entries and near-duplicate instructions."""
    issues: list[str] = []
    dup_lines: set[int] = set()

    seen_exact: dict[str, int] = {}
    seen_instructions: dict[str, int] = {}

    for line_num, entry in entries:
        key = json.dumps(entry, sort_keys=True)
        if key in seen_exact:
            issues.append(
                f"Line {line_num}: Exact duplicate of line {seen_exact[key]}"
            )
            dup_lines.add(line_num)
        else:
            seen_exact[key] = line_num

        instr = entry.get("instruction", "").strip().lower()
        inp = entry.get("input", "").strip().lower()
        instr_key = f"{instr}||{inp}"

        if instr_key in seen_instructions:
            first_line = seen_instructions[instr_key]
            if line_num not in dup_lines:
                issues.append(
                    f"Line {line_num}: Near-duplicate instruction+input "
                    f"(same as line {first_line}) — possible label leakage"
                )
        else:
            seen_instructions[instr_key] = line_num

    return issues, dup_lines


def compute_stats(entries: list[tuple[int, dict]]) -> dict:
    """Compute dataset statistics."""
    categories: Counter[str] = Counter()
    tool_usage: Counter[str] = Counter()
    instr_lengths: list[int] = []
    output_lengths: list[int] = []
    has_tool_call = 0
    has_context = 0
    is_clarification = 0

    for _, entry in entries:
        instr = entry.get("instruction", "")
        output = entry.get("output", "")
        inp = entry.get("input", "")

        instr_lengths.append(len(instr))
        output_lengths.append(len(output))

        if inp.strip():
            has_context += 1

        matches = TOOL_CALL_PATTERN.findall(output)
        if matches:
            has_tool_call += 1
            for m in matches:
                try:
                    call = json.loads(m)
                    tool_usage[call.get("tool", "unknown")] += 1
                except json.JSONDecodeError:
                    pass
        else:
            is_clarification += 1

        if any(
            kw in instr.lower()
            for kw in ["list", "show me what", "what files", "what's in"]
        ):
            categories["file_inspection"] += 1
        elif any(
            kw in instr.lower()
            for kw in ["read", "open the file", "contents of", "what does"]
        ):
            categories["file_read"] += 1
        elif any(
            kw in instr.lower()
            for kw in ["write", "create", "save", "overwrite", "make a new"]
        ):
            categories["file_write"] += 1
        elif any(
            kw in instr.lower()
            for kw in ["open", "launch", "start"]
        ):
            categories["app_launch"] += 1
        elif any(
            kw in instr.lower()
            for kw in ["clipboard", "copied", "copy"]
        ):
            categories["clipboard"] += 1
        elif any(
            kw in instr.lower()
            for kw in [
                "disk", "memory", "cpu", "uptime", "kernel",
                "hostname", "username", "date", "time", "version",
                "ram", "process", "running", "status", "installed",
            ]
        ):
            categories["system_info"] += 1
        elif inp.strip() or "and" in instr.lower():
            categories["multi_step"] += 1
        else:
            categories["shell_command"] += 1

    total = len(entries)
    return {
        "total_entries": total,
        "has_tool_call": has_tool_call,
        "clarification_or_conversation": is_clarification,
        "has_context_input": has_context,
        "avg_instruction_length": round(sum(instr_lengths) / max(total, 1), 1),
        "avg_output_length": round(sum(output_lengths) / max(total, 1), 1),
        "tool_usage": dict(tool_usage.most_common()),
        "categories": dict(categories.most_common()),
    }


def run_quality_check(path: Path) -> tuple[list[str], dict, list[tuple[int, dict]]]:
    """Run all quality checks and return (issues, stats, valid_entries)."""
    all_issues: list[str] = []

    raw = load_jsonl(path)
    valid_entries: list[tuple[int, dict]] = []

    for line_num, obj, error in raw:
        if error:
            all_issues.append(f"Line {line_num}: {error}")
            continue
        assert obj is not None
        field_issues = check_fields(obj, line_num)
        all_issues.extend(field_issues)
        if not field_issues:
            tool_issues = check_tool_calls(obj, line_num)
            all_issues.extend(tool_issues)
            valid_entries.append((line_num, obj))

    dup_issues, _ = find_duplicates(valid_entries)
    all_issues.extend(dup_issues)

    stats = compute_stats(valid_entries)
    return all_issues, stats, valid_entries


def main() -> None:
    parser = argparse.ArgumentParser(description="NeoMint dataset quality checker")
    parser.add_argument("file", type=Path, help="Path to the JSONL dataset")
    parser.add_argument(
        "--fix", action="store_true",
        help="Write a cleaned version (removes exact duplicates and invalid entries)",
    )
    parser.add_argument(
        "--output", type=Path, default=None,
        help="Output path for the cleaned file (default: <input>_cleaned.jsonl)",
    )
    args = parser.parse_args()

    if not args.file.exists():
        print(f"Error: File not found: {args.file}")
        sys.exit(1)

    print(f"Checking: {args.file}\n")

    issues, stats, valid_entries = run_quality_check(args.file)

    print("=" * 60)
    print("DATASET STATISTICS")
    print("=" * 60)
    print(f"  Total entries:            {stats['total_entries']}")
    print(f"  Entries with tool calls:  {stats['has_tool_call']}")
    print(f"  Clarification/convo:      {stats['clarification_or_conversation']}")
    print(f"  With context input:       {stats['has_context_input']}")
    print(f"  Avg instruction length:   {stats['avg_instruction_length']} chars")
    print(f"  Avg output length:        {stats['avg_output_length']} chars")
    print()

    print("  Tool usage:")
    for tool, count in stats["tool_usage"].items():
        print(f"    {tool}: {count}")
    print()

    print("  Category distribution:")
    for cat, count in stats["categories"].items():
        print(f"    {cat}: {count}")
    print()

    print("=" * 60)
    print("QUALITY ISSUES")
    print("=" * 60)
    if issues:
        for issue in issues:
            print(f"  [!] {issue}")
        print(f"\n  Total issues: {len(issues)}")
    else:
        print("  No issues found!")
    print()

    if args.fix:
        out_path = args.output or args.file.with_name(
            args.file.stem + "_cleaned.jsonl"
        )
        seen: set[str] = set()
        cleaned: list[dict] = []
        for _, entry in valid_entries:
            key = json.dumps(entry, sort_keys=True)
            if key not in seen:
                seen.add(key)
                cleaned.append(entry)

        with out_path.open("w", encoding="utf-8") as f:
            for entry in cleaned:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        print(f"Cleaned dataset written to: {out_path}")
        print(f"  Original: {stats['total_entries']} entries")
        print(f"  Cleaned:  {len(cleaned)} entries")

    sys.exit(1 if issues else 0)


if __name__ == "__main__":
    main()
