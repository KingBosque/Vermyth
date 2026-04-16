"""Update benchmarks/report.md with dry-run metrics from OSWorld/WebArena adapters."""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from benchmarks.adapters.osworld import run_dry_run as run_osworld_dry_run
from benchmarks.adapters.webarena import run_dry_run as run_webarena_dry_run


def _repo_root() -> Path:
    return _ROOT


def _format_section(
    *,
    osw: dict[str, float],
    web: dict[str, float],
    updated: str,
) -> str:
    return (
        "## External task evaluation (dry run)\n\n"
        f"- **osworld**: success_rate={osw['success_rate']:.4f}; reshape_rate={osw['reshape_rate']:.4f}; "
        f"samples={int(osw['samples'])} (updated {updated})\n"
        f"- **webarena**: success_rate={web['success_rate']:.4f}; reshape_rate={web['reshape_rate']:.4f}; "
        f"samples={int(web['samples'])} (updated {updated})\n"
        "- note: adapter-level checks only; not equivalent to full live-environment benchmark runs.\n"
    )


def update_report(
    *,
    report_path: Path,
    osworld_tasks: Path,
    webarena_tasks: Path,
) -> str:
    osw = run_osworld_dry_run(osworld_tasks)
    web = run_webarena_dry_run(webarena_tasks)
    updated = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    new_section = _format_section(osw=osw, web=web, updated=updated)
    text = report_path.read_text(encoding="utf-8")
    pattern = re.compile(
        r"## External task evaluation \(dry run\).*?(?=\n## |\Z)",
        re.DOTALL,
    )
    if not pattern.search(text):
        raise ValueError(f"Could not find '## External task evaluation (dry run)' in {report_path}")
    out = pattern.sub(new_section.rstrip() + "\n\n", text, count=1)
    report_path.write_text(out, encoding="utf-8")
    return out


def main() -> None:
    root = _repo_root()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--report",
        type=Path,
        default=root / "benchmarks" / "report.md",
    )
    parser.add_argument(
        "--osworld-tasks",
        type=Path,
        default=root / "benchmarks" / "fixtures" / "osworld_tasks_dry_run.json",
    )
    parser.add_argument(
        "--webarena-tasks",
        type=Path,
        default=root / "benchmarks" / "fixtures" / "webarena_tasks_dry_run.json",
    )
    args = parser.parse_args()
    webarena_path = args.webarena_tasks
    update_report(
        report_path=args.report,
        osworld_tasks=args.osworld_tasks,
        webarena_tasks=webarena_path,
    )
    print(f"Updated {args.report}")


if __name__ == "__main__":
    main()
