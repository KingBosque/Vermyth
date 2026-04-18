export const JSONRPC_VERSION = "2.0";
export const PROTOCOL_VERSION = "2024-11-05";

export const SERVER_INFO = {
  name: "vermyth",
  version: "0.1.0",
};

export const CAPABILITIES = {
  tools: {},
};

export const ERROR_PARSE_ERROR = -32700;
export const ERROR_INVALID_REQUEST = -32600;
export const ERROR_METHOD_NOT_FOUND = -32601;
export const ERROR_INVALID_PARAMS = -32602;
export const ERROR_INTERNAL = -32603;
export const ERROR_NOT_IMPLEMENTED = -32000;

export function makeSuccess(id: unknown, result: Record<string, unknown>): Record<string, unknown> {
  return { jsonrpc: JSONRPC_VERSION, id, result };
}

export function makeError(id: unknown, code: number, message: string): Record<string, unknown> {
  return {
    jsonrpc: JSONRPC_VERSION,
    id,
    error: { code, message },
  };
}

export function isNotification(message: Record<string, unknown>): boolean {
  return !("id" in message) || message["id"] === null;
}

export function getId(message: Record<string, unknown>): unknown {
  return message["id"];
}

export function getMethod(message: Record<string, unknown>): string | undefined {
  const m = message["method"];
  return typeof m === "string" ? m : undefined;
}

export function getParams(message: Record<string, unknown>): Record<string, unknown> {
  const p = message["params"];
  return p && typeof p === "object" && !Array.isArray(p) ? (p as Record<string, unknown>) : {};
}
