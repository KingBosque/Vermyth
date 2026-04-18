import { mkdirSync } from "node:fs";
import { dirname } from "node:path";
import { homedir } from "node:os";

import BetterSqlite3 from "better-sqlite3";

import { runGrimoireMigrations } from "./migrations.js";
import { CastRepository } from "./repositories/casts.js";
import { CausalRepository } from "./repositories/causal.js";
import { DecisionRepository } from "./repositories/decisions.js";
import { DivergenceRepository } from "./repositories/divergence.js";
import { RegistryRepository } from "./repositories/registry.js";
import { ProgramsRepository, type ProgramRow } from "./repositories/programs.js";
import type { DivergenceReport } from "../schema/divergence.js";
import type { CausalQuery, CausalSubgraph } from "../schema/causal.js";
import type { PolicyDecision } from "../schema/policy.js";
import type { CastResult } from "../schema/cast-result.js";

type SqliteDb = InstanceType<typeof BetterSqlite3>;

export interface BasisVersionRow {
  version: number;
  dimensionality: number;
  aspectOrder: string[];
}

export class Grimoire {
  readonly db: SqliteDb;
  readonly casts: CastRepository;
  private readonly divergence: DivergenceRepository;
  private readonly registryRepo: RegistryRepository;
  private readonly causal: CausalRepository;
  private readonly decisions: DecisionRepository;
  private readonly programs: ProgramsRepository;

  constructor(dbPath?: string | null) {
    const path =
      dbPath === undefined || dbPath === null
        ? `${homedir()}/.vermyth/grimoire.db`
        : dbPath;
    if (!path.startsWith(":memory:")) {
      mkdirSync(dirname(path), { recursive: true });
    }
    this.db = new BetterSqlite3(path);
    this.db.pragma("journal_mode = WAL");
    this.db.pragma("foreign_keys = ON");
    runGrimoireMigrations(this.db);
    this.casts = new CastRepository(this.db);
    this.divergence = new DivergenceRepository(this.db);
    this.registryRepo = new RegistryRepository(this.db);
    this.causal = new CausalRepository(this.db);
    this.decisions = new DecisionRepository(this.db);
    this.programs = new ProgramsRepository(this.db);
  }

  readLatestBasisVersion(): BasisVersionRow {
    const row = this.db
      .prepare("SELECT * FROM basis_versions ORDER BY version DESC LIMIT 1")
      .get() as
      | {
          version: number;
          dimensionality: number;
          aspect_order_json: string;
        }
      | undefined;
    if (!row) {
      return {
        version: 0,
        dimensionality: 6,
        aspectOrder: ["VOID", "FORM", "MOTION", "MIND", "DECAY", "LIGHT"],
      };
    }
    return {
      version: row.version,
      dimensionality: row.dimensionality,
      aspectOrder: JSON.parse(row.aspect_order_json) as string[],
    };
  }

  readDivergenceThresholds() {
    return this.divergence.readDivergenceThresholds();
  }

  readDivergenceReport(castId: string): DivergenceReport | null {
    return this.divergence.readDivergenceReport(castId);
  }

  driftBranches(limit = 25): Array<Record<string, unknown>> {
    return this.divergence.driftBranches(limit);
  }

  listPrograms(limit = 50): ProgramRow[] {
    return this.programs.listPrograms(limit);
  }

  queryRegisteredAspects() {
    return this.registryRepo.queryRegisteredAspects();
  }

  queryRegisteredSigils() {
    return this.registryRepo.queryRegisteredSigils();
  }

  causalSubgraph(query: CausalQuery): CausalSubgraph {
    return this.causal.causalSubgraph(query);
  }

  readCausalEdge(edgeId: string) {
    return this.causal.readCausalEdge(edgeId);
  }

  writePolicyDecision(decision: PolicyDecision): void {
    this.decisions.writePolicyDecision(decision);
  }

  /** Alias for `casts.read` (Python `Grimoire.read`). */
  read(castId: string): CastResult {
    return this.casts.read(castId);
  }

  migrationCount(): number {
    const r = this.db.prepare("SELECT COUNT(*) AS c FROM schema_migrations").get() as { c: number };
    return r.c;
  }

  close(): void {
    this.db.close();
  }
}
