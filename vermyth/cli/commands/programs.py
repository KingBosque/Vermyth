from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vermyth.cli.main import VermythCLI


def cmd_compile_program(cli: "VermythCLI", path: str) -> None:
    try:
        raw = Path(path).read_text(encoding="utf-8")
        payload = json.loads(raw)
        out = cli._tools.tool_compile_program(payload)
        print(out)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)


def cmd_execute_program(cli: "VermythCLI", program_id: str) -> None:
    try:
        out = cli._tools.tool_execute_program(program_id)
        print(out)
    except KeyError:
        print(f"Program not found: {program_id}", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)


def cmd_program_status(cli: "VermythCLI", program_id: str) -> None:
    try:
        out = cli._tools.tool_program_status(program_id)
        print(out)
    except KeyError:
        print(f"Program not found: {program_id}", file=sys.stderr)
        sys.exit(1)


def cmd_list_programs(cli: "VermythCLI", limit: int) -> None:
    out = cli._tools.tool_list_programs(limit=limit)
    print(out)


def cmd_execution_status(cli: "VermythCLI", execution_id: str) -> None:
    try:
        out = cli._tools.tool_execution_status(execution_id)
        print(out)
    except KeyError:
        print(f"Execution not found: {execution_id}", file=sys.stderr)
        sys.exit(1)


def cmd_execution_receipt(cli: "VermythCLI", execution_id: str) -> None:
    try:
        out = cli._tools.tool_execution_receipt(execution_id)
        print(out)
    except KeyError:
        print(f"Execution receipt not found: {execution_id}", file=sys.stderr)
        sys.exit(1)


def register_subparsers(subs: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    cp = subs.add_parser("compile-program", help="Compile a semantic program JSON.")
    cp.add_argument("path", metavar="PATH")

    ep = subs.add_parser("execute-program", help="Execute a compiled semantic program.")
    ep.add_argument("program_id", metavar="PROGRAM_ID")

    ps = subs.add_parser("program-status", help="Show semantic program metadata.")
    ps.add_argument("program_id", metavar="PROGRAM_ID")

    lp = subs.add_parser("list-programs", help="List semantic programs.")
    lp.add_argument("--limit", type=int, default=50)

    es = subs.add_parser("execution-status", help="Show program execution status.")
    es.add_argument("execution_id", metavar="EXECUTION_ID")

    er = subs.add_parser("execution-receipt", help="Show execution receipt details.")
    er.add_argument("execution_id", metavar="EXECUTION_ID")


def _dispatch_compile_program(cli: "VermythCLI", ns: argparse.Namespace) -> None:
    cli.cmd_compile_program(path=ns.path)


def _dispatch_execute_program(cli: "VermythCLI", ns: argparse.Namespace) -> None:
    cli.cmd_execute_program(program_id=ns.program_id)


def _dispatch_program_status(cli: "VermythCLI", ns: argparse.Namespace) -> None:
    cli.cmd_program_status(program_id=ns.program_id)


def _dispatch_list_programs(cli: "VermythCLI", ns: argparse.Namespace) -> None:
    cli.cmd_list_programs(limit=int(ns.limit))


def _dispatch_execution_status(cli: "VermythCLI", ns: argparse.Namespace) -> None:
    cli.cmd_execution_status(execution_id=ns.execution_id)


def _dispatch_execution_receipt(cli: "VermythCLI", ns: argparse.Namespace) -> None:
    cli.cmd_execution_receipt(execution_id=ns.execution_id)


DISPATCH = {
    "compile-program": _dispatch_compile_program,
    "execute-program": _dispatch_execute_program,
    "program-status": _dispatch_program_status,
    "list-programs": _dispatch_list_programs,
    "execution-status": _dispatch_execution_status,
    "execution-receipt": _dispatch_execution_receipt,
}
