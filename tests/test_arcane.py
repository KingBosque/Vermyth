"""Arcane ontology layer: compiler, bundles, gateway, policy gates."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from vermyth.adapters.a2a.gateway import TaskGateway
from vermyth.arcane.bundles import load_bundle
from vermyth.arcane.compiler import compile_ritual_spec, compile_semantic_bundle_ref
from vermyth.arcane.discovery import inspect_semantic_bundle_detail, list_bundle_catalog
from vermyth.arcane.invoke import resolve_tool_invocation
from vermyth.arcane.types import BanishmentSpec, RitualSpec, WardSpec
from vermyth.engine.operations.cast import compute_resonance
from vermyth.mcp.server import TOOL_DISPATCH
from vermyth.schema import (
    AspectID,
    Intent,
    PolicyThresholds,
    ReversibilityClass,
    RollbackStrategy,
    SemanticProgram,
    SideEffectTolerance,
)


def test_arcane_ritual_compile_adds_metadata_and_banishment():
    payload = {
        "name": "r1",
        "nodes": [
            {
                "node_id": "n1",
                "node_type": "CAST",
                "aspects": ["MIND"],
                "intent": {
                    "objective": "x",
                    "scope": "y",
                    "reversibility": "REVERSIBLE",
                    "side_effect_tolerance": "LOW",
                },
                "successors": [],
                "effects": [
                    {
                        "effect_type": "WRITE",
                        "target": {
                            "kind": "file",
                            "uri": "workspace://x",
                            "scope": "workspace",
                            "access": "READ_WRITE",
                        },
                        "reversible": False,
                        "cost_hint": 1.0,
                    }
                ],
            }
        ],
        "entry_node_ids": ["n1"],
    }
    prog = SemanticProgram.model_validate(payload)
    spec = RitualSpec(
        ritual_id="test_ritual",
        program=prog,
        banishment=BanishmentSpec(strict=True, default_rollback=RollbackStrategy.COMPENSATE),
    )
    out = compile_ritual_spec(spec)
    assert out.metadata.get("arcane", {}).get("kind") == "ritual"
    assert out.nodes[0].rollback is not None


def test_ward_changes_policy_allow_region():
    base = PolicyThresholds()
    ward = WardSpec(allow_min_resonance=0.92, effect_risk_min_score=0.95)
    from vermyth.arcane.compiler import merge_ward_into_thresholds

    merged = merge_ward_into_thresholds(base, ward)
    assert merged.allow_min_resonance >= 0.92
    assert merged.effect_risk_min_score is not None
    assert merged.allow_min_resonance > base.allow_min_resonance


def test_semantic_bundle_compression_vs_expanded_decide(make_tools):
    ref = {"bundle_id": "coherent_probe", "version": 1, "params": {"topic": "audit"}}
    inv = compile_semantic_bundle_ref(ref)
    assert inv.skill_id == "decide"
    assert inv.input["intent"]["objective"] == "Probe coherence on audit"
    compact = json.dumps(ref)
    expanded = json.dumps({"intent": inv.input["intent"], "aspects": inv.input["aspects"]})
    assert len(compact) < len(expanded)


def test_gateway_semantic_bundle_expansion(make_tools):
    gw = TaskGateway(tools=make_tools, tool_dispatch=TOOL_DISPATCH)
    out = gw.execute_task(
        {
            "skill_id": "decide",
            "input": {
                "semantic_bundle": {
                    "bundle_id": "coherent_probe",
                    "version": 1,
                    "params": {"topic": "gateway"},
                }
            },
        }
    )
    assert out["status"] == "completed"
    body = out["artifact"]["content"]
    assert "arcane_provenance" in body
    assert body["arcane_provenance"]["bundle_id"] == "coherent_probe"


def test_plain_task_json_without_bundle(make_tools):
    gw = TaskGateway(tools=make_tools, tool_dispatch=TOOL_DISPATCH)
    out = gw.execute_task(
        {
            "skill_id": "decide",
            "input": {
                "intent": {
                    "objective": "plain",
                    "scope": "test",
                    "reversibility": "REVERSIBLE",
                    "side_effect_tolerance": "LOW",
                },
                "aspects": ["MIND"],
            },
        }
    )
    assert out["status"] == "completed"
    c = out["artifact"]["content"]
    assert "arcane_provenance" not in c


def test_effect_class_does_not_change_resonance_numeric(composition_engine):
    from vermyth.engine.resonance import ResonanceEngine
    from vermyth.schema import EffectClass

    engine = ResonanceEngine(composition_engine, backend=None)
    aspects = frozenset({AspectID.MIND, AspectID.LIGHT})
    intent = Intent(
        objective="test",
        scope="s",
        reversibility=ReversibilityClass.REVERSIBLE,
        side_effect_tolerance=SideEffectTolerance.LOW,
    )
    r1 = engine.cast(aspects, intent)
    sig = r1.sigil
    iv = engine._build_intent_vector(intent)
    s2 = sig.model_copy(update={"effect_class": EffectClass.MANIFESTATION})
    s3 = sig.model_copy(update={"effect_class": EffectClass.ERASURE})
    rs2, _ = compute_resonance(engine, s2, iv)
    rs3, _ = compute_resonance(engine, s3, iv)
    assert rs2.adjusted == rs3.adjusted


def test_divination_gate_requires_causal(make_tools):
    gw = TaskGateway(tools=make_tools, tool_dispatch=TOOL_DISPATCH)
    out = gw.execute_task(
        {
            "skill_id": "decide",
            "input": {
                "semantic_bundle": {
                    "bundle_id": "divination_gate",
                    "version": 1,
                    "params": {"topic": "x"},
                }
            },
        }
    )
    assert out["status"] == "failed"
    assert "causal" in out["error"].lower() or "divination" in out["error"].lower()


def test_list_bundle_catalog_includes_builtins():
    rows = list_bundle_catalog()
    ids = {r["bundle_id"] for r in rows}
    assert "coherent_probe" in ids
    assert "strict_ward_probe" in ids
    assert all(r["target_skill"] in ("decide", "cast", "compile_program") for r in rows)


def test_inspect_semantic_bundle_detail_has_compiled_preview():
    d = inspect_semantic_bundle_detail("coherent_probe", 1)
    assert d["manifest"]["id"] == "coherent_probe"
    assert d["compiled_preview"]["skill_id"] == "decide"
    assert "intent" in d["compiled_preview"]["input"]
    assert d["semantic_bundle_ref_example"]["bundle_id"] == "coherent_probe"


def test_resolve_tool_invocation_decide_to_cast(monkeypatch):
    d = Path(__file__).resolve().parent / "fixtures" / "arcane_bundles"
    monkeypatch.setenv("VERMYTH_ARCANE_BUNDLE_DIR", str(d))
    load_bundle.cache_clear()
    skill, args, prov = resolve_tool_invocation(
        "decide",
        {
            "semantic_bundle": {
                "bundle_id": "cast_smoke",
                "version": 1,
                "params": {"topic": "unit"},
            }
        },
    )
    assert skill == "cast"
    assert args["objective"] == "Smoke unit"
    assert prov is not None and prov.get("bundle_id") == "cast_smoke"


def test_mcp_decide_bundle_decision_matches_expanded_inputs(tmp_path):
    """Behavioral match: bundle vs manually expanded decide arguments (fresh DB each)."""
    from vermyth.engine.composition import CompositionEngine
    from vermyth.engine.resonance import ResonanceEngine
    from vermyth.grimoire.store import Grimoire
    from vermyth.mcp.server import VermythMCPServer

    ref = {"bundle_id": "coherent_probe", "version": 1, "params": {"topic": "equiv"}}
    inv = compile_semantic_bundle_ref(ref)

    def _decide_via_mcp(db: Path):
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
        return s, out

    db1 = tmp_path / "a.db"
    s1, o1 = _decide_via_mcp(db1)
    s1._handle_tools_call(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "decide",
                "arguments": {"semantic_bundle": ref},
            },
        }
    )
    o1.seek(0)
    r1 = json.loads(o1.read())["result"]

    db2 = tmp_path / "b.db"
    s2, o2 = _decide_via_mcp(db2)
    s2._handle_tools_call(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "decide", "arguments": dict(inv.input)},
        }
    )
    o2.seek(0)
    r2 = json.loads(o2.read())["result"]

    d1, d2 = r1["decision"], r2["decision"]
    assert d1["action"] == d2["action"]
    assert r1["cast"]["verdict"] == r2["cast"]["verdict"]
    assert "arcane_provenance" in r1
    assert "arcane_provenance" not in r2


def test_expand_semantic_bundle_mcp(make_tools):
    out = make_tools.tool_expand_semantic_bundle(
        "decide",
        {
            "semantic_bundle": {
                "bundle_id": "strict_ward_probe",
                "version": 1,
                "params": {"topic": "mcp"},
            }
        },
    )
    assert out["skill_id"] == "decide"
    assert out["input"]["thresholds"]["allow_min_resonance"] == 0.92
