import pytest

from vermyth.cli.main import VermythCLI
from vermyth.engine.composition import CompositionEngine
from vermyth.engine.resonance import ResonanceEngine
from vermyth.grimoire.store import Grimoire
from vermyth.mcp.tools import VermythTools
from vermyth.observability import EventBus


def _intent():
    return {
        "objective": "study the pattern",
        "scope": "local workspace",
        "reversibility": "REVERSIBLE",
        "side_effect_tolerance": "HIGH",
    }

def test_divergence_reports_listing(make_tools):
    parent = make_tools.tool_cast(aspects=["MIND", "LIGHT"], intent=_intent())
    child = make_tools.tool_cast(
        aspects=["MIND", "LIGHT"],
        intent=_intent(),
        parent_cast_id=parent["cast_id"],
    )
    rows = make_tools.tool_divergence_reports(limit=10)
    assert any(r["cast_id"] == child["cast_id"] for r in rows)


def test_drift_branches(make_tools):
    parent = make_tools.tool_cast(aspects=["VOID", "FORM"], intent=_intent())
    child = make_tools.tool_cast(
        aspects=["VOID", "FORM"],
        intent=_intent(),
        parent_cast_id=parent["cast_id"],
    )
    branches = make_tools.tool_drift_branches(limit=10)
    assert branches
    # The child's cast is in some branch id.
    bid = child["lineage"]["branch_id"]
    assert any(b["branch_id"] == bid for b in branches)


def test_lineage_drift_summary(make_tools):
    r1 = make_tools.tool_cast(aspects=["VOID", "FORM"], intent=_intent())
    r2 = make_tools.tool_cast(
        aspects=["VOID", "FORM"],
        intent=_intent(),
        parent_cast_id=r1["cast_id"],
    )
    rep = make_tools.tool_lineage_drift(cast_id=r2["cast_id"], max_depth=10, top_k=2)
    assert rep["chain_length"] >= 2
    assert rep["hops"]
    assert rep["hops"][-1]["cast_id"] == r2["cast_id"]


def test_backfill_divergence_cli(tmp_path, capsys):
    db = tmp_path / "cli_obs.db"
    eng = ResonanceEngine(CompositionEngine(), None)
    g = Grimoire(db_path=db)
    tools = VermythTools(eng, g)

    parent = tools.tool_cast(aspects=["MIND", "LIGHT"], intent=_intent())
    child = tools.tool_cast(
        aspects=["MIND", "LIGHT"],
        intent=_intent(),
        parent_cast_id=parent["cast_id"],
    )

    # Delete the divergence report to simulate missing rows.
    g._conn.execute("DELETE FROM divergence_reports WHERE cast_id = ?", (child["cast_id"],))
    g._conn.commit()

    cli = VermythCLI(engine=eng, grimoire=g)
    cli.run(["backfill-divergence", "--limit", "50"])
    out = capsys.readouterr().out
    assert "Backfilled" in out or "No missing" in out
    # Should exist again
    rep = tools.tool_divergence(cast_id=child["cast_id"])
    assert rep["cast_id"] == child["cast_id"]


def test_cast_and_decide_emit_events(make_tools):
    cast = make_tools.tool_cast(aspects=["MIND", "LIGHT"], intent=_intent())
    decide = make_tools.tool_decide(intent=_intent(), aspects=["MIND", "LIGHT"])
    events = make_tools.tool_events_tail(n=20)
    types = [e["event_type"] for e in events]
    assert "cast" in types
    assert "decide" in types
    assert any(e.get("cast_id") == cast["cast_id"] for e in events if e["event_type"] == "cast")
    assert any(
        e.get("cast_id") == decide["cast"]["cast_id"]
        for e in events
        if e["event_type"] == "decide"
    )


def test_auto_cast_emits_step_events(make_tools):
    _ = make_tools.tool_auto_cast(
        vector=[0.0, 1.0, 0.2, 0.1, 0.0, 0.6],
        intent=_intent(),
        max_depth=3,
        include_diagnostics=True,
    )
    steps = make_tools.tool_events_tail(n=50, event_type="auto_cast_step")
    assert len(steps) >= 1


def test_event_bus_jsonl_sink_and_subscription(tmp_path):
    log_path = tmp_path / "events.jsonl"
    bus = EventBus()
    seen = []
    unsubscribe = bus.subscribe(lambda ev: seen.append(ev.event_type))
    import os

    old = os.environ.get("VERMYTH_EVENT_LOG")
    os.environ["VERMYTH_EVENT_LOG"] = str(log_path)
    try:
        bus.emit_event("cast", {"cast_id": "abc"}, cast_id="abc")
    finally:
        if old is None:
            os.environ.pop("VERMYTH_EVENT_LOG", None)
        else:
            os.environ["VERMYTH_EVENT_LOG"] = old
    unsubscribe()
    bus.emit_event("decide", {"cast_id": "abc"}, cast_id="abc")
    assert seen == ["cast"]
    text = log_path.read_text(encoding="utf-8")
    assert "\"event_type\": \"cast\"" in text

