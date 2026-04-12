"""JSON-RPC 2.0 helpers for MCP over stdio."""

from typing import Any

JSONRPC_VERSION = "2.0"
PROTOCOL_VERSION = "2024-11-05"

SERVER_INFO = {
    "name": "vermyth",
    "version": "0.1.0",
}

CAPABILITIES = {
    "tools": {},
}

ERROR_PARSE_ERROR = -32700
ERROR_INVALID_REQUEST = -32600
ERROR_METHOD_NOT_FOUND = -32601
ERROR_INVALID_PARAMS = -32602
ERROR_INTERNAL = -32603
ERROR_NOT_IMPLEMENTED = -32000


def make_success(id: Any, result: dict) -> dict:
    return {"jsonrpc": JSONRPC_VERSION, "id": id, "result": result}


def make_error(id: Any, code: int, message: str) -> dict:
    return {
        "jsonrpc": JSONRPC_VERSION,
        "id": id,
        "error": {"code": code, "message": message},
    }


def is_notification(message: dict) -> bool:
    return "id" not in message or message.get("id") is None


def get_id(message: dict) -> int | str | None:
    return message.get("id")


def get_method(message: dict) -> str | None:
    return message.get("method")


def get_params(message: dict) -> dict:
    p = message.get("params", {})
    return p if isinstance(p, dict) else {}
