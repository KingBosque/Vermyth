from __future__ import annotations

from vermyth.schema import ScoreComponent


class NarrativeScorer:
    name = "narrative"

    def score(self, **context: object) -> ScoreComponent:
        coherence = context.get("narrative_coherence")
        value = 0.5 if coherence is None else max(0.0, min(1.0, float(coherence)))
        weight = float(context.get("weight", 1.0) or 1.0)
        text = "narrative=unknown" if coherence is None else f"narrative={float(coherence):.3f}"
        return ScoreComponent(
            name=self.name,
            value=value,
            weight=max(0.0, weight),
            explanation=text,
        )

