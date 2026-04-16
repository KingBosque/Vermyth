import io
import json

import pytest

from vermyth.engine.composition import CompositionEngine
from vermyth.engine.resonance import ResonanceEngine
from vermyth.grimoire.store import Grimoire
from vermyth.mcp.protocol import ERROR_INVALID_PARAMS, ERROR_METHOD_NOT_FOUND
from vermyth.mcp.server import VermythMCPServer
from vermyth.mcp.tools import VermythTools


def test_vermyth_tools_importable():
    from vermyth.mcp.tools import VermythTools as VT

    assert VT is VermythTools


def test_tool_cast_returns_expected_keys(make_tools, valid_intent):
    out = make_tools.tool_cast(
        aspects=["MIND", "LIGHT"],
        intent=valid_intent,
    )
    for key in (
        "cast_id",
        "verdict",
        "resonance",
        "sigil_name",
        "casting_note",
        "semantic_vector",
        "intent_vector",
    ):
        assert key in out


def test_tool_cast_unknown_aspect_raises(make_tools, valid_intent):
    with pytest.raises(ValueError, match="Unknown aspect"):
        make_tools.tool_cast(aspects=["MIND", "NOTREAL"], intent=valid_intent)


def test_tool_cast_invalid_intent_raises_validation_error(make_tools):
    pydantic = pytest.importorskip("pydantic")
    with pytest.raises(pydantic.ValidationError):
        make_tools.tool_cast(
            aspects=["MIND", "LIGHT"],
            intent={"objective": "x", "scope": "y", "reversibility": "BAD", "side_effect_tolerance": "HIGH"},
        )


def test_tool_cast_projection_partial_without_backend(make_tools, valid_intent):
    out = make_tools.tool_cast(aspects=["MIND", "LIGHT"], intent=valid_intent)
    assert out["projection_method"] == "PARTIAL"


def test_tool_cast_twice_same_aspects_updates_single_seed_observed_count(
    make_tools,
    valid_intent,
):
    aspects = ["MIND", "LIGHT"]
    make_tools.tool_cast(aspects=aspects, intent=valid_intent)
    make_tools.tool_cast(aspects=aspects, intent=valid_intent)
    seeds = make_tools.tool_seeds(crystallized=None)
    assert len(seeds) == 1
    assert seeds[0]["observed_count"] == 2


def test_tool_cast_persists_seed_after_cast(make_tools, valid_intent):
    make_tools.tool_cast(aspects=["MIND", "LIGHT"], intent=valid_intent)
    seeds = make_tools.tool_seeds(None)
    assert len(seeds) >= 1


def test_tool_query_empty_fresh_grimoire(make_tools):
    assert make_tools.tool_query({}) == []


def test_tool_query_after_one_cast_returns_one(make_tools, valid_intent):
    make_tools.tool_cast(aspects=["MIND", "LIGHT"], intent=valid_intent)
    rows = make_tools.tool_query({})
    assert len(rows) == 1


def test_tool_query_verdict_filter_returns_matching_verdict(make_tools, valid_intent):
    make_tools.tool_cast(aspects=["MIND", "LIGHT"], intent=valid_intent)
    all_rows = make_tools.tool_query({})
    vt = all_rows[0]["verdict"]
    rows = make_tools.tool_query({"verdict_filter": vt, "limit": 20})
    assert len(rows) >= 1
    assert all(r["verdict"] == vt for r in rows)


def test_tool_semantic_search_wrong_vector_length(make_tools):
    with pytest.raises(ValueError, match="exactly 6"):
        make_tools.tool_semantic_search(
            proximity_vector=[0.0, 0.0],
            threshold=0.5,
            limit=10,
        )


def test_tool_semantic_search_threshold_out_of_range(make_tools):
    with pytest.raises(ValueError, match="threshold"):
        make_tools.tool_semantic_search(
            proximity_vector=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            threshold=1.5,
            limit=10,
        )


def test_tool_semantic_search_empty_grimoire(make_tools):
    v = [0.1, 0.2, 0.0, 0.0, 0.0, 0.0]
    assert make_tools.tool_semantic_search(
        proximity_vector=v, threshold=0.0, limit=10
    ) == []


def test_tool_divergence_thresholds_roundtrip(make_tools):
    before = make_tools.tool_divergence_thresholds()
    assert "l2_stable_max" in before
    updated = make_tools.tool_set_divergence_thresholds(
        {"l2_stable_max": 0.1, "l2_diverged_min": 0.2}
    )
    assert float(updated["l2_stable_max"]) == pytest.approx(0.1)
    after = make_tools.tool_divergence_thresholds()
    assert float(after["l2_stable_max"]) == pytest.approx(0.1)


def test_tool_inspect_keyerror_unknown(make_tools):
    with pytest.raises(KeyError):
        make_tools.tool_inspect("nonexistent-cast-id")


def test_tool_inspect_after_cast(make_tools, valid_intent):
    out = make_tools.tool_cast(aspects=["MIND", "LIGHT"], intent=valid_intent)
    cid = out["cast_id"]
    got = make_tools.tool_inspect(cid)
    assert got["cast_id"] == cid


def test_tool_seeds_empty_fresh_grimoire(make_tools):
    assert make_tools.tool_seeds(None) == []


def test_tool_seeds_after_cast(make_tools, valid_intent):
    make_tools.tool_cast(aspects=["MIND", "LIGHT"], intent=valid_intent)
    seeds = make_tools.tool_seeds(None)
    assert len(seeds) == 1


def test_mcp_server_with_engine_has_tools(tmp_path):
    db = tmp_path / "x.db"
    eng = ResonanceEngine(CompositionEngine(), None)
    g = Grimoire(db_path=db)
    s = VermythMCPServer(
        stdin=io.StringIO(),
        stdout=io.StringIO(),
        stderr=io.StringIO(),
        engine=eng,
        grimoire=g,
    )
    assert s._tools is not None


def test_mcp_server_without_engine_no_tools():
    s = VermythMCPServer(
        stdin=io.StringIO(),
        stdout=io.StringIO(),
        stderr=io.StringIO(),
    )
    assert s._tools is None


def test_mcp_integration_cast_success(tmp_path, valid_intent):
    db = tmp_path / "i.db"
    eng = ResonanceEngine(CompositionEngine(), None)
    g = Grimoire(db_path=db)
    out = io.StringIO()
    s = VermythMCPServer(
        stdin=io.StringIO(),
        stdout=out,
        stderr=io.StringIO(),
        engine=eng,
        grimoire=g,
    )
    s._handle_tools_call(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "cast",
                "arguments": {
                    "aspects": ["MIND", "LIGHT"],
                    **valid_intent,
                },
            },
        }
    )
    out.seek(0)
    resp = json.loads(out.read())
    assert "result" in resp
    assert resp["result"]["cast_id"]
    assert resp["id"] == 1


def test_mcp_integration_unknown_tool(tmp_path):
    db = tmp_path / "u.db"
    eng = ResonanceEngine(CompositionEngine(), None)
    g = Grimoire(db_path=db)
    out = io.StringIO()
    s = VermythMCPServer(
        stdin=io.StringIO(),
        stdout=out,
        stderr=io.StringIO(),
        engine=eng,
        grimoire=g,
    )
    s._handle_tools_call(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "nope", "arguments": {}},
        }
    )
    out.seek(0)
    resp = json.loads(out.read())
    assert resp["error"]["code"] == ERROR_METHOD_NOT_FOUND
    assert resp["error"]["code"] == -32601


def test_mcp_integration_invalid_aspects(tmp_path, valid_intent):
    db = tmp_path / "v.db"
    eng = ResonanceEngine(CompositionEngine(), None)
    g = Grimoire(db_path=db)
    out = io.StringIO()
    s = VermythMCPServer(
        stdin=io.StringIO(),
        stdout=out,
        stderr=io.StringIO(),
        engine=eng,
        grimoire=g,
    )
    s._handle_tools_call(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "cast",
                "arguments": {
                    "aspects": ["MIND", "XYZZY"],
                    **valid_intent,
                },
            },
        }
    )
    out.seek(0)
    resp = json.loads(out.read())
    assert resp["error"]["code"] == ERROR_INVALID_PARAMS
    assert resp["error"]["code"] == -32602
