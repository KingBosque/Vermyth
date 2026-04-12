"""MCP stdio server skeleton (JSON-RPC 2.0, newline-delimited)."""

from __future__ import annotations

import json
import sys
from typing import Any, TextIO

from vermyth.engine.resonance import ResonanceEngine
from vermyth.grimoire.store import Grimoire
from vermyth.mcp.protocol import (
    CAPABILITIES,
    ERROR_INTERNAL,
    ERROR_INVALID_PARAMS,
    ERROR_METHOD_NOT_FOUND,
    ERROR_NOT_IMPLEMENTED,
    ERROR_PARSE_ERROR,
    PROTOCOL_VERSION,
    SERVER_INFO,
    get_id,
    get_method,
    get_params,
    is_notification,
    make_error,
    make_success,
)
from vermyth.mcp.tools import VermythTools

TOOL_DEFINITIONS = [
    {
        "name": "cast",
        "description": "Compose aspects into a Sigil and evaluate against a declared Intent. Returns a fully typed CastResult.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "aspects": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of AspectID names. Valid values: VOID, FORM, MOTION, MIND, DECAY, LIGHT. Between 1 and 3 inclusive.",
                },
                "objective": {
                    "type": "string",
                    "description": "What this casting should accomplish. Max 500 characters.",
                },
                "scope": {
                    "type": "string",
                    "description": "The bounded domain this casting applies to. Max 200 characters.",
                },
                "reversibility": {
                    "type": "string",
                    "enum": ["REVERSIBLE", "PARTIAL", "IRREVERSIBLE"],
                },
                "side_effect_tolerance": {
                    "type": "string",
                    "enum": ["NONE", "LOW", "MEDIUM", "HIGH"],
                },
            },
            "required": [
                "aspects",
                "objective",
                "scope",
                "reversibility",
                "side_effect_tolerance",
            ],
        },
    },
    {
        "name": "query",
        "description": "Query the grimoire for CastResults by field filters.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "verdict_filter": {
                    "type": "string",
                    "enum": ["COHERENT", "PARTIAL", "INCOHERENT"],
                    "description": "Optional verdict type filter.",
                },
                "min_resonance": {
                    "type": "number",
                    "description": "Minimum adjusted resonance score. 0.0 to 1.0.",
                },
                "branch_id": {
                    "type": "string",
                    "description": "Filter by lineage branch ID.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum results to return. Default 20, max 100.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "semantic_search",
        "description": "Search the grimoire by semantic proximity to a given aspect vector.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "proximity_vector": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "Six floats in canonical aspect order: VOID, FORM, MOTION, MIND, DECAY, LIGHT. Each in range -1.0 to 1.0.",
                },
                "threshold": {
                    "type": "number",
                    "description": "Minimum cosine similarity. 0.0 to 1.0.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum results to return. Default 20, max 100.",
                },
            },
            "required": ["proximity_vector", "threshold"],
        },
    },
    {
        "name": "inspect",
        "description": "Retrieve a single CastResult by cast_id.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "cast_id": {
                    "type": "string",
                    "description": "The ULID cast_id of the CastResult to retrieve.",
                }
            },
            "required": ["cast_id"],
        },
    },
    {
        "name": "seeds",
        "description": "List GlyphSeeds optionally filtered by crystallized status.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "crystallized": {
                    "type": "boolean",
                    "description": "Filter by crystallized status. Omit to return all seeds.",
                }
            },
            "required": [],
        },
    },
]


class VermythMCPServer:
    """Stdio MCP server: initialize, tools/list, tools/call with optional Vermyth wiring."""

    def __init__(
        self,
        stdin: TextIO | None = None,
        stdout: TextIO | None = None,
        stderr: TextIO | None = None,
        engine: ResonanceEngine | None = None,
        grimoire: Grimoire | None = None,
    ) -> None:
        self._in = stdin if stdin is not None else sys.stdin
        self._out = stdout if stdout is not None else sys.stdout
        self._err = stderr if stderr is not None else sys.stderr
        self._running = False
        self._stdin_eof = False
        if engine is not None and grimoire is not None:
            self._tools = VermythTools(engine, grimoire)
        else:
            self._tools = None

    def _log(self, message: str) -> None:
        try:
            self._err.write(f"[vermyth-mcp] {message}\n")
            self._err.flush()
        except OSError:
            pass
        except ValueError:
            pass

    def _send(self, message: dict) -> None:
        try:
            line = json.dumps(message) + "\n"
            self._out.write(line)
            self._out.flush()
        except (TypeError, ValueError):
            self._log("failed to serialize JSON-RPC response")
        except OSError:
            pass

    def _read_message(self) -> dict | None:
        self._stdin_eof = False
        try:
            raw = self._in.readline()
        except OSError:
            self._stdin_eof = True
            return None
        if raw == "":
            self._stdin_eof = True
            return None
        line = raw.rstrip("\r\n")
        if line.strip() == "":
            return None
        try:
            parsed: Any = json.loads(line)
        except json.JSONDecodeError:
            self._send(
                make_error(
                    None,
                    ERROR_PARSE_ERROR,
                    "Parse error: invalid JSON",
                )
            )
            return None
        if not isinstance(parsed, dict):
            self._send(
                make_error(
                    None,
                    ERROR_PARSE_ERROR,
                    "Parse error: expected JSON object",
                )
            )
            return None
        return parsed

    def _handle_initialize(self, message: dict) -> None:
        result = {
            "protocolVersion": PROTOCOL_VERSION,
            "serverInfo": SERVER_INFO,
            "capabilities": CAPABILITIES,
        }
        self._send(make_success(get_id(message), result))

    def _handle_tools_list(self, message: dict) -> None:
        self._send(make_success(get_id(message), {"tools": TOOL_DEFINITIONS}))

    def _handle_tools_call(self, message: dict) -> None:
        msg_id = get_id(message)
        params = get_params(message)
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        self._log(f"tool call: {tool_name}")

        if self._tools is None:
            self._send(
                make_error(
                    msg_id,
                    ERROR_NOT_IMPLEMENTED,
                    "No engine or grimoire configured.",
                )
            )
            return

        try:
            if tool_name == "cast":
                result = self._tools.tool_cast(
                    aspects=arguments.get("aspects", []),
                    intent={
                        "objective": arguments.get("objective", ""),
                        "scope": arguments.get("scope", ""),
                        "reversibility": arguments.get("reversibility", "PARTIAL"),
                        "side_effect_tolerance": arguments.get(
                            "side_effect_tolerance", "MEDIUM"
                        ),
                    },
                )
                self._send(make_success(msg_id, result))

            elif tool_name == "query":
                result = self._tools.tool_query(arguments)
                self._send(make_success(msg_id, result))

            elif tool_name == "semantic_search":
                result = self._tools.tool_semantic_search(
                    proximity_vector=arguments.get("proximity_vector", []),
                    threshold=float(arguments.get("threshold", 0.5)),
                    limit=int(arguments.get("limit", 20)),
                )
                self._send(make_success(msg_id, result))

            elif tool_name == "inspect":
                result = self._tools.tool_inspect(
                    cast_id=arguments.get("cast_id", "")
                )
                self._send(make_success(msg_id, result))

            elif tool_name == "seeds":
                crystallized = arguments.get("crystallized")
                result = self._tools.tool_seeds(crystallized=crystallized)
                self._send(make_success(msg_id, result))

            else:
                self._send(
                    make_error(
                        msg_id,
                        ERROR_METHOD_NOT_FOUND,
                        f"Unknown tool: {tool_name}",
                    )
                )

        except ValueError as e:
            self._send(make_error(msg_id, ERROR_INVALID_PARAMS, str(e)))
        except KeyError as e:
            self._send(
                make_error(
                    msg_id,
                    ERROR_INVALID_PARAMS,
                    f"Not found: {e}",
                )
            )
        except RuntimeError as e:
            self._send(make_error(msg_id, ERROR_INTERNAL, str(e)))
        except Exception as e:
            self._log(f"unexpected error in tool call: {e}")
            self._send(
                make_error(
                    msg_id,
                    ERROR_INTERNAL,
                    "Unexpected server error.",
                )
            )

    def _handle_message(self, message: dict) -> None:
        try:
            if is_notification(message):
                method = get_method(message)
                self._log(f"notification: {method!r}")
                return
            if get_method(message) == "notifications/initialized":
                self._log("notifications/initialized")
                return
            method = get_method(message)
            if method == "initialize":
                self._handle_initialize(message)
            elif method == "tools/list":
                self._handle_tools_list(message)
            elif method == "tools/call":
                self._handle_tools_call(message)
            else:
                self._send(
                    make_error(
                        get_id(message),
                        ERROR_METHOD_NOT_FOUND,
                        f"Method not found: {method}",
                    )
                )
        except Exception as exc:
            self._log(f"internal error: {exc!r}")
            self._send(
                make_error(
                    get_id(message),
                    ERROR_INTERNAL,
                    "Internal error",
                )
            )

    def run(self) -> None:
        self._running = True
        self._log("Vermyth MCP server starting")
        try:
            while self._running:
                msg = self._read_message()
                if self._stdin_eof:
                    break
                if msg is None:
                    continue
                self._handle_message(msg)
        except KeyboardInterrupt:
            pass
        except EOFError:
            pass
        finally:
            self._log("Vermyth MCP server stopping")
            self._running = False


def main() -> None:
    import os

    from vermyth.engine.composition import CompositionEngine
    from vermyth.engine.resonance import ResonanceEngine
    from vermyth.grimoire.store import Grimoire

    backend_requested = os.environ.get("VERMYTH_BACKEND")
    backend = None
    if backend_requested:
        print(
            f"[vermyth-mcp] VERMYTH_BACKEND={backend_requested} set but "
            "dynamic backend loading is not yet implemented. "
            "Proceeding with PARTIAL projection.",
            file=sys.stderr,
        )

    composition = CompositionEngine()
    grimoire = Grimoire()
    engine = ResonanceEngine(composition_engine=composition, backend=backend)

    server = VermythMCPServer(engine=engine, grimoire=grimoire)
    server.run()


if __name__ == "__main__":
    main()
