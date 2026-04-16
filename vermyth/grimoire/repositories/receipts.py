from __future__ import annotations

import json
import sqlite3
from datetime import datetime

from vermyth.schema import ExecutionReceipt, ProgramStatus


class ReceiptRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def write_execution_receipt(self, receipt: ExecutionReceipt) -> None:
        try:
            cur = self._conn.cursor()
            cur.execute(
                """
                INSERT INTO execution_receipts (
                    receipt_id, execution_id, program_id, status, nodes_json, started_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(receipt_id) DO UPDATE SET
                    execution_id=excluded.execution_id,
                    program_id=excluded.program_id,
                    status=excluded.status,
                    nodes_json=excluded.nodes_json,
                    started_at=excluded.started_at,
                    completed_at=excluded.completed_at
                """,
                (
                    str(receipt.receipt_id),
                    str(receipt.execution_id),
                    str(receipt.program_id),
                    str(receipt.status.value),
                    json.dumps([n.model_dump(mode="json") for n in receipt.nodes]),
                    receipt.started_at.isoformat(),
                    receipt.completed_at.isoformat() if receipt.completed_at else None,
                ),
            )
            self._conn.commit()
        except sqlite3.Error as exc:
            raise RuntimeError(str(exc)) from exc

    def read_execution_receipt(self, receipt_id: str) -> ExecutionReceipt:
        try:
            cur = self._conn.cursor()
            cur.execute(
                "SELECT * FROM execution_receipts WHERE receipt_id = ?",
                (str(receipt_id),),
            )
            row = cur.fetchone()
            if row is None:
                raise KeyError(str(receipt_id))
            completed_at = row["completed_at"]
            return ExecutionReceipt(
                receipt_id=str(row["receipt_id"]),
                execution_id=str(row["execution_id"]),
                program_id=str(row["program_id"]),
                status=ProgramStatus(str(row["status"])),
                nodes=json.loads(row["nodes_json"]),
                started_at=datetime.fromisoformat(str(row["started_at"])),
                completed_at=datetime.fromisoformat(str(completed_at)) if completed_at else None,
            )
        except KeyError:
            raise
        except sqlite3.Error as exc:
            raise RuntimeError(str(exc)) from exc

    def read_execution_receipt_by_execution(self, execution_id: str) -> ExecutionReceipt:
        try:
            cur = self._conn.cursor()
            cur.execute(
                "SELECT * FROM execution_receipts WHERE execution_id = ? LIMIT 1",
                (str(execution_id),),
            )
            row = cur.fetchone()
            if row is None:
                raise KeyError(str(execution_id))
            return self.read_execution_receipt(str(row["receipt_id"]))
        except KeyError:
            raise
        except sqlite3.Error as exc:
            raise RuntimeError(str(exc)) from exc

