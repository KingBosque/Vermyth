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
