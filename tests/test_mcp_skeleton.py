import io
import json
from pathlib import Path

from vermyth.mcp import protocol
from vermyth.mcp.protocol import (
    CAPABILITIES,
    ERROR_METHOD_NOT_FOUND,
    ERROR_NOT_IMPLEMENTED,
    ERROR_PARSE_ERROR,
    JSONRPC_VERSION,
    PROTOCOL_VERSION,
    SERVER_INFO,
    get_id,
    get_method,
    get_params,
    is_notification,
    make_error,
    make_success,
)
from vermyth.mcp.server import TOOL_DEFINITIONS, VermythMCPServer


def send_message(server: VermythMCPServer, message: dict) -> dict:
    """Invoke routing and return the single JSON-RPC object written to stdout."""
    server._handle_message(message)
    server._out.seek(0)
    raw = server._out.read()
    server._out.seek(0)
    server._out.truncate(0)
    text = raw.strip()
    if not text:
        return {}
    return json.loads(text)


def _fresh_server() -> VermythMCPServer:
    return VermythMCPServer(
        stdin=io.StringIO(),
        stdout=io.StringIO(),
        stderr=io.StringIO(),
    )


def test_vermyth_mcp_server_importable():
    from vermyth.mcp.server import VermythMCPServer as S

    assert S is VermythMCPServer


def test_server_instantiates_with_stringio():
    s = _fresh_server()
    assert s._running is False


def test_protocol_constants_importable():
    assert protocol.JSONRPC_VERSION == "2.0"
    assert protocol.PROTOCOL_VERSION == "2024-11-05"
    assert protocol.SERVER_INFO["name"] == "vermyth"
    assert protocol.CAPABILITIES == {"tools": {}}
    assert protocol.ERROR_PARSE_ERROR == -32700
    assert protocol.ERROR_INVALID_REQUEST == -32600
    assert protocol.ERROR_METHOD_NOT_FOUND == -32601
    assert protocol.ERROR_INVALID_PARAMS == -32602
    assert protocol.ERROR_INTERNAL == -32603
    assert protocol.ERROR_NOT_IMPLEMENTED == -32000


def test_make_success_shape():
    d = make_success(42, {"ok": True})
    assert d == {"jsonrpc": JSONRPC_VERSION, "id": 42, "result": {"ok": True}}


def test_make_error_shape():
    d = make_error("x", -32601, "nope")
    assert d["jsonrpc"] == JSONRPC_VERSION
    assert d["id"] == "x"
    assert d["error"]["code"] == -32601
    assert d["error"]["message"] == "nope"


def test_is_notification_no_id():
    assert is_notification({"jsonrpc": "2.0", "method": "x"}) is True


def test_is_notification_id_none():
    assert is_notification({"jsonrpc": "2.0", "method": "x", "id": None}) is True


def test_is_notification_with_id():
    assert is_notification({"jsonrpc": "2.0", "method": "x", "id": 1}) is False


def test_handle_initialize_response():
    s = _fresh_server()
    msg = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {"protocolVersion": "2024-11-05", "clientInfo": {}},
    }
    s._handle_initialize(msg)
    s._out.seek(0)
    out = json.loads(s._out.read())
    assert out["id"] == 1
    r = out["result"]
    assert r["protocolVersion"] == PROTOCOL_VERSION
    assert r["serverInfo"] == SERVER_INFO
    assert r["capabilities"] == CAPABILITIES


def test_handle_tools_list_tools():
    s = _fresh_server()
    s._handle_tools_list({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    s._out.seek(0)
    out = json.loads(s._out.read())
    tools = out["result"]["tools"]
    assert len(tools) == len(TOOL_DEFINITIONS)
    names = [t["name"] for t in tools]
    assert names == [
        "decide",
        "expand_semantic_bundle",
        "compile_ritual",
        "events_tail",
        "cast",
        "fluid_cast",
        "auto_cast",
        "geometric_cast",
        "inspect",
        "lineage",
        "query",
        "semantic_search",
        "crystallized_sigils",
        "seeds",
        "register_aspect",
        "register_sigil",
        "registered_aspects",
        "registered_sigils",
        "channel_status",
        "divergence",
        "divergence_reports",
        "divergence_thresholds",
        "drift_branches",
        "lineage_drift",
        "set_divergence_thresholds",
        "sync_channel",
        "compile_program",
        "execute_program",
        "execution_status",
        "execution_receipt",
        "verify_execution_receipt",
        "list_programs",
        "program_status",
        "accept_genesis",
        "genesis_proposals",
        "propose_genesis",
        "review_genesis",
        "reject_genesis",
        "add_causal_edge",
        "causal_subgraph",
        "evaluate_narrative",
        "infer_causal_edge",
        "predictive_cast",
    ]


def test_tool_definitions_match_module_constant():
    assert len(TOOL_DEFINITIONS) > 0


def test_handle_resources_list():
    s = _fresh_server()
    s._handle_resources_list({"jsonrpc": "2.0", "id": 8, "method": "resources/list"})
    s._out.seek(0)
    out = json.loads(s._out.read())
    names = [r["name"] for r in out["result"]["resources"]]
    assert names == [
        "cast",
        "program_execution",
        "execution_receipt",
        "program",
        "programs",
    ]


def test_handle_resources_read_not_implemented_without_tools():
    s = _fresh_server()
    s._handle_resources_read(
        {
            "jsonrpc": "2.0",
            "id": 9,
            "method": "resources/read",
            "params": {"uri": "vermyth://cast/abc"},
        }
    )
    s._out.seek(0)
    out = json.loads(s._out.read())
    assert out["error"]["code"] == ERROR_NOT_IMPLEMENTED


def test_handle_tools_call_not_implemented():
    s = _fresh_server()
    s._handle_tools_call(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "cast", "arguments": {}},
        }
    )
    s._out.seek(0)
    out = json.loads(s._out.read())
    assert out["error"]["code"] == -32000
    assert out["error"]["code"] == ERROR_NOT_IMPLEMENTED
    assert "no engine or grimoire" in out["error"]["message"].lower()
    s._err.seek(0)
    err_log = s._err.read()
    assert "cast" in err_log


def test_handle_message_unknown_method():
    s = _fresh_server()
    resp = send_message(
        s,
        {"jsonrpc": "2.0", "id": 99, "method": "unknown/thing", "params": {}},
    )
    assert resp["error"]["code"] == ERROR_METHOD_NOT_FOUND
    assert "unknown/thing" in resp["error"]["message"]


def test_handle_message_notifications_initialized_no_stdout():
    s = _fresh_server()
    s._handle_message(
        {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}
    )
    assert s._out.getvalue() == ""


def test_read_message_empty_line_returns_none():
    s = VermythMCPServer(
        stdin=io.StringIO("\n"),
        stdout=io.StringIO(),
        stderr=io.StringIO(),
    )
    assert s._read_message() is None
    assert s._stdin_eof is False


def test_read_message_invalid_json_sends_parse_error():
    out = io.StringIO()
    s = VermythMCPServer(
        stdin=io.StringIO("not json at all\n"),
        stdout=out,
        stderr=io.StringIO(),
    )
    assert s._read_message() is None
    out.seek(0)
    err_obj = json.loads(out.read())
    assert err_obj["id"] is None
    assert err_obj["error"]["code"] == ERROR_PARSE_ERROR


def test_log_writes_stderr():
    err = io.StringIO()
    s = VermythMCPServer(
        stdin=io.StringIO(),
        stdout=io.StringIO(),
        stderr=err,
    )
    s._log("hello")
    err.seek(0)
    assert err.read() == "[vermyth-mcp] hello\n"


def test_send_writes_json_newline():
    out = io.StringIO()
    s = VermythMCPServer(
        stdin=io.StringIO(),
        stdout=out,
        stderr=io.StringIO(),
    )
    s._send(make_success(1, {"a": 1}))
    out.seek(0)
    line = out.read()
    assert line.endswith("\n")
    assert json.loads(line.rstrip("\n")) == {
        "jsonrpc": JSONRPC_VERSION,
        "id": 1,
        "result": {"a": 1},
    }


def test_server_run_processes_two_messages_and_stops_on_eof():
    stdin = io.StringIO(
        "\n".join(
            [
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "initialize",
                        "params": {
                            "protocolVersion": PROTOCOL_VERSION,
                            "clientInfo": {},
                        },
                    }
                ),
                json.dumps({"jsonrpc": "2.0", "method": "tools/list"}),
                "",
            ]
        )
    )
    out = io.StringIO()
    err = io.StringIO()
    s = VermythMCPServer(stdin=stdin, stdout=out, stderr=err)
    s.run()
    lines = [ln for ln in out.getvalue().splitlines() if ln.strip()]
    assert len(lines) >= 1
    first = json.loads(lines[0])
    assert first["id"] == 1


def test_get_id_get_method_get_params():
    m = {"id": 5, "method": "tools/list", "params": {"x": 1}}
    assert get_id(m) == 5
    assert get_method(m) == "tools/list"
    assert get_params(m) == {"x": 1}
    assert get_params({"method": "m"}) == {}
