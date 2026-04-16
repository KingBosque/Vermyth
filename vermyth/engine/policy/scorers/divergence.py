from __future__ import annotations

from vermyth.schema import DivergenceStatus, ScoreComponent


class DivergenceScorer:
    name = "divergence"

    _VALUES = {
        None: 1.0,
        DivergenceStatus.STABLE: 1.0,
        DivergenceStatus.DRIFTING: 0.5,
        DivergenceStatus.DIVERGED: 0.0,
    }

    def score(self, **context: object) -> ScoreComponent:
        status = context.get("divergence_status")
        weight = float(context.get("weight", 1.0) or 1.0)
        value = float(self._VALUES.get(status, 0.0))
        name = status.value if isinstance(status, DivergenceStatus) else "NONE"
        return ScoreComponent(
            name=self.name,
            value=value,
            weight=max(0.0, weight),
            explanation=f"divergence={name}",
        )

