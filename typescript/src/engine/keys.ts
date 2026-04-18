import type { Aspect } from "../schema/aspect.js";
import { AspectRegistry } from "../registry.js";

export function canonicalAspectKey(aspects: ReadonlySet<Aspect>): string {
  const order = AspectRegistry.get().fullOrder;
  const orderIndex = new Map(order.map((a, i) => [a.name, i]));
  const ordered = [...aspects].sort(
    (a, b) => (orderIndex.get(a.name) ?? 1e9) - (orderIndex.get(b.name) ?? 1e9),
  );
  return ordered.map((a) => a.name).join("+");
}
