from __future__ import annotations

import json
import os
import threading
import urllib.error
import urllib.request
from pathlib import Path

from vermyth.adapters.http import serve
from vermyth.mcp.tool_definitions import TOOL_DEFINITIONS


def _request(url: str, *, method: str = "GET", body: dict | None = None, token: str | None = None):
    data = None
    headers = {"Content-Type": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def test_http_adapter_endpoints(tmp_path: Path) -> None:
    db = tmp_path / "http.db"
    server = serve(host="127.0.0.1", port=0, db_path=str(db))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    base = f"http://127.0.0.1:{port}"
    try:
        tools = _request(f"{base}/tools")
        assert len(tools["tools"]) == len(TOOL_DEFINITIONS)
        card = _request(f"{base}/.well-known/agent.json")
        assert card["name"] == "vermyth"
        assert card["skills"]

        cast = _request(
            f"{base}/tools/cast",
            method="POST",
            body={
                "aspects": ["MIND", "LIGHT"],
                "objective": "Reveal hidden structure",
                "scope": "analysis",
                "reversibility": "REVERSIBLE",
                "side_effect_tolerance": "LOW",
            },
        )["result"]
        assert "cast_id" in cast

        a2a = _request(
            f"{base}/a2a/tasks",
            method="POST",
            body={
                "skill_id": "decide",
                "input": {
                    "intent": {
                        "objective": "Reveal hidden structure",
                        "scope": "analysis",
                        "reversibility": "REVERSIBLE",
                        "side_effect_tolerance": "LOW",
                    },
                    "aspects": ["MIND", "LIGHT"],
                },
            },
        )
        assert a2a["status"] == "completed"
        assert a2a["artifact"] is not None

        decide = _request(
            f"{base}/tools/decide",
            method="POST",
            body={
                "intent": {
                    "objective": "Reveal hidden structure",
                    "scope": "analysis",
                    "reversibility": "REVERSIBLE",
                    "side_effect_tolerance": "LOW",
                },
                "aspects": ["MIND", "LIGHT"],
            },
        )["result"]
        assert "decision" in decide and "cast" in decide
        assert "arcane_provenance" not in decide

        bundle_decide = _request(
            f"{base}/tools/decide",
            method="POST",
            body={
                "semantic_bundle": {
                    "bundle_id": "coherent_probe",
                    "version": 1,
                    "params": {"topic": "http_adapter"},
                }
            },
        )["result"]
        assert "decision" in bundle_decide and "cast" in bundle_decide
        assert bundle_decide["arcane_provenance"]["bundle_id"] == "coherent_probe"

        catalog = _request(f"{base}/arcane/bundles")
        assert any(b["bundle_id"] == "coherent_probe" for b in catalog["bundles"])
        detail = _request(f"{base}/arcane/bundles/coherent_probe?version=1")
        assert detail["manifest"]["id"] == "coherent_probe"
        assert detail["compiled_preview"]["skill_id"] == "decide"
        assert detail["semantic_bundle_ref_example"]["bundle_id"] == "coherent_probe"
        assert detail["guided_upgrade"]["inspect"]["http_get_path"].startswith("/arcane/bundles/")

        rec = _request(
            f"{base}/arcane/recommend",
            method="POST",
            body={
                "skill_id": "decide",
                "input": {
                    "intent": {
                        "objective": "Probe coherence on http_rec",
                        "scope": "semantic_bundle",
                        "reversibility": "REVERSIBLE",
                        "side_effect_tolerance": "LOW",
                    },
                    "aspects": ["MIND", "LIGHT"],
                },
            },
        )
        assert any(
            r["bundle_id"] == "coherent_probe" for r in rec["recommendations"]
        )
        probe = next(r for r in rec["recommendations"] if r["bundle_id"] == "coherent_probe")
        assert probe["guided_upgrade"]["semantic_bundle"]["bundle_id"] == "coherent_probe"

        report = _request(f"{base}/arcane/telemetry/report")
        assert report.get("schema_version") == 1

        events = _request(f"{base}/events?tail=20")
        assert "events" in events

        health = _request(f"{base}/healthz")
        assert health["status"] == "ok"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_http_adapter_token_auth(tmp_path: Path) -> None:
    old = os.environ.get("VERMYTH_HTTP_TOKEN")
    os.environ["VERMYTH_HTTP_TOKEN"] = "secret"
    db = tmp_path / "http_auth.db"
    server = serve(host="127.0.0.1", port=0, db_path=str(db))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    base = f"http://127.0.0.1:{port}"
    try:
        with urllib.request.urlopen(
            urllib.request.Request(f"{base}/healthz", method="GET")
        ) as _:
            raise AssertionError("request without token should fail")
    except urllib.error.HTTPError as exc:
        assert exc.code == 401
    try:
        out = _request(f"{base}/healthz", token="secret")
        assert out["status"] == "ok"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        if old is None:
            os.environ.pop("VERMYTH_HTTP_TOKEN", None)
        else:
            os.environ["VERMYTH_HTTP_TOKEN"] = old
