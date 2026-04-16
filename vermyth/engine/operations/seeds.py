from __future__ import annotations

from typing import Optional

from vermyth.schema import CastResult, GlyphSeed, Sigil, VerdictType


def accumulate(engine, result: CastResult, seeds: list[GlyphSeed]) -> Optional[GlyphSeed]:
    aspects = result.sigil.aspects
    matching: Optional[GlyphSeed] = None
    for seed in seeds:
        if seed.aspect_pattern == aspects:
            matching = seed
            break
    vt = result.verdict.verdict_type
    if vt == VerdictType.INCOHERENT and matching is None:
        return None
    adj = float(result.verdict.resonance.adjusted)
    coh_increment = 1.0 if vt == VerdictType.COHERENT else 0.0

    if matching is not None:
        n = matching.observed_count + 1
        new_mean = (matching.mean_resonance * matching.observed_count + adj) / n
        new_coh = (matching.coherence_rate * matching.observed_count + coh_increment) / n
        cand = (
            result.sigil.effect_class
            if matching.candidate_effect_class is None
            else matching.candidate_effect_class
        )
        return GlyphSeed(
            aspect_pattern=matching.aspect_pattern,
            observed_count=n,
            mean_resonance=new_mean,
            coherence_rate=new_coh,
            candidate_effect_class=cand,
            crystallized=False,
            generation=matching.generation,
        )

    return GlyphSeed(
        aspect_pattern=aspects,
        observed_count=1,
        mean_resonance=adj,
        coherence_rate=coh_increment,
        candidate_effect_class=result.sigil.effect_class,
        crystallized=False,
        generation=1,
    )


def crystallize(engine, seed: GlyphSeed) -> Optional[Sigil]:
    gen = int(getattr(seed, "generation", 1) or 1)
    req_count = min(50, 10 + 5 * (gen - 1))
    req_mean = min(0.95, 0.70 + 0.05 * (gen - 1))
    req_coh = min(0.90, 0.65 + 0.05 * (gen - 1))
    if seed.crystallized:
        return None
    if (
        seed.observed_count < req_count
        or seed.mean_resonance < req_mean
        or seed.coherence_rate < req_coh
    ):
        return None
    if seed.candidate_effect_class is None:
        return None
    base = engine.composition_engine.compose(seed.aspect_pattern)
    name = f"Glyph:{base.name}"
    ceiling = round(float(seed.mean_resonance), 2)
    return Sigil(
        name=name,
        aspects=seed.aspect_pattern,
        effect_class=seed.candidate_effect_class,
        resonance_ceiling=ceiling,
        contradiction_severity=base.contradiction_severity,
    )

