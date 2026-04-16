from __future__ import annotations

from pydantic import BaseModel


class CastEventPayload(BaseModel):
    cast_id: str
    verdict: str
    adjusted_resonance: float


class DecideEventPayload(BaseModel):
    cast_id: str
    action: str
    rationale: str
