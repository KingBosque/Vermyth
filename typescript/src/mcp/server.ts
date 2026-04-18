import { createInterface } from "node:readline";
import { parse as parseUrl } from "node:url";

import { buildToolsFromEnv } from "../bootstrap.js";
import type { VermythTools } from "./tools/facade.js";
import { inspectSemanticBundleDetail, listBundleCatalog } from "../arcane/bundles.js";
import { castResultToDict } from "./cast-result-json.js";
import {
  CAPABILITIES,
  ERROR_INTERNAL,
  ERROR_INVALID_PARAMS,
  ERROR_METHOD_NOT_FOUND,
  ERROR_PARSE_ERROR,
  PROTOCOL_VERSION,
  SERVER_INFO,
  getId,
  getMethod,
  getParams,
  isNotification,
  makeError,
  makeSuccess,
} from "./protocol.js";
import { createToolDispatch, getToolDefinitions } from "./tool-handlers.js";

export class VermythMcpServer {
  private tools: VermythTools;
  private readonly dispatch: ReturnType<typeof createToolDispatch>;

  constructor(tools?: VermythTools) {
    if (tools) {
      this.tools = tools;
    } else {
      this.tools = buildToolsFromEnv().tools;
    }
    this.dispatch = createToolDispatch();
  }

  handleMessage(raw: Record<string, unknown>): Record<string, unknown> | null {
    const method = getMethod(raw);
    const id = getId(raw);
    if (isNotification(raw)) {
      return null;
    }
    if (method === "initialize") {
      return makeSuccess(id, {
        protocolVersion: PROTOCOL_VERSION,
        serverInfo: SERVER_INFO,
        capabilities: CAPABILITIES,
      });
    }
    if (method === "tools/list") {
      return makeSuccess(id, { tools: getToolDefinitions() });
    }
    if (method === "tools/call") {
      const params = getParams(raw);
      const name = params["name"];
      const args = params["arguments"];
      if (typeof name !== "string") {
        return makeError(id, ERROR_INVALID_PARAMS, "tools/call requires params.name");
      }
      const argObj = args && typeof args === "object" && !Array.isArray(args) ? (args as Record<string, unknown>) : {};
      const handler = this.dispatch[name];
      if (!handler) {
        return makeError(id, ERROR_METHOD_NOT_FOUND, `unknown tool: ${name}`);
      }
      try {
        const result = handler(this.tools, argObj);
        return makeSuccess(id, { content: [{ type: "text", text: JSON.stringify(result) }] });
      } catch (exc) {
        return makeError(id, ERROR_INTERNAL, exc instanceof Error ? exc.message : String(exc));
      }
    }
    if (method === "resources/list") {
      const resources = [
        {
          name: "cast",
          uriTemplate: "vermyth://cast/{cast_id}",
          description: "Read cast record by cast id.",
        },
        {
          name: "program_execution",
          uriTemplate: "vermyth://program_execution/{execution_id}",
          description: "Read program execution by execution id.",
        },
        {
          name: "execution_receipt",
          uriTemplate: "vermyth://execution_receipt/{execution_id}",
          description: "Read execution receipt by execution id.",
        },
        {
          name: "program",
          uriTemplate: "vermyth://program/{program_id}",
          description: "Read a stored semantic program by program id.",
        },
        {
          name: "programs",
          uri: "vermyth://programs",
          description: "List stored semantic programs (optional query ?limit=N, default 50).",
        },
        {
          name: "semantic_bundles",
          uri: "vermyth://semantic_bundles",
          description: "List semantic bundle catalog (optional ?kind=decide|cast|compile_program).",
        },
        {
          name: "semantic_bundle",
          uriTemplate: "vermyth://semantic_bundle/{bundle_id}",
          description: "Bundle manifest + compiled preview (query ?version=1).",
        },
      ];
      return makeSuccess(id, { resources });
    }
    if (method === "resources/read") {
      const params = getParams(raw);
      const uri = String(params["uri"] ?? "");
      try {
        const pu = parseUrl(uri, true);
        if (pu.protocol === "vermyth:" && pu.hostname === "semantic_bundles") {
          const kind = pu.query["kind"] as string | undefined;
          const k =
            kind === "decide" || kind === "cast" || kind === "compile_program" ? kind : null;
          const payload = { bundles: listBundleCatalog(k) };
          return makeSuccess(id, { contents: [{ uri, json: payload }] });
        }
        if (pu.protocol === "vermyth:" && pu.hostname === "semantic_bundle") {
          const bid = (pu.pathname ?? "/").replace(/^\//, "");
          if (!bid) {
            return makeError(id, ERROR_INVALID_PARAMS, "bundle_id required in vermyth://semantic_bundle/{bundle_id}");
          }
          let ver = 1;
          const vq = pu.query["version"];
          if (typeof vq === "string") {
            ver = parseInt(vq, 10);
          } else if (Array.isArray(vq) && vq[0]) {
            ver = parseInt(String(vq[0]), 10);
          }
          const payload = inspectSemanticBundleDetail(bid, ver);
          return makeSuccess(id, { contents: [{ uri, json: payload }] });
        }
        if (pu.protocol === "vermyth:" && pu.hostname === "cast") {
          const castId = (pu.pathname ?? "/").replace(/^\//, "");
          if (!castId) {
            return makeError(id, ERROR_INVALID_PARAMS, "cast_id required");
          }
          try {
            const row = this.tools.grimoire.read(castId);
            return makeSuccess(id, {
              contents: [{ uri, json: castResultToDict(row, { grimoire: this.tools.grimoire }) }],
            });
          } catch (e) {
            return makeError(id, ERROR_INVALID_PARAMS, e instanceof Error ? e.message : String(e));
          }
        }
        if (pu.protocol === "vermyth:" && pu.hostname === "programs") {
          return makeSuccess(id, {
            contents: [{ uri, json: { programs: [], stub: true } }],
          });
        }
        return makeError(id, ERROR_INVALID_PARAMS, `unsupported resource uri: ${uri}`);
      } catch (exc) {
        return makeError(id, ERROR_INTERNAL, exc instanceof Error ? exc.message : String(exc));
      }
    }
    return makeError(id, ERROR_METHOD_NOT_FOUND, `method not found: ${String(method)}`);
  }

  async runStdio(): Promise<void> {
    const rl = createInterface({ input: process.stdin, crlfDelay: Infinity });
    for await (const line of rl) {
      const trimmed = line.trim();
      if (trimmed === "") {
        continue;
      }
      let msg: Record<string, unknown>;
      try {
        const parsed: unknown = JSON.parse(trimmed);
        if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
          process.stdout.write(`${JSON.stringify(makeError(null, ERROR_PARSE_ERROR, "expected object"))}\n`);
          continue;
        }
        msg = parsed as Record<string, unknown>;
      } catch {
        process.stdout.write(`${JSON.stringify(makeError(null, ERROR_PARSE_ERROR, "invalid JSON"))}\n`);
        continue;
      }
      const out = this.handleMessage(msg);
      if (out) {
        process.stdout.write(`${JSON.stringify(out)}\n`);
      }
    }
  }
}
