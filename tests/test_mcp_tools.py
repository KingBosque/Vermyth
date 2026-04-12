import io
import json
import sys
from pathlib import Path

_root = Path(__file__).resolve().parents[1]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import pytest

from vermyth.engine.composition import CompositionEngine
from vermyth.engine.resonance import ResonanceEngine
from vermyth.grimoire.store import Grimoire
from vermyth.mcp.protocol import ERROR_INVALID_PARAMS, ERROR_METHOD_NOT_FOUND
from vermyth.mcp.server import VermythMCPServer
from vermyth.mcp.tools import VermythTools


@pytest.fixture
def make_tools(tmp_path):
    db = tmp_path / "grimoire.db"
    composition = CompositionEngine()
    engine = ResonanceEngine(composition, backend=None)
    grimoire = Grimoire(db_path=db)
    return VermythTools(engine, grimoire)


def _valid_intent():
    return {
        "objective": "study the pattern",
        "scope": "local workspace",
        "reversibility": "REVERSIBLE",
        "side_effect_tolerance": "HIGH",
    }


def test_vermyth_tools_importable():
    from vermyth.mcp.tools import VermythTools as VT

    assert VT is VermythTools


def test_tool_cast_returns_expected_keys(make_tools):
    out = make_tools.tool_cast(
        aspects=["MIND", "LIGHT"],
        intent=_valid_intent(),
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


def test_tool_cast_unknown_aspect_raises(make_tools):
    with pytest.raises(ValueError, match="Unknown aspect"):
        make_tools.tool_cast(aspects=["MIND", "NOTREAL"], intent=_valid_intent())


def test_tool_cast_invalid_intent_raises_validation_error(make_tools):
    pydantic = pytest.importorskip("pydantic")
    with pytest.raises(pydantic.ValidationError):
        make_tools.tool_cast(
            aspects=["MIND", "LIGHT"],
            intent={"objective": "x", "scope": "y", "reversibility": "BAD", "side_effect_tolerance": "HIGH"},
        )


def test_tool_cast_projection_partial_without_backend(make_tools):
    out = make_tools.tool_cast(aspects=["MIND", "LIGHT"], intent=_valid_intent())
    assert out["projection_method"] == "PARTIAL"


def test_tool_cast_twice_same_aspects_updates_single_seed_observed_count(
    make_tools,
):
    aspects = ["MIND", "LIGHT"]
    intent = _valid_intent()
    make_tools.tool_cast(aspects=aspects, intent=intent)
    make_tools.tool_cast(aspects=aspects, intent=intent)
    seeds = make_tools.tool_seeds(crystallized=None)
    assert len(seeds) == 1
    assert seeds[0]["observed_count"] == 2


def test_tool_cast_persists_seed_after_cast(make_tools):
    make_tools.tool_cast(aspects=["MIND", "LIGHT"], intent=_valid_intent())
    seeds = make_tools.tool_seeds(None)
    assert len(seeds) >= 1


def test_tool_query_empty_fresh_grimoire(make_tools):
    assert make_tools.tool_query({}) == []


def test_tool_query_after_one_cast_returns_one(make_tools):
    make_tools.tool_cast(aspects=["MIND", "LIGHT"], intent=_valid_intent())
    rows = make_tools.tool_query({})
    assert len(rows) == 1


def test_tool_query_verdict_filter_returns_matching_verdict(make_tools):
    make_tools.tool_cast(aspects=["MIND", "LIGHT"], intent=_valid_intent())
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


def test_tool_inspect_keyerror_unknown(make_tools):
    with pytest.raises(KeyError):
        make_tools.tool_inspect("nonexistent-cast-id")


def test_tool_inspect_after_cast(make_tools):
    out = make_tools.tool_cast(aspects=["MIND", "LIGHT"], intent=_valid_intent())
    cid = out["cast_id"]
    got = make_tools.tool_inspect(cid)
    assert got["cast_id"] == cid


def test_tool_seeds_empty_fresh_grimoire(make_tools):
    assert make_tools.tool_seeds(None) == []


def test_tool_seeds_after_cast(make_tools):
    make_tools.tool_cast(aspects=["MIND", "LIGHT"], intent=_valid_intent())
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


def test_mcp_integration_cast_success(tmp_path):
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
                    **_valid_intent(),
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


def test_mcp_integration_invalid_aspects(tmp_path):
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
                    **_valid_intent(),
                },
            },
        }
    )
    out.seek(0)
    resp = json.loads(out.read())
    assert resp["error"]["code"] == ERROR_INVALID_PARAMS
    assert resp["error"]["code"] == -32602
