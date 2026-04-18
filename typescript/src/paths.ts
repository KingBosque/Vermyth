import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

/**
 * Resolve asset root: folder that contains `data/` and `grimoire/migrations/`
 * (synced copy under `typescript/assets`, or the `vermyth` Python package dir in-repo).
 */
export function getAssetRoot(): string {
  const env = process.env.VERMYTH_ASSET_ROOT;
  if (env && existsSync(env)) {
    return env;
  }
  const here = dirname(fileURLToPath(import.meta.url));
  const packaged = join(here, "..", "assets");
  if (existsSync(join(packaged, "data"))) {
    return packaged;
  }
  const vermythPkg = join(here, "..", "..", "vermyth");
  if (existsSync(join(vermythPkg, "data"))) {
    return vermythPkg;
  }
  return packaged;
}

export function sigilsDir(): string {
  return join(getAssetRoot(), "data", "sigils");
}

export function grimoireMigrationsDir(): string {
  return join(getAssetRoot(), "grimoire", "migrations");
}
