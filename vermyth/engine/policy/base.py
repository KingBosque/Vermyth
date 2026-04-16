from __future__ import annotations

from typing import Protocol

from vermyth.schema import DivergenceStatus, PolicyAction, PolicyThresholds, VerdictType


class PolicyModel(Protocol):
    name: str
    version: str

    def decide(
        self,
        *,
        verdict: VerdictType,
        adjusted_resonance: float,
        divergence_status: DivergenceStatus | None,
        narrative_coherence: float | None,
        thresholds: PolicyThresholds,
    ) -> tuple[PolicyAction, str]: ...
