from __future__ import annotations

from vermyth.registry import AspectRegistry
from vermyth.schema import (
    AspectID,
    CastResult,
    ChannelState,
    ChannelStatus,
    Intent,
    IntentVector,
    SemanticVector,
    VerdictType,
)
from ulid import ULID


def swarm_cast(
    engine,
    intent: Intent,
    members: list[tuple[str, SemanticVector, int]],
    *,
    consensus_threshold: float = 0.75,
):
    if not members:
        raise ValueError("swarm requires at least one member")
    dim = AspectRegistry.get().dimensionality
    weights = [1.0 + 0.01 * min(100, int(streak)) for _, _, streak in members]
    acc = [0.0] * dim
    sum_w = 0.0
    for (_, vec, _), w in zip(members, weights):
        sum_w += w
        for i in range(dim):
            c = vec.components[i] if i < len(vec.components) else 0.0
            acc[i] += w * float(c)
    if sum_w <= 0:
        sum_w = 1.0
    agg = tuple(acc[i] / sum_w for i in range(dim))
    agg_vec = engine._normalize_unit(agg)
    result = engine.fluid_cast(agg_vec, intent)
    adj = float(result.verdict.resonance.adjusted)
    vt = result.verdict.verdict_type
    new_streaks: dict[str, int] = {}
    if vt == VerdictType.COHERENT and adj >= float(consensus_threshold):
        status = "COHERENT"
        for sid, _, streak in members:
            new_streaks[sid] = int(streak) + 1
    elif vt == VerdictType.INCOHERENT:
        status = "DECOHERENT"
        for sid, _, _ in members:
            new_streaks[sid] = 0
    else:
        status = "STRAINED"
        for sid, _, streak in members:
            new_streaks[sid] = int(streak)
    return result, agg_vec, status, new_streaks


def chained_cast(
    engine,
    aspects: frozenset[AspectID],
    intent: Intent,
    channel: ChannelState | None,
    *,
    force: bool = False,
):
    from vermyth.engine.resonance import ChannelDecoherentError

    if channel is not None and channel.status == ChannelStatus.DECOHERENT and not force:
        raise ChannelDecoherentError(
            f"channel {channel.branch_id} is DECOHERENT; sync required"
        )

    sigil = engine.composition_engine.compose(aspects)
    iv = engine._build_intent_vector(intent)

    if channel is not None and channel.constraint_vector is not None:
        dim = max(len(iv.vector.components), len(channel.constraint_vector.components))
        blended: list[float] = []
        for i in range(dim):
            a = iv.vector.components[i] if i < len(iv.vector.components) else 0.0
            b = (
                channel.constraint_vector.components[i]
                if i < len(channel.constraint_vector.components)
                else 0.0
            )
            blended.append(0.8 * float(a) + 0.2 * float(b))
        blended_vec = engine._normalize_unit(tuple(blended))
        iv = IntentVector.model_construct(
            vector=blended_vec,
            projection_method=iv.projection_method,
            constraint_component=iv.constraint_component,
            semantic_component=iv.semantic_component,
            confidence=iv.confidence,
        )

    verdict = engine._evaluate_with_intent_vector(sigil, intent, iv)
    result = CastResult(intent=intent, sigil=sigil, verdict=verdict)

    if channel is None:
        branch_id = str(ULID())
        cast_count = 0
        cumulative = 0.0
        streak = 0
    else:
        branch_id = channel.branch_id
        cast_count = int(channel.cast_count)
        cumulative = float(channel.cumulative_resonance)
        streak = int(channel.coherence_streak)

    cast_count += 1
    cumulative += float(result.verdict.resonance.adjusted)
    mean = cumulative / float(cast_count) if cast_count else 0.0
    if result.verdict.verdict_type == VerdictType.COHERENT:
        streak += 1
    else:
        streak = 0

    if mean >= 0.65:
        status = ChannelStatus.COHERENT
    elif mean >= 0.40:
        status = ChannelStatus.STRAINED
    else:
        status = ChannelStatus.DECOHERENT
    updated = ChannelState(
        branch_id=branch_id,
        cast_count=cast_count,
        cumulative_resonance=cumulative,
        mean_resonance=mean,
        coherence_streak=streak,
        last_verdict_type=result.verdict.verdict_type,
        status=status,
        last_cast_id=result.cast_id,
        constraint_vector=sigil.semantic_vector,
    )
    return result, updated

