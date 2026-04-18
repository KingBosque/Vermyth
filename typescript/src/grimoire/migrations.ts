import { readFileSync } from "node:fs";
import { join } from "node:path";

import BetterSqlite3 from "better-sqlite3";
import { grimoireMigrationsDir } from "../paths.js";

type SqliteDb = InstanceType<typeof BetterSqlite3>;

const MIGRATIONS: Array<[string, string]> = [
  ["v001", "v001_initial.sql"],
  ["v002", "v002_crystallized_loop.sql"],
  ["v003", "v003_extension_api.sql"],
  ["v004", "v004_divergence_detection.sql"],
  ["v005", "v005_observability_indexes.sql"],
  ["v006", "v006_cast_aspect_pattern_key.sql"],
  ["v007", "v007_channel_states.sql"],
  ["v008", "v008_sessions.sql"],
  ["v009", "v009_swarm_federation.sql"],
  ["v010", "v010_semantic_programs.sql"],
  ["v011", "v011_emergent_aspects.sql"],
  ["v012", "v012_causal_graph.sql"],
  ["v013", "v013_basis_versions.sql"],
  ["v014", "v014_policy_decisions.sql"],
  ["v015", "v015_cast_provenance_extend.sql"],
  ["v016", "v016_policy_decision_model.sql"],
  ["v017", "v017_program_effects.sql"],
  ["v018", "v018_execution_receipts.sql"],
  ["v019", "v019_genesis_review.sql"],
  ["v020", "v020_execution_receipt_audit.sql"],
  ["v021", "v021_execution_receipt_arcane.sql"],
];

export function runGrimoireMigrations(db: SqliteDb): void {
  const dir = grimoireMigrationsDir();
  const applied = new Set<string>();
  const hasTable = db
    .prepare(
      "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations'",
    )
    .get() as { name: string } | undefined;
  if (hasTable) {
    const rows = db.prepare("SELECT version FROM schema_migrations").all() as Array<{
      version: string;
    }>;
    for (const r of rows) {
      applied.add(r.version);
    }
  }
  for (const [version, file] of MIGRATIONS) {
    if (applied.has(version)) {
      continue;
    }
    const sqlPath = join(dir, file);
    const sql = readFileSync(sqlPath, "utf8");
    db.exec(sql);
    db.prepare("INSERT INTO schema_migrations (version, applied_at) VALUES (?, datetime('now'))").run(
      version,
    );
  }
}
