"""CLI: print bundle adoption report (local telemetry)."""

from __future__ import annotations

import argparse
import json
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vermyth.cli.main import VermythCLI


def register_subparsers(
    subs: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    p = subs.add_parser(
        "arcane-bundle-report",
        help="Print derived bundle adoption report from local telemetry (enable VERMYTH_BUNDLE_TELEMETRY=1 first).",
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="Emit full JSON (default: short text summary).",
    )


def _dispatch_arcane_bundle_report(cli: "VermythCLI", ns: argparse.Namespace) -> None:
    _ = cli
    from vermyth.arcane.bundle_adoption_report import build_bundle_adoption_report

    r = build_bundle_adoption_report()
    if ns.json:
        print(json.dumps(r, indent=2))
        return
    if not r.get("telemetry_enabled"):
        print(
            "Telemetry is disabled. Set VERMYTH_BUNDLE_TELEMETRY=1 and exercise "
            "recommend/inspect/invoke paths, then re-run.",
            file=sys.stderr,
        )
        print(json.dumps(r, indent=2))
        return
    print("Bundle adoption report (local, approximate ratios)")
    print("  totals:", r.get("totals_by_event_type"))
    print("  top recommended:", r.get("top_by_recommended"))
    print("  top invoked:", r.get("top_by_invoked"))
    print("  top missed:", r.get("top_by_missed"))
    findings = r.get("findings") or []
    if findings:
        print("  findings:")
        for f in findings[:12]:
            print(f"   - [{f.get('severity')}] {f.get('message')}")
    else:
        print("  findings: (none)")
    print("\nFull JSON: vermyth arcane-bundle-report --json")


DISPATCH = {"arcane-bundle-report": _dispatch_arcane_bundle_report}
