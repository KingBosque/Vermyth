import BetterSqlite3 from "better-sqlite3";

import type { RegisteredAspect } from "../../schema/aspect.js";
import { parseRegisteredAspect } from "../../registry.js";

type SqliteDb = InstanceType<typeof BetterSqlite3>;

export class RegistryRepository {
  constructor(private readonly db: SqliteDb) {}

  queryRegisteredAspects(): Array<[RegisteredAspect, number]> {
    const rows = this.db
      .prepare(
        "SELECT name, polarity, entropy_coefficient, symbol, ordinal FROM registered_aspects ORDER BY ordinal ASC",
      )
      .all() as Array<{
      name: string;
      polarity: number;
      entropy_coefficient: number;
      symbol: string;
      ordinal: number;
    }>;
    return rows.map((row) => [
      parseRegisteredAspect({
        name: row.name,
        polarity: row.polarity === 1 ? 1 : -1,
        entropyCoefficient: row.entropy_coefficient,
        symbol: row.symbol,
      }),
      row.ordinal,
    ]);
  }

  queryRegisteredSigils(): Array<{
    name: string;
    aspects: string[];
    effect_class: string;
    resonance_ceiling: number;
    contradiction_severity: string;
    is_override: boolean;
  }> {
    const rows = this.db.prepare("SELECT * FROM registered_sigils ORDER BY registered_at DESC").all() as Array<{
      name: string;
      aspects_json: string;
      effect_class: string;
      resonance_ceiling: number;
      contradiction_severity: string;
      is_override: number;
    }>;
    return rows.map((row) => ({
      name: row.name,
      aspects: JSON.parse(row.aspects_json) as string[],
      effect_class: row.effect_class,
      resonance_ceiling: row.resonance_ceiling,
      contradiction_severity: row.contradiction_severity,
      is_override: Boolean(row.is_override),
    }));
  }
}
