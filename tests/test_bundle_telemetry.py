"""Local bundle adoption telemetry (opt-in via env)."""

from __future__ import annotations

import os

import pytest

from vermyth.arcane.bundle_telemetry import (
    ENV_ENABLE,
    ENV_MISSED,
    get_bundle_adoption_summary,
    reset_for_tests,
)
from vermyth.arcane.invoke import resolve_tool_invocation
from vermyth.arcane.recommend import recommend_for_plain_invocation


@pytest.fixture(autouse=True)
def _telemetry_env():
    reset_for_tests()
    prev_e = os.environ.get(ENV_ENABLE)
    prev_m = os.environ.get(ENV_MISSED)
    os.environ[ENV_ENABLE] = "1"
    os.environ[ENV_MISSED] = "1"
    yield
    reset_for_tests()
    if prev_e is None:
        os.environ.pop(ENV_ENABLE, None)
    else:
        os.environ[ENV_ENABLE] = prev_e
    if prev_m is None:
        os.environ.pop(ENV_MISSED, None)
    else:
        os.environ[ENV_MISSED] = prev_m


def test_recommendation_events_recorded():
    reset_for_tests()
    recommend_for_plain_invocation(
        "decide",
        {
            "intent": {
                "objective": "Probe coherence on t",
                "scope": "semantic_bundle",
                "reversibility": "REVERSIBLE",
                "side_effect_tolerance": "LOW",
            },
            "aspects": ["MIND", "LIGHT"],
        },
        surface="mcp",
    )
    s = get_bundle_adoption_summary()
    assert s["counts_by_event_type"].get("bundle_recommended", 0) >= 1
    assert s["funnel"]["bundle_recommended"] >= 1


def test_inspection_and_catalog_events_recorded():
    reset_for_tests()
    from vermyth.arcane.bundle_telemetry import (
        record_bundle_catalog_listed,
        record_bundle_inspected,
    )

    record_bundle_catalog_listed(surface="test", kind=None)
    record_bundle_inspected(
        surface="test", bundle_id="coherent_probe", version=1, guided_upgrade_shown=True
    )
    s = get_bundle_adoption_summary()
    assert s["counts_by_event_type"].get("bundle_catalog_listed", 0) >= 1
    assert s["counts_by_event_type"].get("bundle_inspected", 0) >= 1


def test_bundle_invocation_recorded():
    reset_for_tests()
    resolve_tool_invocation(
        "decide",
        {
            "semantic_bundle": {
                "bundle_id": "coherent_probe",
                "version": 1,
                "params": {"topic": "tel"},
            }
        },
        telemetry_surface="http",
    )
    s = get_bundle_adoption_summary()
    assert s["counts_by_event_type"].get("bundle_invoked", 0) == 1
    assert s["counts_by_bundle_id"].get("coherent_probe", 0) >= 1


def test_missed_upgrade_recorded_for_plain_matching_input():
    reset_for_tests()
    resolve_tool_invocation(
        "decide",
        {
            "intent": {
                "objective": "Probe coherence on miss",
                "scope": "semantic_bundle",
                "reversibility": "REVERSIBLE",
                "side_effect_tolerance": "LOW",
            },
            "aspects": ["MIND", "LIGHT"],
        },
        telemetry_surface="http",
    )
    s = get_bundle_adoption_summary()
    assert s["counts_by_event_type"].get("bundle_recommendation_missed", 0) >= 1


def test_plain_json_no_invocation_event():
    reset_for_tests()
    resolve_tool_invocation(
        "decide",
        {
            "intent": {
                "objective": "Unrelated",
                "scope": "other",
                "reversibility": "IRREVERSIBLE",
                "side_effect_tolerance": "HIGH",
            },
            "aspects": ["VOID"],
        },
        telemetry_surface="http",
    )
    s = get_bundle_adoption_summary()
    assert s["counts_by_event_type"].get("bundle_invoked", 0) == 0


def test_telemetry_disabled_no_events():
    reset_for_tests()
    os.environ[ENV_ENABLE] = "0"
    os.environ[ENV_MISSED] = "0"
    recommend_for_plain_invocation(
        "decide",
        {
            "intent": {
                "objective": "Probe coherence on off",
                "scope": "semantic_bundle",
                "reversibility": "REVERSIBLE",
                "side_effect_tolerance": "LOW",
            },
            "aspects": ["MIND", "LIGHT"],
        },
        surface="mcp",
    )
    s = get_bundle_adoption_summary()
    assert s["enabled"] is False
    assert sum(s["counts_by_event_type"].values()) == 0


def test_get_bundle_adoption_summary_shape():
    reset_for_tests()
    s = get_bundle_adoption_summary()
    assert "funnel" in s and "recent_events_sample" in s
    assert "bytes_saved_estimate_total" in s
