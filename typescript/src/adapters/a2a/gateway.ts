/**
 * Task gateway: maps A2A-style `{ tool, arguments }` payloads to MCP tool handlers.
 * Optional idempotency matches Python `TaskGateway` when `Idempotency-Key` is used.
 */
import { createToolDispatch, type ToolHandler } from "../../mcp/tool-handlers.js";
import type { VermythTools } from "../../mcp/tools/facade.js";

export class TaskGateway {
  constructor(
    readonly tools: VermythTools,
    readonly toolDispatch: Record<string, ToolHandler> = createToolDispatch(),
    private readonly idempotencyStore: Map<string, unknown> | null = null,
  ) {}

  executeTask(
    payload: Record<string, unknown>,
    opts?: { idempotencyKey?: string | null },
  ): Record<string, unknown> {
    const key = opts?.idempotencyKey;
    if (key && this.idempotencyStore) {
      const composite = `${key}:${JSON.stringify(payload)}`;
      if (this.idempotencyStore.has(composite)) {
        return this.idempotencyStore.get(composite) as Record<string, unknown>;
      }
    }
    const tool = String(payload["tool"] ?? "");
    const args =
      payload["arguments"] && typeof payload["arguments"] === "object" && !Array.isArray(payload["arguments"])
        ? (payload["arguments"] as Record<string, unknown>)
        : {};
    const handler = this.toolDispatch[tool];
    if (!handler) {
      return { error: `unknown tool: ${tool}` };
    }
    const out = handler(this.tools, args) as Record<string, unknown>;
    if (key && this.idempotencyStore) {
      const composite = `${key}:${JSON.stringify(payload)}`;
      this.idempotencyStore.set(composite, out);
    }
    return out;
  }
}
