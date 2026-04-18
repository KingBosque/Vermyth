import { z } from "zod";

export const ASPECT_CANONICAL_NAMES = [
  "VOID",
  "FORM",
  "MOTION",
  "MIND",
  "DECAY",
  "LIGHT",
] as const;
export type AspectName = (typeof ASPECT_CANONICAL_NAMES)[number];

export interface CanonicalAspect {
  readonly kind: "canonical";
  readonly name: AspectName;
  readonly polarity: -1 | 1;
  readonly entropyCoefficient: number;
  readonly symbol: string;
}

const CANONICAL: Record<AspectName, CanonicalAspect> = {
  VOID: {
    kind: "canonical",
    name: "VOID",
    polarity: -1,
    entropyCoefficient: 0.95,
    symbol: "◯",
  },
  FORM: { kind: "canonical", name: "FORM", polarity: 1, entropyCoefficient: 0.15, symbol: "⬡" },
  MOTION: {
    kind: "canonical",
    name: "MOTION",
    polarity: 1,
    entropyCoefficient: 0.55,
    symbol: "⟳",
  },
  MIND: { kind: "canonical", name: "MIND", polarity: 1, entropyCoefficient: 0.35, symbol: "◈" },
  DECAY: {
    kind: "canonical",
    name: "DECAY",
    polarity: -1,
    entropyCoefficient: 0.85,
    symbol: "※",
  },
  LIGHT: {
    kind: "canonical",
    name: "LIGHT",
    polarity: 1,
    entropyCoefficient: 0.05,
    symbol: "✦",
  },
};

export function aspectIdFromName(name: string): CanonicalAspect {
  if (name in CANONICAL) {
    return CANONICAL[name as AspectName];
  }
  throw new Error(`unknown AspectID name: ${JSON.stringify(name)}`);
}

export const RegisteredAspectSchema = z.object({
  name: z
    .string()
    .min(1)
    .max(30)
    .regex(/^[A-Z][A-Z0-9_]*$/),
  polarity: z.union([z.literal(-1), z.literal(1)]),
  entropyCoefficient: z.number().min(0).max(1),
  symbol: z.string().min(1).max(1),
});

export type RegisteredAspect = z.infer<typeof RegisteredAspectSchema> & {
  readonly kind: "registered";
};

export function toRegisteredAspect(data: z.infer<typeof RegisteredAspectSchema>): RegisteredAspect {
  return { kind: "registered", ...data };
}

export type Aspect = CanonicalAspect | RegisteredAspect;

export function aspectName(a: Aspect): string {
  return a.name;
}

export function aspectPolarity(a: Aspect): number {
  return a.polarity;
}

export function aspectEntropy(a: Aspect): number {
  return a.entropyCoefficient;
}
