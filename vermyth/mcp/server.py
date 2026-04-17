"""MCP stdio server (JSON-RPC 2.0, newline-delimited).

MCP is used for tool/resource access. Experimental peer-agent coordination
surfaces are available only when explicitly enabled.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, BinaryIO, TextIO
from urllib.parse import parse_qs, urlparse

from vermyth.mcp.binary_transport import FrameType, decode_frame_from_buffer, encode_frame

from vermyth.arcane.bundle_telemetry import (
    record_bundle_catalog_listed,
    record_bundle_inspected,
)
from vermyth.arcane.discovery import inspect_semantic_bundle_detail, list_bundle_catalog
from vermyth.arcane.invoke import attach_arcane_provenance, resolve_tool_invocation
from vermyth.bootstrap import build_tools, build_tools_from_env
from vermyth.engine.projection_backends import NullProjectionBackend
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
from vermyth.mcp.tools import arcane as arcane_tools
from vermyth.mcp.tools import casting as casting_tools
from vermyth.mcp.tools import causal as causal_tools
from vermyth.mcp.tools import decisions as decision_tools
from vermyth.mcp.tools import drift as drift_tools
from vermyth.mcp.tools import genesis as genesis_tools
from vermyth.mcp.tools import observability as observability_tools
from vermyth.mcp.tools import programs as program_tools
from vermyth.mcp.tools import query as query_tools
from vermyth.mcp.tools import registry as registry_tools
from vermyth.mcp.tools import seeds as seed_tools
from vermyth.mcp.tools import session as session_tools
from vermyth.mcp.tools import swarm as swarm_tools
from vermyth.mcp.tools import VermythTools
from vermyth.mcp.tool_definitions import TOOL_DEFINITIONS

_ENABLE_EXPERIMENTAL = bool(
    int((os.environ.get("VERMYTH_EXPERIMENTAL_TOOLS", "0") or "0"))
)

TOOL_DISPATCH = {
    **casting_tools.DISPATCH,
    **arcane_tools.DISPATCH,
    **decision_tools.DISPATCH,
    **observability_tools.DISPATCH,
    **drift_tools.DISPATCH,
    **causal_tools.DISPATCH,
    **genesis_tools.DISPATCH,
    **program_tools.DISPATCH,
    **query_tools.DISPATCH,
    **registry_tools.DISPATCH,
    **seed_tools.DISPATCH,
}

if _ENABLE_EXPERIMENTAL:
    TOOL_DISPATCH.update(swarm_tools.DISPATCH)


class VermythMCPServer:
    """Stdio MCP server: initialize, tools/list, tools/call with optional Vermyth wiring."""

    def __init__(
        self,
        stdin: TextIO | None = None,
        stdout: TextIO | None = None,
        stderr: TextIO | None = None,
        engine: ResonanceEngine | None = None,
        grimoire: Grimoire | None = None,
        *,
        binary_mode: bool = False,
    ) -> None:
        self._in = stdin if stdin is not None else sys.stdin
        self._out = stdout if stdout is not None else sys.stdout
        self._err = stderr if stderr is not None else sys.stderr
        self._binary_mode = bool(binary_mode)
        self._bin_in: BinaryIO | None = None
        self._bin_out: BinaryIO | None = None
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

    def _run_binary(self) -> None:
        self._bin_in = getattr(self._in, "buffer", None) or sys.stdin.buffer
        self._bin_out = getattr(self._out, "buffer", None) or sys.stdout.buffer

        while self._running:
            frame = decode_frame_from_buffer(self._bin_in)  # type: ignore[arg-type]
            if frame is None:
                break
            try:
                payload_obj: Any = json.loads(frame.payload.decode("utf-8"))
            except Exception:
                err = {"error": "invalid payload json"}
                self._bin_out.write(encode_frame(FrameType.ERROR, json.dumps(err).encode("utf-8")))
                self._bin_out.flush()
                continue

            if frame.frame_type == FrameType.SESSION_OPEN:
                ack = {"accepted": True, "transport": "BINARY", "version": 1}
                self._bin_out.write(encode_frame(FrameType.SESSION_ACK, json.dumps(ack).encode("utf-8")))
                self._bin_out.flush()
                continue

            if frame.frame_type == FrameType.SESSION_CLOSE:
                ack = {"closed": True}
                self._bin_out.write(encode_frame(FrameType.SESSION_CLOSE, json.dumps(ack).encode("utf-8")))
                self._bin_out.flush()
                continue

            if frame.frame_type in (FrameType.GOSSIP_PUSH, FrameType.GOSSIP_PULL):
                if not _ENABLE_EXPERIMENTAL:
                    err = {"error": "experimental tool surface disabled"}
                    self._bin_out.write(encode_frame(FrameType.ERROR, json.dumps(err).encode("utf-8")))
                    self._bin_out.flush()
                    continue
                if self._tools is None:
                    err = {"error": "No engine or grimoire configured."}
                    self._bin_out.write(encode_frame(FrameType.ERROR, json.dumps(err).encode("utf-8")))
                    self._bin_out.flush()
                    continue
                try:
                    result = self._tools.tool_gossip_sync(payload_obj)
                    self._bin_out.write(
                        encode_frame(FrameType.GOSSIP_ACK, json.dumps(result).encode("utf-8"))
                    )
                    self._bin_out.flush()
                except Exception as exc:
                    err = {"error": str(exc)}
                    self._bin_out.write(encode_frame(FrameType.ERROR, json.dumps(err).encode("utf-8")))
                    self._bin_out.flush()
                continue

            if frame.frame_type == FrameType.CAUSAL_SYNC:
                if self._tools is None:
                    err = {"error": "No engine or grimoire configured."}
                    self._bin_out.write(encode_frame(FrameType.ERROR, json.dumps(err).encode("utf-8")))
                    self._bin_out.flush()
                    continue
                try:
                    if (
                        isinstance(payload_obj, dict)
                        and "source_cast_id" in payload_obj
                        and "target_cast_id" in payload_obj
                    ):
                        result = self._tools.tool_add_causal_edge(payload_obj)
                    else:
                        result = {"accepted": True}
                    self._bin_out.write(
                        encode_frame(FrameType.CAUSAL_SYNC, json.dumps(result).encode("utf-8"))
                    )
                    self._bin_out.flush()
                except Exception as exc:
                    err = {"error": str(exc)}
                    self._bin_out.write(encode_frame(FrameType.ERROR, json.dumps(err).encode("utf-8")))
                    self._bin_out.flush()
                continue

            if frame.frame_type == FrameType.PACKET:
                if self._tools is None:
                    err = {"error": "No engine or grimoire configured."}
                    self._bin_out.write(encode_frame(FrameType.ERROR, json.dumps(err).encode("utf-8")))
                    self._bin_out.flush()
                    continue
                tool = payload_obj.get("tool")
                args = payload_obj.get("arguments", {})
                if not isinstance(args, dict):
                    args = {}
                try:
                    binary_handler = (
                        session_tools.BINARY_DISPATCH.get(str(tool))
                        if _ENABLE_EXPERIMENTAL
                        else None
                    )
                    if binary_handler is not None:
                        self._tools.enforce_tool_scope(str(tool))
                        result = binary_handler(self._tools, args)
                    else:
                        resolved_tool, merged_args, arc_prov = resolve_tool_invocation(
                            str(tool), args
                        )
                        self._tools.enforce_tool_scope(resolved_tool)
                        if resolved_tool not in TOOL_DISPATCH:
                            raise ValueError(f"unknown tool: {resolved_tool}")
                        result = TOOL_DISPATCH[resolved_tool](self._tools, merged_args)
                        result = attach_arcane_provenance(result, arc_prov)
                    self._bin_out.write(encode_frame(FrameType.RESPONSE, json.dumps(result).encode("utf-8")))
                    self._bin_out.flush()
                except Exception as exc:
                    err = {"error": str(exc)}
                    self._bin_out.write(encode_frame(FrameType.ERROR, json.dumps(err).encode("utf-8")))
                    self._bin_out.flush()
                continue

    def _handle_initialize(self, message: dict) -> None:
        result = {
            "protocolVersion": PROTOCOL_VERSION,
            "serverInfo": SERVER_INFO,
            "capabilities": CAPABILITIES,
        }
        self._send(make_success(get_id(message), result))

    def _handle_tools_list(self, message: dict) -> None:
        self._send(make_success(get_id(message), {"tools": TOOL_DEFINITIONS}))

    def _handle_resources_list(self, message: dict) -> None:
        resources = [
            {
                "name": "cast",
                "uriTemplate": "vermyth://cast/{cast_id}",
                "description": "Read cast record by cast id.",
            },
            {
                "name": "program_execution",
                "uriTemplate": "vermyth://program_execution/{execution_id}",
                "description": "Read program execution by execution id.",
            },
            {
                "name": "execution_receipt",
                "uriTemplate": "vermyth://execution_receipt/{execution_id}",
                "description": "Read execution receipt by execution id.",
            },
            {
                "name": "program",
                "uriTemplate": "vermyth://program/{program_id}",
                "description": "Read a stored semantic program by program id.",
            },
            {
                "name": "programs",
                "uri": "vermyth://programs",
                "description": "List stored semantic programs (optional query ?limit=N, default 50).",
            },
            {
                "name": "semantic_bundles",
                "uri": "vermyth://semantic_bundles",
                "description": "List semantic bundle catalog (optional ?kind=decide|cast|compile_program).",
            },
            {
                "name": "semantic_bundle",
                "uriTemplate": "vermyth://semantic_bundle/{bundle_id}",
                "description": "Bundle manifest + compiled preview (query ?version=1).",
            },
        ]
        self._send(make_success(get_id(message), {"resources": resources}))

    def _handle_resources_read(self, message: dict) -> None:
        params = get_params(message)
        uri = str(params.get("uri", ""))
        try:
            pu = urlparse(uri)
            if pu.scheme == "vermyth" and pu.netloc == "semantic_bundles":
                qs = parse_qs(pu.query)
                raw_k = (qs.get("kind") or [None])[0]
                k = (
                    raw_k
                    if raw_k in ("decide", "cast", "compile_program")
                    else None
                )
                payload: Any = {"bundles": list_bundle_catalog(kind=k)}
                record_bundle_catalog_listed(surface="mcp_resource", kind=k)
                self._send(
                    make_success(
                        get_id(message),
                        {"contents": [{"uri": uri, "json": payload}]},
                    )
                )
                return
            if pu.scheme == "vermyth" and pu.netloc == "semantic_bundle":
                bid = pu.path.lstrip("/")
                if not bid:
                    self._send(
                        make_error(
                            get_id(message),
                            ERROR_INVALID_PARAMS,
                            "bundle_id required in vermyth://semantic_bundle/{bundle_id}",
                        )
                    )
                    return
                qs = parse_qs(pu.query)
                try:
                    ver = int((qs.get("version") or ["1"])[0])
                except ValueError as exc:
                    self._send(
                        make_error(get_id(message), ERROR_INVALID_PARAMS, str(exc))
                    )
                    return
                payload = inspect_semantic_bundle_detail(bid, ver)
                record_bundle_inspected(
                    surface="mcp_resource",
                    bundle_id=bid,
                    version=ver,
                    guided_upgrade_shown=bool(payload.get("guided_upgrade")),
                )
                self._send(
                    make_success(
                        get_id(message),
                        {"contents": [{"uri": uri, "json": payload}]},
                    )
                )
                return
        except (FileNotFoundError, ValueError) as exc:
            self._send(make_error(get_id(message), ERROR_INVALID_PARAMS, str(exc)))
            return

        if self._tools is None:
            self._send(
                make_error(
                    get_id(message),
                    ERROR_NOT_IMPLEMENTED,
                    "No engine or grimoire configured.",
                )
            )
            return
        try:
            if uri.startswith("vermyth://cast/"):
                cast_id = uri.split("/", 3)[-1]
                payload = self._tools.tool_inspect(cast_id)
            elif uri.startswith("vermyth://program_execution/"):
                execution_id = uri.split("/", 3)[-1]
                payload = self._tools.tool_execution_status(execution_id)
            elif uri.startswith("vermyth://execution_receipt/"):
                execution_id = uri.split("/", 3)[-1]
                payload = self._tools.tool_execution_receipt(execution_id)
            elif uri.startswith("vermyth://programs"):
                limit = 50
                if "?" in uri:
                    _, q = uri.split("?", 1)
                    for part in q.split("&"):
                        if part.startswith("limit="):
                            try:
                                limit = max(1, int(part.split("=", 1)[1]))
                            except ValueError as exc:
                                raise ValueError("invalid limit in programs uri") from exc
                payload = self._tools.tool_list_programs(limit=limit)
            elif uri.startswith("vermyth://program/"):
                program_id = uri[len("vermyth://program/") :].split("?")[0]
                if not program_id:
                    self._send(
                        make_error(
                            get_id(message),
                            ERROR_INVALID_PARAMS,
                            "program_id required in vermyth://program/{program_id}",
                        )
                    )
                    return
                payload = self._tools.tool_program_status(program_id)
            else:
                self._send(
                    make_error(
                        get_id(message),
                        ERROR_INVALID_PARAMS,
                        f"unknown resource uri: {uri}",
                    )
                )
                return
        except Exception as exc:
            self._send(make_error(get_id(message), ERROR_INVALID_PARAMS, str(exc)))
            return
        self._send(make_success(get_id(message), {"contents": [{"uri": uri, "json": payload}]}))

    def _handle_tools_call(self, message: dict) -> None:
        msg_id = get_id(message)
        params = get_params(message)
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        if not isinstance(arguments, dict):
            self._send(
                make_error(
                    msg_id,
                    ERROR_INVALID_PARAMS,
                    "arguments must be an object",
                )
            )
            return
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
            resolved_name, merged_args, arc_prov = resolve_tool_invocation(
                str(tool_name), arguments, telemetry_surface="mcp"
            )
            handler = TOOL_DISPATCH.get(resolved_name)
            if handler is None:
                self._send(
                    make_error(
                        msg_id,
                        ERROR_METHOD_NOT_FOUND,
                        f"Unknown tool: {resolved_name}",
                    )
                )
                return
            self._tools.enforce_tool_scope(resolved_name)
            result = handler(self._tools, merged_args)
            result = attach_arcane_provenance(result, arc_prov)
            self._send(make_success(msg_id, result))

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
            elif method == "resources/list":
                self._handle_resources_list(message)
            elif method == "resources/read":
                self._handle_resources_read(message)
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
            if self._binary_mode:
                self._run_binary()
                return
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
    try:
        grimoire, _composition, engine, _tools = build_tools_from_env(None)
    except ValueError as exc:
        print(f"[vermyth-mcp] invalid backend configuration: {exc}", file=sys.stderr)
        grimoire, _composition, engine, _tools = build_tools(None, backend=NullProjectionBackend())
    binary_mode = bool(int((os.environ.get("VERMYTH_BINARY_TRANSPORT", "0") or "0")))
    server = VermythMCPServer(engine=engine, grimoire=grimoire, binary_mode=binary_mode)
    server.run()


if __name__ == "__main__":
    main()
