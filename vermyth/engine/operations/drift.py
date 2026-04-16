from __future__ import annotations

from vermyth.schema import ChannelState, ChannelStatus, GlyphSeed, SemanticVector


def sync_channel(engine, channel: ChannelState, seeds: list[GlyphSeed]) -> ChannelState:
    anchor_vec: SemanticVector | None = None
    best: tuple[float, GlyphSeed] | None = None
    for seed in seeds:
        score = float(getattr(seed, "mean_resonance", 0.0) or 0.0)
        if best is None or score > best[0]:
            best = (score, seed)
    if best is not None:
        sigil = engine.crystallize(best[1])
        if sigil is not None:
            anchor_vec = sigil.semantic_vector
    if anchor_vec is None:
        anchor_vec = channel.constraint_vector

    return ChannelState(
        branch_id=channel.branch_id,
        cast_count=int(channel.cast_count),
        cumulative_resonance=float(channel.cumulative_resonance),
        mean_resonance=float(channel.mean_resonance),
        coherence_streak=0,
        last_verdict_type=channel.last_verdict_type,
        status=ChannelStatus.COHERENT,
        last_cast_id=channel.last_cast_id,
        constraint_vector=anchor_vec,
    )

