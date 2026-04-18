import BetterSqlite3 from "better-sqlite3";

import { canonicalAspectKey } from "../../engine/keys.js";
import { deserializeCastResult } from "../cast-deserialize.js";
import { serializeCastResultRow } from "../cast-serialize.js";
import type { SemanticQuery } from "../../schema/semantic-query.js";
import type { CastResult } from "../../schema/cast-result.js";
import { cosineSimilarity } from "../../schema/vectors.js";
import type { SemanticVector } from "../../schema/vectors.js";

type SqliteDb = InstanceType<typeof BetterSqlite3>;

function safeCosine(a: SemanticVector, b: SemanticVector): number | null {
  try {
    return cosineSimilarity(a, b);
  } catch {
    return null;
  }
}

export class CastRepository {
  constructor(private readonly db: SqliteDb) {}

  write(result: CastResult): void {
    const existing = this.db.prepare("SELECT 1 FROM cast_results WHERE cast_id = ?").get(result.castId);
    if (existing) {
      throw new Error(`CastResult with cast_id ${JSON.stringify(result.castId)} already exists`);
    }
    const d = serializeCastResultRow(result);
    this.db
      .prepare(
        `
      INSERT INTO cast_results (
        cast_id, timestamp, intent_json, sigil_json, verdict_json,
        lineage_json, glyph_seed_id, semantic_vector_json,
        verdict_type, effect_class, adjusted_resonance, branch_id,
        provenance_json, aspect_pattern_key, basis_version,
        narrative_coherence, causal_root_cast_id
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `,
      )
      .run(
        d["cast_id"],
        d["timestamp"],
        d["intent_json"],
        d["sigil_json"],
        d["verdict_json"],
        d["lineage_json"],
        d["glyph_seed_id"],
        d["semantic_vector_json"],
        d["verdict_type"],
        d["effect_class"],
        d["adjusted_resonance"],
        d["branch_id"],
        d["provenance_json"],
        d["aspect_pattern_key"],
        d["basis_version"],
        d["narrative_coherence"],
        d["causal_root_cast_id"],
      );
  }

  read(castId: string): CastResult {
    const row = this.db.prepare("SELECT * FROM cast_results WHERE cast_id = ?").get(castId) as
      | Record<string, unknown>
      | undefined;
    if (!row) {
      throw new Error(`unknown cast_id: ${JSON.stringify(castId)}`);
    }
    return deserializeCastResult(row);
  }

  query(q: SemanticQuery): CastResult[] {
    return this.runSemanticQuery(q);
  }

  semanticSearch(q: SemanticQuery): CastResult[] {
    return this.runSemanticQuery(q);
  }

  private runSemanticQuery(q: SemanticQuery): CastResult[] {
    let sql = "SELECT * FROM cast_results WHERE 1=1";
    const params: unknown[] = [];
    if (q.verdictFilter !== undefined && q.verdictFilter !== null) {
      sql += " AND verdict_type = ?";
      params.push(q.verdictFilter);
    }
    if (q.effectClassFilter !== undefined && q.effectClassFilter !== null) {
      sql += " AND effect_class = ?";
      params.push(q.effectClassFilter);
    }
    if (q.branchId !== undefined && q.branchId !== null) {
      sql += " AND branch_id = ?";
      params.push(q.branchId);
    }
    if (q.minResonance !== undefined && q.minResonance !== null) {
      sql += " AND adjusted_resonance >= ?";
      params.push(q.minResonance);
    }
    sql += " ORDER BY timestamp DESC LIMIT ?";
    const preLimit = Math.min(2000, Math.max(50, q.limit * 20));
    params.push(preLimit);
    const rows = this.db.prepare(sql).all(...params) as Record<string, unknown>[];
    let results = rows.map((row) => deserializeCastResult(row));
    if (q.aspectFilter !== undefined && q.aspectFilter !== null && q.aspectFilter.size > 0) {
      const want = canonicalAspectKey(q.aspectFilter);
      results = results.filter((r) => canonicalAspectKey(r.sigil.aspects) === want);
    }
    if (q.proximityTo !== undefined && q.proximityTo !== null) {
      const thr = q.proximityThreshold ?? 0;
      const scored = results
        .map((r) => {
          const sim = safeCosine(q.proximityTo!, r.sigil.semanticVector);
          return { r, sim: sim === null ? -2 : sim };
        })
        .filter((x) => x.sim >= thr)
        .sort((a, b) => b.sim - a.sim);
      results = scored.map((x) => x.r);
    }
    return results.slice(0, q.limit);
  }
}
