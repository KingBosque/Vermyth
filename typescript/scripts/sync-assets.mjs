import { cp, mkdir } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(fileURLToPath(new URL(".", import.meta.url)), "..");
const repoRoot = join(root, "..");
const assetsDir = join(root, "assets");

await mkdir(join(assetsDir, "data"), { recursive: true });
await mkdir(join(assetsDir, "grimoire", "migrations"), { recursive: true });

await cp(join(repoRoot, "vermyth", "data"), join(assetsDir, "data"), {
  recursive: true,
  force: true,
});
await cp(join(repoRoot, "vermyth", "grimoire", "migrations"), join(assetsDir, "grimoire", "migrations"), {
  recursive: true,
  force: true,
});

console.log("synced vermyth data + grimoire migrations into typescript/assets");
