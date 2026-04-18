#!/usr/bin/env node
import { Command } from "commander";

import { buildToolsFromEnv } from "../bootstrap.js";
import { castAspectNames } from "../engine/operations/casting.js";
import type { Intent } from "../schema/intent.js";

function parseIntentLike(s: string): Intent {
  const j = JSON.parse(s) as Record<string, unknown>;
  return {
    objective: String(j["objective"] ?? ""),
    scope: String(j["scope"] ?? ""),
    reversibility: j["reversibility"] as Intent["reversibility"],
    sideEffectTolerance: (j["side_effect_tolerance"] ?? j["sideEffectTolerance"]) as Intent["sideEffectTolerance"],
  };
}

const program = new Command();
program.name("vermyth-ts").description("Vermyth CLI (TypeScript)").version("0.1.0");

program
  .command("cast")
  .description("Compose aspects and evaluate intent")
  .requiredOption("--aspects <names>", "Comma-separated AspectID names, e.g. VOID,FORM")
  .requiredOption("--intent <json>", "JSON object with objective, scope, reversibility, side_effect_tolerance")
  .action((opts: { aspects: string; intent: string }) => {
    const { engine } = buildToolsFromEnv();
    const aspects = opts.aspects.split(",").map((s) => s.trim());
    const intent = parseIntentLike(opts.intent);
    const result = castAspectNames(engine, aspects, intent);
    console.log(JSON.stringify(result, null, 2));
  });

program
  .command("decide")
  .description("Run policy decision (cast + decision record)")
  .requiredOption("--intent <json>", "Intent JSON")
  .option("--aspects <names>", "Comma-separated aspect names")
  .option("--vector <json>", "Semantic vector JSON array")
  .option("--parent-cast-id <id>", "Parent cast for drift scoring")
  .option("--causal-root-cast-id <id>", "Causal root for narrative scoring")
  .action(
    (opts: {
      intent: string;
      aspects?: string;
      vector?: string;
      parentCastId?: string;
      causalRootCastId?: string;
    }) => {
      const { tools } = buildToolsFromEnv();
      const intent = parseIntentLike(opts.intent);
      const args: Record<string, unknown> = { intent };
      if (opts.aspects) {
        args["aspects"] = opts.aspects.split(",").map((s) => s.trim());
      }
      if (opts.vector) {
        args["vector"] = JSON.parse(opts.vector) as unknown[];
      }
      if (opts.parentCastId) {
        args["parent_cast_id"] = opts.parentCastId;
      }
      if (opts.causalRootCastId) {
        args["causal_root_cast_id"] = opts.causalRootCastId;
      }
      const out = tools.toolDecide(args);
      console.log(JSON.stringify(out, null, 2));
    },
  );

const query = program.command("query").description("Query grimoire");

query
  .command("casts")
  .description("Filter casts (JSON options as --filters)")
  .option("--filters <json>", "Semantic query filters object", "{}")
  .action((opts: { filters: string }) => {
    const { tools } = buildToolsFromEnv();
    const f = JSON.parse(opts.filters) as Record<string, unknown>;
    console.log(JSON.stringify(tools.toolQueryCasts(f), null, 2));
  });

program
  .command("inspect")
  .description("Load one cast by id")
  .requiredOption("--cast-id <id>", "Cast ULID")
  .action((opts: { castId: string }) => {
    const { tools } = buildToolsFromEnv();
    console.log(JSON.stringify(tools.toolInspect({ cast_id: opts.castId }), null, 2));
  });

const registry = program.command("registry").description("Extension registry");

registry
  .command("aspects")
  .description("List registered aspects")
  .action(() => {
    const { tools } = buildToolsFromEnv();
    console.log(JSON.stringify(tools.toolRegisteredAspects({}), null, 2));
  });

registry
  .command("sigils")
  .description("List registered sigils")
  .action(() => {
    const { tools } = buildToolsFromEnv();
    console.log(JSON.stringify(tools.toolRegisteredSigils({}), null, 2));
  });

program
  .command("drift")
  .description("Drift tooling (stub)")
  .action(() => {
    const { tools } = buildToolsFromEnv();
    console.log(JSON.stringify(tools.toolDriftBranches({}), null, 2));
  });

program
  .command("session")
  .description("Session tooling (stub)")
  .action(() => {
    console.log(JSON.stringify({ stub: true, message: "sessions not ported in TypeScript" }, null, 2));
  });

program
  .command("events")
  .description("Observability events")
  .option("--tail <n>", "Last N events", "50")
  .action((opts: { tail: string }) => {
    const { tools } = buildToolsFromEnv();
    const n = parseInt(opts.tail, 10);
    console.log(JSON.stringify(tools.toolEventsTail({ n }), null, 2));
  });

program
  .command("auto-cast")
  .description("Iterative auto_cast")
  .requiredOption("--vector <json>", "Seed vector JSON array")
  .requiredOption("--intent <json>", "Intent JSON")
  .action((opts: { vector: string; intent: string }) => {
    const { tools } = buildToolsFromEnv();
    const intent = parseIntentLike(opts.intent);
    const vector = JSON.parse(opts.vector) as unknown[];
    console.log(
      JSON.stringify(
        tools.toolAutoCast({
          vector,
          objective: intent.objective,
          scope: intent.scope,
          reversibility: intent.reversibility,
          side_effect_tolerance: intent.sideEffectTolerance,
        }),
        null,
        2,
      ),
    );
  });

program
  .command("swarm")
  .description("Swarm federation (stub unless VERMYTH_EXPERIMENTAL_TOOLS)")
  .action(() => {
    const { tools } = buildToolsFromEnv();
    console.log(JSON.stringify(tools.toolSwarmCast({}), null, 2));
  });

program
  .command("programs")
  .description("Semantic programs (stub)")
  .action(() => {
    const { tools } = buildToolsFromEnv();
    console.log(JSON.stringify(tools.toolListPrograms({}), null, 2));
  });

program
  .command("genesis")
  .description("Genesis review (stub)")
  .action(() => {
    console.log(JSON.stringify({ stub: true }, null, 2));
  });

program
  .command("causal")
  .description("Causal graph helpers")
  .requiredOption("--root <id>", "Root cast id")
  .action((opts: { root: string }) => {
    const { tools } = buildToolsFromEnv();
    console.log(JSON.stringify(tools.toolCausalSubgraph({ root_cast_id: opts.root }), null, 2));
  });

program
  .command("bundle-report")
  .description("Bundle report (stub)")
  .action(() => {
    console.log(JSON.stringify({ stub: true }, null, 2));
  });

program.parse();
