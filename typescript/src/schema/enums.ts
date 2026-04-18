export const ContradictionSeverity = {
  NONE: "NONE",
  SOFT: "SOFT",
  HARD: "HARD",
} as const;
export type ContradictionSeverity =
  (typeof ContradictionSeverity)[keyof typeof ContradictionSeverity];

export const Polarity = {
  POSITIVE: "POSITIVE",
  NEGATIVE: "NEGATIVE",
  NEUTRAL: "NEUTRAL",
} as const;
export type Polarity = (typeof Polarity)[keyof typeof Polarity];

export const ReversibilityClass = {
  REVERSIBLE: "REVERSIBLE",
  PARTIAL: "PARTIAL",
  IRREVERSIBLE: "IRREVERSIBLE",
} as const;
export type ReversibilityClass =
  (typeof ReversibilityClass)[keyof typeof ReversibilityClass];

export const SideEffectTolerance = {
  NONE: "NONE",
  LOW: "LOW",
  MEDIUM: "MEDIUM",
  HIGH: "HIGH",
} as const;
export type SideEffectTolerance =
  (typeof SideEffectTolerance)[keyof typeof SideEffectTolerance];

export const ProjectionMethod = {
  FULL: "FULL",
  PARTIAL: "PARTIAL",
} as const;
export type ProjectionMethod =
  (typeof ProjectionMethod)[keyof typeof ProjectionMethod];

export const VerdictType = {
  COHERENT: "COHERENT",
  PARTIAL: "PARTIAL",
  INCOHERENT: "INCOHERENT",
} as const;
export type VerdictType = (typeof VerdictType)[keyof typeof VerdictType];

export const EffectClass = {
  ERASURE: "ERASURE",
  MANIFESTATION: "MANIFESTATION",
  FORCE: "FORCE",
  COGNITION: "COGNITION",
  DISSOLUTION: "DISSOLUTION",
  REVELATION: "REVELATION",
  CONTAINMENT: "CONTAINMENT",
  NEGATION: "NEGATION",
  CORRUPTION: "CORRUPTION",
  ACCELERATION: "ACCELERATION",
  BINDING: "BINDING",
  EMERGENCE: "EMERGENCE",
} as const;
export type EffectClass = (typeof EffectClass)[keyof typeof EffectClass];

export const ChannelStatus = {
  COHERENT: "COHERENT",
  STRAINED: "STRAINED",
  DECOHERENT: "DECOHERENT",
} as const;
export type ChannelStatus = (typeof ChannelStatus)[keyof typeof ChannelStatus];

export const DivergenceStatus = {
  STABLE: "STABLE",
  DRIFTING: "DRIFTING",
  DIVERGED: "DIVERGED",
} as const;
export type DivergenceStatus =
  (typeof DivergenceStatus)[keyof typeof DivergenceStatus];

export const PolicyAction = {
  ALLOW: "ALLOW",
  RESHAPE: "RESHAPE",
  DENY: "DENY",
} as const;
export type PolicyAction = (typeof PolicyAction)[keyof typeof PolicyAction];

export const GenesisStatus = {
  PROPOSED: "PROPOSED",
  ACCEPTED: "ACCEPTED",
  REJECTED: "REJECTED",
  INTEGRATED: "INTEGRATED",
} as const;
export type GenesisStatus = (typeof GenesisStatus)[keyof typeof GenesisStatus];

export const CausalEdgeType = {
  CAUSES: "CAUSES",
  INHIBITS: "INHIBITS",
  ENABLES: "ENABLES",
  REQUIRES: "REQUIRES",
} as const;
export type CausalEdgeType = (typeof CausalEdgeType)[keyof typeof CausalEdgeType];
