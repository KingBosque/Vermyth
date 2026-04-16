from __future__ import annotations

from vermyth.schema import EffectType, ScoreComponent


class EffectRiskScorer:
    name = "effect_risk"

    def score(self, **context: object) -> ScoreComponent:
        effects = context.get("effects") or []
        risk = 0.0
        for effect in effects:
            effect_type = getattr(effect, "effect_type", None)
            reversible = bool(getattr(effect, "reversible", True))
            if effect_type in (EffectType.WRITE, EffectType.EXEC, EffectType.NETWORK):
                risk += 0.35
            elif effect_type == EffectType.COMPUTE:
                risk += 0.10
            if not reversible:
                risk += 0.25
        risk = max(0.0, min(1.0, risk))
        value = 1.0 - risk
        weight = float(context.get("weight", 1.0) or 1.0)
        return ScoreComponent(
            name=self.name,
            value=value,
            weight=max(0.0, weight),
            explanation=f"effect_risk={risk:.3f}",
        )

