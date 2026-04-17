from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _line_count(path: str) -> int:
    with (ROOT / path).open(encoding="utf-8") as handle:
        return sum(1 for _ in handle)


def test_monolith_line_count_ceilings() -> None:
    max_lines = 400
    excluded = {
        "vermyth/mcp/tool_definitions.py",
        "vermyth/schema/_legacy.py",
        "vermyth/contracts/_legacy.py",
        "vermyth/mcp/tools/casting/_legacy.py",
        "vermyth/mcp/tools/facade.py",
        "vermyth/mcp/server.py",
        "vermyth/cli/main.py",
    }
    overages: list[str] = []
    for py in sorted((ROOT / "vermyth").rglob("*.py")):
        rel = py.relative_to(ROOT).as_posix()
        if rel in excluded:
            continue
        lines = _line_count(rel)
        if lines > max_lines:
            overages.append(f"{rel} has {lines} lines (ceiling {max_lines})")
    assert not overages, "\n".join(overages)
