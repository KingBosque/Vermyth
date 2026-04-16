from __future__ import annotations

import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from vermyth.adapters.a2a import TaskGateway, build_agent_card
from vermyth.bootstrap import build_tools
from vermyth.mcp.server import TOOL_DISPATCH
from vermyth.mcp.tool_definitions import TOOL_DEFINITIONS


def _json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict[str, Any]) -> None:
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    cors = os.getenv("VERMYTH_HTTP_CORS")
    if cors:
        handler.send_header("Access-Control-Allow-Origin", cors)
    handler.end_headers()
    handler.wfile.write(body)


class VermythHTTPHandler(BaseHTTPRequestHandler):
    tools = None

    def _authorized(self) -> bool:
        expected = os.getenv("VERMYTH_HTTP_TOKEN")
        if not expected:
            return True
        auth = self.headers.get("Authorization", "")
        if auth == f"Bearer {expected}":
            return True
        _json_response(self, 401, {"error": "unauthorized"})
        return False

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        cors = os.getenv("VERMYTH_HTTP_CORS")
        if cors:
            self.send_header("Access-Control-Allow-Origin", cors)
            self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        if not self._authorized():
            return
        if self.path == "/.well-known/agent.json":
            card = build_agent_card(TOOL_DEFINITIONS)
            _json_response(self, 200, card.model_dump(mode="json"))
            return
        if self.path == "/tools":
            _json_response(self, 200, {"tools": TOOL_DEFINITIONS})
            return
        if self.path.startswith("/events"):
            query = {}
            if "?" in self.path:
                _, raw = self.path.split("?", 1)
                for part in raw.split("&"):
                    if "=" in part:
                        k, v = part.split("=", 1)
                        query[k] = v
            n = int(query.get("tail", "100"))
            event_type = query.get("type")
            rows = self.tools.tool_events_tail(n=n, event_type=event_type)
            _json_response(self, 200, {"events": rows})
            return
        if self.path == "/healthz":
            latest = self.tools._grimoire.read_latest_basis_version()
            cur = self.tools._grimoire._conn.cursor()
            cur.execute("SELECT COUNT(*) AS c FROM schema_migrations")
            row = cur.fetchone()
            _json_response(
                self,
                200,
                {
                    "status": "ok",
                    "migrations": int(row["c"]) if row is not None else 0,
                    "basis_version": int(latest.version),
                },
            )
            return
        _json_response(self, 404, {"error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        if not self._authorized():
            return
        if self.path == "/a2a/tasks":
            size = int(self.headers.get("Content-Length", "0") or 0)
            raw = self.rfile.read(size) if size > 0 else b"{}"
            try:
                payload = json.loads(raw.decode("utf-8"))
                gateway = TaskGateway(tools=self.tools, tool_dispatch=TOOL_DISPATCH)
                result = gateway.execute_task(payload)
            except Exception as exc:
                _json_response(self, 400, {"error": str(exc)})
                return
            _json_response(self, 200, result)
            return
        if not self.path.startswith("/tools/"):
            _json_response(self, 404, {"error": "not_found"})
            return
        tool_name = self.path[len("/tools/") :]
        handler = TOOL_DISPATCH.get(tool_name)
        if handler is None:
            _json_response(self, 404, {"error": "unknown_tool"})
            return
        size = int(self.headers.get("Content-Length", "0") or 0)
        raw = self.rfile.read(size) if size > 0 else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8"))
            if payload is None:
                payload = {}
            if not isinstance(payload, dict):
                raise ValueError("JSON body must be an object")
            self.tools.enforce_tool_scope(tool_name)
            result = handler(self.tools, payload)
        except Exception as exc:
            _json_response(self, 400, {"error": str(exc)})
            return
        _json_response(self, 200, {"result": result})

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        _ = format, args


def serve(*, host: str = "127.0.0.1", port: int = 7777, db_path: str | None = None) -> ThreadingHTTPServer:
    _grimoire, _composition, _engine, tools = build_tools(db_path=db_path)
    handler_cls = type("BoundVermythHTTPHandler", (VermythHTTPHandler,), {"tools": tools})
    httpd = ThreadingHTTPServer((host, int(port)), handler_cls)
    return httpd


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m vermyth.adapters.http")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=7777)
    parser.add_argument("--db", default=None)
    args = parser.parse_args()
    server = serve(host=args.host, port=args.port, db_path=args.db)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
