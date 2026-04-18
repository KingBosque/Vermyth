import { createServer, type IncomingMessage, type ServerResponse } from "node:http";
import { parse } from "node:url";

import { buildToolsFromEnv } from "../bootstrap.js";
import { buildAgentCard } from "./a2a/agent-card.js";
import { TaskGateway } from "./a2a/gateway.js";
import { createToolDispatch, getToolDefinitions } from "../mcp/tool-handlers.js";
import type { VermythTools } from "../mcp/tools/facade.js";
import { getBundleAdoptionSummary, inspectSemanticBundleDetail, listBundleCatalog } from "../arcane/bundles.js";

function jsonResponse(res: ServerResponse, status: number, payload: unknown): void {
  const body = Buffer.from(JSON.stringify(payload), "utf8");
  const cors = process.env.VERMYTH_HTTP_CORS;
  const headers: Record<string, string | number> = {
    "Content-Type": "application/json",
    "Content-Length": body.length,
  };
  if (cors) {
    headers["Access-Control-Allow-Origin"] = cors;
  }
  res.writeHead(status, headers);
  res.end(body);
}

function optionsResponse(res: ServerResponse): void {
  const cors = process.env.VERMYTH_HTTP_CORS;
  const headers: Record<string, string | number> = {};
  if (cors) {
    headers["Access-Control-Allow-Origin"] = cors;
    headers["Access-Control-Allow-Headers"] =
      "Authorization, Content-Type, Idempotency-Key, X-Request-ID, X-Correlation-ID";
    headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS";
  }
  res.writeHead(204, headers);
  res.end();
}

export function createVermythHttpServer(tools: VermythTools) {
  const dispatch = createToolDispatch();
  const idempotencyStore = new Map<string, unknown>();
  const gateway = new TaskGateway(tools, dispatch, idempotencyStore);

  return createServer((req: IncomingMessage, res: ServerResponse) => {
    const token = process.env.VERMYTH_HTTP_TOKEN;
    if (token) {
      const auth = req.headers.authorization ?? "";
      if (auth !== `Bearer ${token}`) {
        jsonResponse(res, 401, { error: "unauthorized" });
        return;
      }
    }

    if (req.method === "OPTIONS") {
      optionsResponse(res);
      return;
    }

    const u = parse(req.url ?? "/", true);

    if (req.method === "GET" && u.pathname === "/healthz") {
      const latest = tools.grimoire.readLatestBasisVersion();
      const migrations = tools.grimoire.migrationCount();
      jsonResponse(res, 200, {
        status: "ok",
        migrations,
        basis_version: latest.version,
      });
      return;
    }

    if (req.method === "GET" && u.pathname === "/tools") {
      jsonResponse(res, 200, { tools: getToolDefinitions() });
      return;
    }

    const agentCardPayload = buildAgentCard(getToolDefinitions() as Array<Record<string, unknown>>);
    if (
      req.method === "GET" &&
      (u.pathname === "/.well-known/agent.json" || u.pathname === "/.well-known/agent-card.json")
    ) {
      jsonResponse(res, 200, agentCardPayload as unknown as Record<string, unknown>);
      return;
    }

    if (req.method === "GET" && u.pathname?.startsWith("/events")) {
      const n = u.query["tail"] !== undefined ? Number(u.query["tail"]) : 100;
      const eventType = typeof u.query["type"] === "string" ? u.query["type"] : null;
      const rows = tools.toolEventsTail({ n: Number.isFinite(n) ? n : 100, event_type: eventType });
      jsonResponse(res, 200, rows);
      return;
    }

    if (req.method === "GET" && u.pathname === "/arcane/telemetry") {
      jsonResponse(res, 200, getBundleAdoptionSummary());
      return;
    }

    if (req.method === "GET" && u.pathname === "/arcane/bundles") {
      const rawK = u.query["kind"];
      const k =
        rawK === "decide" || rawK === "cast" || rawK === "compile_program"
          ? rawK
          : null;
      jsonResponse(res, 200, { bundles: listBundleCatalog(k) });
      return;
    }

    if (req.method === "GET" && u.pathname?.startsWith("/arcane/bundles/")) {
      const bid = u.pathname.slice("/arcane/bundles/".length).replace(/\/$/, "");
      if (!bid || bid.includes("/")) {
        jsonResponse(res, 404, { error: "not_found" });
        return;
      }
      const verRaw = u.query["version"];
      const ver = verRaw !== undefined ? parseInt(String(verRaw), 10) : 1;
      if (!Number.isFinite(ver)) {
        jsonResponse(res, 400, { error: "invalid_version" });
        return;
      }
      try {
        const detail = inspectSemanticBundleDetail(bid, ver);
        jsonResponse(res, 200, detail);
      } catch (exc) {
        jsonResponse(res, 404, { error: exc instanceof Error ? exc.message : String(exc) });
      }
      return;
    }

    if (req.method === "POST" && u.pathname?.startsWith("/tools/")) {
      const toolName = u.pathname.slice("/tools/".length);
      const idem = req.headers["idempotency-key"];
      let data = "";
      req.on("data", (c) => {
        data += c;
      });
      req.on("end", () => {
        let payload: Record<string, unknown> = {};
        try {
          payload = data ? (JSON.parse(data) as Record<string, unknown>) : {};
        } catch {
          jsonResponse(res, 400, { error: "invalid_json" });
          return;
        }
        try {
          const composite =
            typeof idem === "string" && idem.length > 0
              ? `${idem}:${JSON.stringify({ tool: toolName, ...payload })}`
              : null;
          if (composite && idempotencyStore.has(composite)) {
            jsonResponse(res, 200, idempotencyStore.get(composite) as Record<string, unknown>);
            return;
          }
          const handler = dispatch[toolName];
          if (!handler) {
            jsonResponse(res, 404, { error: "unknown_tool" });
            return;
          }
          const out = handler(tools, payload) as Record<string, unknown>;
          if (composite) {
            idempotencyStore.set(composite, out);
          }
          jsonResponse(res, 200, out);
        } catch (exc) {
          jsonResponse(res, 400, { error: exc instanceof Error ? exc.message : String(exc) });
        }
      });
      return;
    }

    if (req.method === "POST" && u.pathname === "/a2a/tasks") {
      const idem = req.headers["idempotency-key"];
      let data = "";
      req.on("data", (c) => {
        data += c;
      });
      req.on("end", () => {
        let payload: Record<string, unknown> = {};
        try {
          payload = data ? (JSON.parse(data) as Record<string, unknown>) : {};
        } catch {
          jsonResponse(res, 400, { error: "invalid_json" });
          return;
        }
        try {
          const out = gateway.executeTask(payload, {
            idempotencyKey: typeof idem === "string" ? idem : null,
          });
          jsonResponse(res, 200, out);
        } catch (exc) {
          jsonResponse(res, 400, { error: exc instanceof Error ? exc.message : String(exc) });
        }
      });
      return;
    }

    jsonResponse(res, 404, { error: "not_found" });
  });
}

export function mainHttp(): void {
  const { tools } = buildToolsFromEnv();
  const port = Number(process.env.VERMYTH_HTTP_PORT ?? "8765");
  const host = process.env.VERMYTH_HTTP_HOST ?? "127.0.0.1";
  const server = createVermythHttpServer(tools);
  server.listen(port, host, () => {
    process.stderr.write(`vermyth http listening on http://${host}:${String(port)}\n`);
  });
}
