from __future__ import annotations

import argparse
import sys
from typing import TYPE_CHECKING

from vermyth.cli.format import format_aspects_table, format_registered_sigils_table
from vermyth.registry import AspectRegistry

if TYPE_CHECKING:
    from vermyth.cli.main import VermythCLI


def cmd_register_aspect(
    cli: "VermythCLI", aspect_id: str, polarity: int, entropy_coefficient: float, symbol: str
) -> None:
    try:
        cli._tools.tool_register_aspect(
            aspect_id=aspect_id,
            polarity=polarity,
            entropy_coefficient=entropy_coefficient,
            symbol=symbol,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)


def cmd_register_sigil(cli: "VermythCLI", payload: dict) -> None:
    try:
        cli._tools.tool_register_sigil(payload)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)


def cmd_aspects(cli: "VermythCLI") -> None:
    _ = cli
    reg = AspectRegistry.get()
    canonical = [
        {
            "name": a.name,
            "polarity": a.polarity,
            "entropy_coefficient": a.entropy_coefficient,
            "symbol": a.symbol,
        }
        for a in reg.full_order
        if not reg.is_registered(a.name)
    ]
    registered = [
        {
            "name": a.name,
            "polarity": a.polarity,
            "entropy_coefficient": a.entropy_coefficient,
            "symbol": a.symbol,
        }
        for a in reg.registered_aspects()
    ]
    print(format_aspects_table(canonical, registered))


def cmd_registered_sigils(cli: "VermythCLI") -> None:
    try:
        rows = cli._tools.tool_registered_sigils()
        print(format_registered_sigils_table(rows))
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)


def register_subparsers(subs: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    ra = subs.add_parser("register-aspect", help="Register a new aspect.")
    ra.add_argument("aspect_id", metavar="ASPECT_ID")
    ra.add_argument("--polarity", type=int, choices=[-1, 1], required=True)
    ra.add_argument("--entropy-coefficient", type=float, required=True, dest="entropy_coefficient")
    ra.add_argument("--symbol", required=True)

    rs = subs.add_parser("register-sigil", help="Register a named sigil override.")
    rs.add_argument("name", metavar="NAME")
    rs.add_argument("--aspects", nargs="+", required=True)
    rs.add_argument("--effect-class", required=True, dest="effect_class")
    rs.add_argument("--resonance-ceiling", type=float, required=True, dest="resonance_ceiling")
    rs.add_argument(
        "--contradiction-severity",
        required=True,
        dest="contradiction_severity",
    )
    rs.add_argument("--allow-override", action="store_true", default=False, dest="allow_override")

    subs.add_parser("aspects", help="List all aspects (canonical + registered).")
    subs.add_parser("registered-sigils", help="List registered sigils.")


def _dispatch_register_aspect(cli: "VermythCLI", ns: argparse.Namespace) -> None:
    cli.cmd_register_aspect(
        aspect_id=ns.aspect_id,
        polarity=ns.polarity,
        entropy_coefficient=ns.entropy_coefficient,
        symbol=ns.symbol,
    )


def _dispatch_register_sigil(cli: "VermythCLI", ns: argparse.Namespace) -> None:
    cli.cmd_register_sigil(
        {
            "name": ns.name,
            "aspects": ns.aspects,
            "effect_class": ns.effect_class,
            "resonance_ceiling": ns.resonance_ceiling,
            "contradiction_severity": ns.contradiction_severity,
            "allow_override": ns.allow_override,
        }
    )


def _dispatch_aspects(cli: "VermythCLI", ns: argparse.Namespace) -> None:
    _ = ns
    cli.cmd_aspects()


def _dispatch_registered_sigils(cli: "VermythCLI", ns: argparse.Namespace) -> None:
    _ = ns
    cli.cmd_registered_sigils()


DISPATCH = {
    "register-aspect": _dispatch_register_aspect,
    "register-sigil": _dispatch_register_sigil,
    "aspects": _dispatch_aspects,
    "registered-sigils": _dispatch_registered_sigils,
}
