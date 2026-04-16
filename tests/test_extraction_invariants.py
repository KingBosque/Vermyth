from __future__ import annotations

from pathlib import Path

from vermyth.grimoire.store import Grimoire
from vermyth.mcp.server import TOOL_DEFINITIONS, TOOL_DISPATCH


def test_decide_tool_definition_and_dispatch_are_registered() -> None:
    names = [entry["name"] for entry in TOOL_DEFINITIONS]
    assert "decide" in names
    assert "decide" in TOOL_DISPATCH


def test_grimoire_policy_methods_delegate_to_decision_repository(tmp_path: Path) -> None:
    grimoire = Grimoire(tmp_path / "grimoire.db")
    calls: list[str] = []

    class _StubRepo:
        def write_policy_decision(self, _decision) -> None:
            calls.append("write")

        def read_policy_decision(self, _decision_id: str):
            calls.append("read")
            return "read-result"

        def query_policy_decisions(self, **_kwargs):
            calls.append("query")
            return ["query-result"]

    grimoire.decisions = _StubRepo()
    grimoire.write_policy_decision(None)  # type: ignore[arg-type]
    read_value = grimoire.read_policy_decision("decision-id")
    query_value = grimoire.query_policy_decisions(limit=1)
    grimoire.close()

    assert calls == ["write", "read", "query"]
    assert read_value == "read-result"
    assert query_value == ["query-result"]

