import BetterSqlite3 from "better-sqlite3";

import type { CausalEdge, CausalQuery, CausalSubgraph } from "../../schema/causal.js";
import { CausalEdgeTypes, type CausalEdgeType } from "../../schema/causal.js";

type SqliteDb = InstanceType<typeof BetterSqlite3>;

function parseEdgeType(raw: string): CausalEdgeType {
  const v = Object.values(CausalEdgeTypes) as string[];
  if (!v.includes(raw)) {
    throw new Error(`invalid causal edge_type: ${JSON.stringify(raw)}`);
  }
  return raw as CausalEdgeType;
}

function rowToEdge(row: Record<string, unknown>): CausalEdge {
  return {
    edgeId: String(row["edge_id"]),
    sourceCastId: String(row["source_cast_id"]),
    targetCastId: String(row["target_cast_id"]),
    edgeType: parseEdgeType(String(row["edge_type"])),
    weight: Number(row["weight"]),
    createdAt: new Date(String(row["created_at"])),
    evidence: row["evidence"] === null || row["evidence"] === undefined ? null : String(row["evidence"]),
  };
}

export class CausalRepository {
  constructor(private readonly db: SqliteDb) {}

  readCausalEdge(edgeId: string): CausalEdge {
    const row = this.db.prepare("SELECT * FROM causal_edges WHERE edge_id = ?").get(edgeId) as
      | Record<string, unknown>
      | undefined;
    if (!row) {
      throw new Error(`unknown causal edge_id: ${JSON.stringify(edgeId)}`);
    }
    return rowToEdge(row);
  }

  queryCausalEdges(opts: {
    castId?: string | null;
    edgeTypes?: readonly string[] | null;
    minWeight?: number;
    limit?: number;
  }): CausalEdge[] {
    const minWeight = opts.minWeight ?? 0;
    let sql = "SELECT * FROM causal_edges WHERE weight >= ?";
    const params: unknown[] = [minWeight];
    if (opts.castId !== undefined && opts.castId !== null) {
      sql += " AND (source_cast_id = ? OR target_cast_id = ?)";
      params.push(opts.castId, opts.castId);
    }
    if (opts.edgeTypes !== undefined && opts.edgeTypes !== null && opts.edgeTypes.length > 0) {
      sql += ` AND edge_type IN (${opts.edgeTypes.map(() => "?").join(",")})`;
      params.push(...opts.edgeTypes);
    }
    sql += " ORDER BY created_at DESC LIMIT ?";
    params.push(opts.limit ?? 100);
    const rows = this.db.prepare(sql).all(...params) as Record<string, unknown>[];
    return rows.map(rowToEdge);
  }

  causalSubgraph(query: CausalQuery): CausalSubgraph {
    const allowed =
      query.edgeTypes !== undefined && query.edgeTypes !== null && query.edgeTypes.length > 0
        ? new Set(query.edgeTypes.map((t) => String(t)))
        : null;
    const visitedNodes = new Set<string>([query.rootCastId]);
    const visitedEdges = new Map<string, CausalEdge>();
    const frontier: Array<{ id: string; depth: number }> = [{ id: query.rootCastId, depth: 0 }];

    while (frontier.length > 0) {
      const { id: nodeId, depth } = frontier.shift()!;
      if (depth >= query.maxDepth) {
        continue;
      }
      const neighbors = this.queryCausalEdges({
        castId: nodeId,
        minWeight: query.minWeight,
        limit: 1000,
      });
      for (const edge of neighbors) {
        if (allowed !== null && !allowed.has(edge.edgeType)) {
          continue;
        }
        if (query.direction === "forward" && edge.sourceCastId !== nodeId) {
          continue;
        }
        if (query.direction === "backward" && edge.targetCastId !== nodeId) {
          continue;
        }
        visitedEdges.set(edge.edgeId, edge);
        if (!visitedNodes.has(edge.sourceCastId)) {
          visitedNodes.add(edge.sourceCastId);
          frontier.push({ id: edge.sourceCastId, depth: depth + 1 });
        }
        if (!visitedNodes.has(edge.targetCastId)) {
          visitedNodes.add(edge.targetCastId);
          frontier.push({ id: edge.targetCastId, depth: depth + 1 });
        }
      }
    }

    const edges = [...visitedEdges.values()];
    let narrative = 0;
    if (edges.length > 0) {
      narrative = edges.reduce((a, e) => a + e.weight, 0) / edges.length;
    }
    return {
      rootCastId: query.rootCastId,
      nodes: [...visitedNodes].sort(),
      edges,
      narrativeCoherence: Math.max(0, Math.min(1, narrative)),
    };
  }
}
