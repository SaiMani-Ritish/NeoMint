#!/usr/bin/env python3
"""NeoMint MCP CLI."""

from __future__ import annotations

import argparse

from neomint_mcp.session import run_session


def main() -> None:
    parser = argparse.ArgumentParser(description="NeoMint local-first tooling")
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("session", help="Run the Session 0 text-first local agent shell")
    args = parser.parse_args()

    if args.command == "session":
        run_session()
        return

    parser.print_help()


if __name__ == "__main__":
    main()
