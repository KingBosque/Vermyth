"""
Real external benchmark path: network fetch + Vermyth policy decision.

This is intentionally distinct from dry-run adapters: it performs outbound HTTP
and records structured artifacts under benchmarks/artifacts/.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _git_sha() -> str:
    try:
        return (
            subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                cwd=str(ROOT),
                stderr=subprocess.DEVNULL,
            )
            .decode()
            .strip()
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def run_real_benchmark(
    *,
    url: str | None = None,
    artifact_dir: Path | None = None,
) -> dict:
    from vermyth.bootstrap import build_tools

    fetch_url = url or os.environ.get(
        "VERMYTH_BENCHMARK_EXTERNAL_URL",
        "https://example.com",
    )
    with urllib.request.urlopen(fetch_url, timeout=30) as resp:
        body = resp.read(64_000)
        status = resp.status

    digest = hashlib.sha256(body).hexdigest()[:16]
    with TemporaryDirectory() as td:
        _g, _c, _engine, tools = build_tools(db_path=Path(td) / "bench.db")
        out = tools.tool_decide(
            intent={
                "objective": f"Evaluate external fetch integrity (sha256 prefix {digest})",
                "scope": "benchmark",
                "reversibility": "REVERSIBLE",
                "side_effect_tolerance": "LOW",
            },
            aspects=["MIND"],
        )
        _g.close()

    record = {
        "mode": "real_external_http",
        "integration": "urllib_fetch_plus_decide",
        "fetch_url": fetch_url,
        "http_status": status,
        "content_sha256_prefix": digest,
        "decision": out.get("decision"),
        "git_sha": _git_sha(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    artifact_dir = artifact_dir or (ROOT / "benchmarks" / "artifacts")
    artifact_dir.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = artifact_dir / f"external_run_{run_id}.json"
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    record["artifact_path"] = str(path)
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=None, help="URL to fetch (default: env or example.com)")
    parser.add_argument("--artifact-dir", type=Path, default=None)
    args = parser.parse_args()
    rec = run_real_benchmark(url=args.url, artifact_dir=args.artifact_dir)
    print(json.dumps(rec, indent=2))


if __name__ == "__main__":
    main()
