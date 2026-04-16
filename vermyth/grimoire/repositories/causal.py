from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any

from vermyth.schema import CausalEdge, CausalEdgeType, CausalQuery, CausalSubgraph


class CausalRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def write_causal_edge(self, edge: CausalEdge) -> None:
        try:
            cur = self._conn.cursor()
            cur.execute(
                """
                INSERT INTO causal_edges (
                    edge_id, source_cast_id, target_cast_id, edge_type, weight, created_at, evidence
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(edge_id) DO UPDATE SET
                    source_cast_id=excluded.source_cast_id,
                    target_cast_id=excluded.target_cast_id,
                    edge_type=excluded.edge_type,
                    weight=excluded.weight,
                    created_at=excluded.created_at,
                    evidence=excluded.evidence
                """,
                (
                    edge.edge_id,
                    edge.source_cast_id,
                    edge.target_cast_id,
                    edge.edge_type.value,
                    float(edge.weight),
                    edge.created_at.isoformat(),
                    edge.evidence,
                ),
            )
            self._conn.commit()
        except sqlite3.Error as exc:
            raise RuntimeError(str(exc)) from exc

    def read_causal_edge(self, edge_id: str) -> CausalEdge:
        try:
            cur = self._conn.cursor()
            cur.execute("SELECT * FROM causal_edges WHERE edge_id = ?", (str(edge_id),))
            row = cur.fetchone()
            if row is None:
                raise KeyError(str(edge_id))
            return CausalEdge(
                edge_id=str(row["edge_id"]),
                source_cast_id=str(row["source_cast_id"]),
                target_cast_id=str(row["target_cast_id"]),
                edge_type=CausalEdgeType(str(row["edge_type"])),
                weight=float(row["weight"]),
                created_at=datetime.fromisoformat(str(row["created_at"])),
                evidence=row["evidence"],
            )
        except KeyError:
            raise
        except sqlite3.Error as exc:
            raise RuntimeError(str(exc)) from exc

    def query_causal_edges(
        self,
        cast_id: str | None = None,
        edge_types: list[str] | None = None,
        min_weight: float = 0.0,
        limit: int = 100,
    ) -> list[CausalEdge]:
        try:
            cur = self._conn.cursor()
            sql = "SELECT * FROM causal_edges WHERE weight >= ?"
            params: list[Any] = [float(min_weight)]
            if cast_id is not None:
                sql += " AND (source_cast_id = ? OR target_cast_id = ?)"
                params.extend([str(cast_id), str(cast_id)])
            if edge_types:
                placeholders = ",".join("?" for _ in edge_types)
                sql += f" AND edge_type IN ({placeholders})"
                params.extend([str(e) for e in edge_types])
            sql += " ORDER BY created_at DESC LIMIT ?"
            params.append(int(limit))
            cur.execute(sql, tuple(params))
            out: list[CausalEdge] = []
            for row in cur.fetchall():
                out.append(
                    CausalEdge(
                        edge_id=str(row["edge_id"]),
                        source_cast_id=str(row["source_cast_id"]),
                        target_cast_id=str(row["target_cast_id"]),
                        edge_type=CausalEdgeType(str(row["edge_type"])),
                        weight=float(row["weight"]),
                        created_at=datetime.fromisoformat(str(row["created_at"])),
                        evidence=row["evidence"],
                    )
                )
            return out
        except sqlite3.Error as exc:
            raise RuntimeError(str(exc)) from exc

    def causal_subgraph(self, query: CausalQuery) -> CausalSubgraph:
        allowed = {t.value for t in query.edge_types} if query.edge_types else None
        visited_nodes: set[str] = {query.root_cast_id}
        visited_edges: dict[str, CausalEdge] = {}
        frontier: list[tuple[str, int]] = [(query.root_cast_id, 0)]

        while frontier:
            node_id, depth = frontier.pop(0)
            if depth >= int(query.max_depth):
                continue
            neighbors = self.query_causal_edges(
                cast_id=node_id,
                min_weight=float(query.min_weight),
                limit=1000,
            )
            for edge in neighbors:
                if allowed is not None and edge.edge_type.value not in allowed:
                    continue
                if query.direction == "forward" and edge.source_cast_id != node_id:
                    continue
                if query.direction == "backward" and edge.target_cast_id != node_id:
                    continue
                visited_edges[edge.edge_id] = edge
                if edge.source_cast_id not in visited_nodes:
                    visited_nodes.add(edge.source_cast_id)
                    frontier.append((edge.source_cast_id, depth + 1))
                if edge.target_cast_id not in visited_nodes:
                    visited_nodes.add(edge.target_cast_id)
                    frontier.append((edge.target_cast_id, depth + 1))

        edges = list(visited_edges.values())
        narrative = 0.0
        if edges:
            narrative = sum(float(e.weight) for e in edges) / float(len(edges))
        return CausalSubgraph(
            root_cast_id=query.root_cast_id,
            nodes=sorted(visited_nodes),
            edges=edges,
            narrative_coherence=max(0.0, min(1.0, narrative)),
        )

    def delete_causal_edge(self, edge_id: str) -> None:
        try:
            cur = self._conn.cursor()
            cur.execute("DELETE FROM causal_edges WHERE edge_id = ?", (str(edge_id),))
            if cur.rowcount == 0:
                raise KeyError(str(edge_id))
            self._conn.commit()
        except KeyError:
            raise
        except sqlite3.Error as exc:
            raise RuntimeError(str(exc)) from exc
"""Causal graph repository split placeholder."""

