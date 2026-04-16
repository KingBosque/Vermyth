from __future__ import annotations

import json
import sqlite3
from datetime import datetime

from vermyth.schema import ProgramExecution, ProgramStatus, SemanticProgram


class ProgramRepository:
    """Repository methods for semantic programs and executions."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def write_program(self, program: SemanticProgram) -> None:
        try:
            cur = self._conn.cursor()
            cur.execute(
                """
                INSERT INTO programs (
                    program_id, name, status, nodes_json, entry_node_ids_json,
                    metadata_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(program_id) DO UPDATE SET
                    name=excluded.name,
                    status=excluded.status,
                    nodes_json=excluded.nodes_json,
                    entry_node_ids_json=excluded.entry_node_ids_json,
                    metadata_json=excluded.metadata_json,
                    created_at=excluded.created_at,
                    updated_at=excluded.updated_at
                """,
                (
                    str(program.program_id),
                    str(program.name),
                    str(program.status.value),
                    json.dumps([n.model_dump(mode="json") for n in program.nodes]),
                    json.dumps(list(program.entry_node_ids)),
                    json.dumps(program.metadata),
                    program.created_at.isoformat(),
                    program.updated_at.isoformat(),
                ),
            )
            self._conn.commit()
        except sqlite3.Error as exc:
            raise RuntimeError(str(exc)) from exc

    def read_program(self, program_id: str) -> SemanticProgram:
        try:
            cur = self._conn.cursor()
            cur.execute("SELECT * FROM programs WHERE program_id = ?", (str(program_id),))
            row = cur.fetchone()
            if row is None:
                raise KeyError(str(program_id))
            nodes = json.loads(row["nodes_json"])
            entries = json.loads(row["entry_node_ids_json"])
            metadata = json.loads(row["metadata_json"])
            return SemanticProgram(
                program_id=str(row["program_id"]),
                name=str(row["name"]),
                status=ProgramStatus(str(row["status"])),
                nodes=nodes,
                entry_node_ids=entries,
                metadata=metadata,
                created_at=datetime.fromisoformat(str(row["created_at"])),
                updated_at=datetime.fromisoformat(str(row["updated_at"])),
            )
        except KeyError:
            raise
        except sqlite3.Error as exc:
            raise RuntimeError(str(exc)) from exc

    def query_programs(self, limit: int = 50) -> list[SemanticProgram]:
        try:
            cur = self._conn.cursor()
            cur.execute(
                """
                SELECT * FROM programs
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (int(limit),),
            )
            out: list[SemanticProgram] = []
            for row in cur.fetchall():
                out.append(
                    SemanticProgram(
                        program_id=str(row["program_id"]),
                        name=str(row["name"]),
                        status=ProgramStatus(str(row["status"])),
                        nodes=json.loads(row["nodes_json"]),
                        entry_node_ids=json.loads(row["entry_node_ids_json"]),
                        metadata=json.loads(row["metadata_json"]),
                        created_at=datetime.fromisoformat(str(row["created_at"])),
                        updated_at=datetime.fromisoformat(str(row["updated_at"])),
                    )
                )
            return out
        except sqlite3.Error as exc:
            raise RuntimeError(str(exc)) from exc

    def write_execution(self, execution: ProgramExecution) -> None:
        try:
            cur = self._conn.cursor()
            cur.execute(
                """
                INSERT INTO program_executions (
                    execution_id, program_id, status, node_results_json,
                    started_at, completed_at, branch_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(execution_id) DO UPDATE SET
                    program_id=excluded.program_id,
                    status=excluded.status,
                    node_results_json=excluded.node_results_json,
                    started_at=excluded.started_at,
                    completed_at=excluded.completed_at,
                    branch_id=excluded.branch_id
                """,
                (
                    str(execution.execution_id),
                    str(execution.program_id),
                    str(execution.status.value),
                    json.dumps(execution.node_results),
                    execution.started_at.isoformat(),
                    execution.completed_at.isoformat() if execution.completed_at else None,
                    str(execution.branch_id),
                ),
            )
            self._conn.commit()
        except sqlite3.Error as exc:
            raise RuntimeError(str(exc)) from exc

    def read_execution(self, execution_id: str) -> ProgramExecution:
        try:
            cur = self._conn.cursor()
            cur.execute(
                "SELECT * FROM program_executions WHERE execution_id = ?",
                (str(execution_id),),
            )
            row = cur.fetchone()
            if row is None:
                raise KeyError(str(execution_id))
            completed_at = row["completed_at"]
            return ProgramExecution(
                execution_id=str(row["execution_id"]),
                program_id=str(row["program_id"]),
                status=ProgramStatus(str(row["status"])),
                node_results=json.loads(row["node_results_json"]),
                started_at=datetime.fromisoformat(str(row["started_at"])),
                completed_at=datetime.fromisoformat(str(completed_at)) if completed_at else None,
                branch_id=str(row["branch_id"]),
            )
        except KeyError:
            raise
        except sqlite3.Error as exc:
            raise RuntimeError(str(exc)) from exc

    def query_executions(self, program_id: str, limit: int = 50) -> list[ProgramExecution]:
        try:
            cur = self._conn.cursor()
            cur.execute(
                """
                SELECT * FROM program_executions
                WHERE program_id = ?
                ORDER BY started_at DESC
                LIMIT ?
                """,
                (str(program_id), int(limit)),
            )
            out: list[ProgramExecution] = []
            for row in cur.fetchall():
                completed_at = row["completed_at"]
                out.append(
                    ProgramExecution(
                        execution_id=str(row["execution_id"]),
                        program_id=str(row["program_id"]),
                        status=ProgramStatus(str(row["status"])),
                        node_results=json.loads(row["node_results_json"]),
                        started_at=datetime.fromisoformat(str(row["started_at"])),
                        completed_at=(
                            datetime.fromisoformat(str(completed_at)) if completed_at else None
                        ),
                        branch_id=str(row["branch_id"]),
                    )
                )
            return out
        except sqlite3.Error as exc:
            raise RuntimeError(str(exc)) from exc
