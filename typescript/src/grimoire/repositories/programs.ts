import BetterSqlite3 from "better-sqlite3";

type SqliteDb = InstanceType<typeof BetterSqlite3>;

export interface ProgramRow {
  program_id: string;
  name: string;
  status: string;
  nodes_json: string;
  entry_node_ids_json: string;
  metadata_json: string;
  created_at: string;
  updated_at: string;
}

export class ProgramsRepository {
  constructor(private readonly db: SqliteDb) {}

  listPrograms(limit: number): ProgramRow[] {
    const rows = this.db
      .prepare(
        "SELECT program_id, name, status, nodes_json, entry_node_ids_json, metadata_json, created_at, updated_at FROM programs ORDER BY updated_at DESC LIMIT ?",
      )
      .all(Math.max(1, Math.min(500, Math.floor(limit)))) as ProgramRow[];
    return rows;
  }
}
