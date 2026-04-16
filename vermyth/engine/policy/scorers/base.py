from __future__ import annotations

from typing import Protocol

from vermyth.schema import ScoreComponent


class PlanScorer(Protocol):
    name: str

    def score(self, **context: object) -> ScoreComponent: ...

