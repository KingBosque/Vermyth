import type { Aspect, RegisteredAspect } from "./schema/aspect.js";
import {
  ASPECT_CANONICAL_NAMES,
  aspectIdFromName,
  toRegisteredAspect,
  RegisteredAspectSchema,
} from "./schema/aspect.js";

let registeredAspects: RegisteredAspect[] = [];
let basisVersion = 0;

function readBasisVersionInternal(): number {
  return basisVersion;
}

function applyBasisVersionInternal(value: number): void {
  basisVersion = Math.max(0, Math.floor(value));
}

export function fullAspectOrder(): readonly Aspect[] {
  const canonical = ASPECT_CANONICAL_NAMES.map((n) => aspectIdFromName(n));
  return [...canonical, ...registeredAspects];
}

export function registeredAspectsList(): RegisteredAspect[] {
  return [...registeredAspects];
}

export function getBasisVersion(): number {
  return readBasisVersionInternal();
}

export function setBasisVersion(value: number): void {
  applyBasisVersionInternal(value);
}

export function resetRegisteredAspectsForTests(): void {
  registeredAspects = [];
  basisVersion = 0;
}

export function registerAspect(aspect: RegisteredAspect): void {
  for (const n of ASPECT_CANONICAL_NAMES) {
    if (n === aspect.name) {
      throw new Error(`Aspect ${JSON.stringify(aspect.name)} conflicts with canonical AspectID`);
    }
  }
  if (registeredAspects.some((a) => a.name === aspect.name)) {
    throw new Error(`Aspect ${JSON.stringify(aspect.name)} already exists`);
  }
  registeredAspects.push(aspect);
  basisVersion += 1;
}

export function parseRegisteredAspect(input: unknown): RegisteredAspect {
  return toRegisteredAspect(RegisteredAspectSchema.parse(input));
}

export class AspectRegistry {
  private static instance: AspectRegistry | undefined;

  static get(): AspectRegistry {
    if (!AspectRegistry.instance) {
      AspectRegistry.instance = new AspectRegistry();
    }
    return AspectRegistry.instance;
  }

  static reset(): void {
    AspectRegistry.instance = undefined;
    resetRegisteredAspectsForTests();
  }

  get dimensionality(): number {
    return fullAspectOrder().length;
  }

  get fullOrder(): readonly Aspect[] {
    return fullAspectOrder();
  }

  resolve(name: string): Aspect {
    try {
      return aspectIdFromName(name);
    } catch {
      const found = registeredAspects.find((a) => a.name === name);
      if (found) {
        return found;
      }
      throw new Error(`unknown aspect: ${JSON.stringify(name)}`);
    }
  }

  isRegistered(name: string): boolean {
    return registeredAspects.some((a) => a.name === name);
  }

  register(aspect: RegisteredAspect): void {
    registerAspect(aspect);
  }

  getBasisVersion(): number {
    return readBasisVersionInternal();
  }

  setBasisVersion(version: number): void {
    applyBasisVersionInternal(version);
  }
}
