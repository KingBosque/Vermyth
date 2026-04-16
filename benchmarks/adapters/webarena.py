from __future__ import annotations

import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from vermyth.bootstrap import build_tools


def run_dry_run(tasks_path: Path) -> dict[str, float]:
    tasks = json.loads(tasks_path.read_text(encoding="utf-8"))
    total = len(tasks)
    ok = 0
    reshape = 0
    with TemporaryDirectory() as td:
        _grimoire, _composition, _engine, tools = build_tools(db_path=Path(td) / "webarena.db")
        for row in tasks:
            out = tools.tool_decide(intent=row["intent"], aspects=row.get("aspects"))
            action = out["decision"]["action"]
            if action == row.get("expected_action"):
                ok += 1
            if action == "RESHAPE":
                reshape += 1
        _grimoire.close()
    return {
        "success_rate": (ok / total) if total else 0.0,
        "reshape_rate": (reshape / total) if total else 0.0,
        "samples": float(total),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="python benchmarks/adapters/webarena.py")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Run against bundled dry-run fixtures.",
    )
    parser.add_argument(
        "--tasks",
        default="benchmarks/fixtures/webarena_tasks_dry_run.json",
    )
    args = parser.parse_args()
    if not args.dry_run:
        raise SystemExit("only --dry-run is implemented in this adapter")
    metrics = run_dry_run(Path(args.tasks))
    print(json.dumps({"benchmark": "webarena", "mode": "dry-run", **metrics}))

