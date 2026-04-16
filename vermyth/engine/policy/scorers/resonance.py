from __future__ import annotations

from vermyth.schema import ScoreComponent


class ResonanceScorer:
    name = "resonance"

    def score(self, **context: object) -> ScoreComponent:
        adjusted = float(context.get("adjusted_resonance", 0.0) or 0.0)
        weight = float(context.get("weight", 1.0) or 1.0)
        return ScoreComponent(
            name=self.name,
            value=max(0.0, min(1.0, adjusted)),
            weight=max(0.0, weight),
            explanation=f"resonance={adjusted:.3f}",
        )

