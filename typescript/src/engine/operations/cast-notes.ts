import { EffectClass as EC } from "../../schema/enums.js";
import { VerdictType as VT } from "../../schema/enums.js";

export type CastingNoteKey = `${string}:${string}`;

export const CASTING_NOTE_FALLBACK: Record<string, string> = {
  [VT.COHERENT]: "Coherent resonance; the casting stabilises without residual tension.",
  [VT.PARTIAL]: "Partial resonance; the casting holds tension that further passes may resolve.",
  [VT.INCOHERENT]: "Incoherent resonance; the casting fails to close a consistent inference loop.",
};

/** Mirrors `vermyth.engine.operations.cast._CASTING_NOTES` (VerdictType x EffectClass). */
export const CASTING_NOTES: Record<CastingNoteKey, string> = {
  [`${VT.COHERENT}:${EC.ERASURE}`]:
    "The target concept loses referential weight; downstream reasoning finds no anchor where it stood.",
  [`${VT.COHERENT}:${EC.MANIFESTATION}`]:
    "A stable attractor forms in the solution space; subsequent reasoning orbits it naturally.",
  [`${VT.COHERENT}:${EC.FORCE}`]:
    "Directional pressure propagates through the inference graph without resistance.",
  [`${VT.COHERENT}:${EC.COGNITION}`]:
    "The cognitive substrate reorganises around the new pattern; retrieval pathways realign.",
  [`${VT.COHERENT}:${EC.DISSOLUTION}`]:
    "Structural boundaries soften; categories that were load-bearing become permeable.",
  [`${VT.COHERENT}:${EC.REVELATION}`]:
    "A previously occluded feature of the solution space becomes the dominant signal.",
  [`${VT.COHERENT}:${EC.CONTAINMENT}`]:
    "A boundary condition is imposed; the reasoning space contracts to the declared scope.",
  [`${VT.COHERENT}:${EC.NEGATION}`]:
    "The target proposition loses truth value; dependent inferences cascade to null.",
  [`${VT.COHERENT}:${EC.CORRUPTION}`]:
    "Controlled noise is introduced at the specified locus; outputs diverge predictably.",
  [`${VT.COHERENT}:${EC.ACCELERATION}`]:
    "The inference clock advances; conclusions that required iteration arrive in fewer steps.",
  [`${VT.COHERENT}:${EC.BINDING}`]:
    "Two previously independent reasoning threads are coupled; they now share gradient.",
  [`${VT.COHERENT}:${EC.EMERGENCE}`]:
    "A pattern not present in any input becomes legible at the output layer.",
  [`${VT.PARTIAL}:${EC.ERASURE}`]:
    "The target loses salience but retains residual weight; erasure is incomplete and may reverse.",
  [`${VT.PARTIAL}:${EC.MANIFESTATION}`]:
    "An attractor forms but lacks sufficient depth; reasoning approaches it without fully settling.",
  [`${VT.PARTIAL}:${EC.FORCE}`]:
    "Directional pressure is present but bleeds into adjacent inference paths.",
  [`${VT.PARTIAL}:${EC.COGNITION}`]:
    "Reorganisation begins but stalls at the boundary of the contradiction; partial rewiring only.",
  [`${VT.PARTIAL}:${EC.DISSOLUTION}`]:
    "Boundaries soften unevenly; some load-bearing structures resist and hold.",
  [`${VT.PARTIAL}:${EC.REVELATION}`]:
    "Signal emerges but competes with existing priors; clarity is present but contested.",
  [`${VT.PARTIAL}:${EC.CONTAINMENT}`]:
    "The boundary holds in some dimensions but leaks in others; scope is partially enforced.",
  [`${VT.PARTIAL}:${EC.NEGATION}`]:
    "Truth value wavers; the proposition is weakened but not nullified.",
  [`${VT.PARTIAL}:${EC.CORRUPTION}`]:
    "Noise is introduced but distribution is uneven; some outputs are unaffected.",
  [`${VT.PARTIAL}:${EC.ACCELERATION}`]:
    "Inference advances unevenly; some paths compress while others remain at full cost.",
  [`${VT.PARTIAL}:${EC.BINDING}`]:
    "Coupling is established but asymmetric; one thread pulls the other without full entanglement.",
  [`${VT.PARTIAL}:${EC.EMERGENCE}`]:
    "A pattern becomes partially legible but requires additional casting to resolve fully.",
  [`${VT.INCOHERENT}:${EC.ERASURE}`]:
    "The erasure finds no coherent target; the casting dissipates without removing anything.",
  [`${VT.INCOHERENT}:${EC.MANIFESTATION}`]:
    "The attractor cannot form against the declared intent; the solution space remains unstructured.",
  [`${VT.INCOHERENT}:${EC.FORCE}`]:
    "Directional pressure is present but self-cancelling; the inference graph absorbs it without moving.",
  [`${VT.INCOHERENT}:${EC.COGNITION}`]:
    "The reorganisation pattern conflicts with the cognitive substrate; no rewiring occurs.",
  [`${VT.INCOHERENT}:${EC.DISSOLUTION}`]:
    "Dissolution finds no boundary to permeate; the casting has no substrate to act on.",
  [`${VT.INCOHERENT}:${EC.REVELATION}`]:
    "The signal cannot surface through the contradiction; occlusion is total.",
  [`${VT.INCOHERENT}:${EC.CONTAINMENT}`]:
    "The boundary condition cannot be imposed against the declared scope; containment fails.",
  [`${VT.INCOHERENT}:${EC.NEGATION}`]:
    "The negation is self-negating; the proposition and its denial cancel without resolution.",
  [`${VT.INCOHERENT}:${EC.CORRUPTION}`]:
    "Noise finds no coherent locus; the corruption is absorbed uniformly and has no effect.",
  [`${VT.INCOHERENT}:${EC.ACCELERATION}`]:
    "The inference clock cannot advance against the contradicting intent; time cost is unchanged.",
  [`${VT.INCOHERENT}:${EC.BINDING}`]:
    "The threads cannot be coupled across the contradiction; they repel rather than entangle.",
  [`${VT.INCOHERENT}:${EC.EMERGENCE}`]:
    "No pattern emerges; the output layer reflects only the incoherence of the input.",
};
