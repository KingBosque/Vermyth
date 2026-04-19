from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from ulid import ULID

from vermyth.arcane.presentation.transcript import arcane_transcript_for_cast_result
from vermyth.mcp.geometric import decode_packet, encode_response, validate_proof
from vermyth.registry import AspectRegistry
from vermyth.schema import (
    CastProvenance,
    CastResult,
    ChannelState,
    ChannelStatus,
    CrystallizedSigil,
    DivergenceReport,
    GeometricPacket,
    GlyphSeed,
    Intent,
    Lineage,
    SemanticVector,
    VerdictType,
)

if TYPE_CHECKING:
    from vermyth.mcp.tools.facade import VermythTools

TOOLS = [{'name': 'cast',
  'description': 'Compose aspects into a Sigil and evaluate against a declared Intent. Returns a '
                 'fully typed CastResult.',
  'inputSchema': {'type': 'object',
                  'properties': {'aspects': {'type': 'array',
                                             'items': {'type': 'string'},
                                             'description': 'List of AspectID names. Valid values: '
                                                            'VOID, FORM, MOTION, MIND, DECAY, '
                                                            'LIGHT. Between 1 and 3 inclusive.'},
                                 'objective': {'type': 'string',
                                               'description': 'What this casting should '
                                                              'accomplish. Max 500 characters.'},
                                 'scope': {'type': 'string',
                                           'description': 'The bounded domain this casting applies '
                                                          'to. Max 200 characters.'},
                                 'reversibility': {'type': 'string',
                                                   'enum': ['REVERSIBLE',
                                                            'PARTIAL',
                                                            'IRREVERSIBLE']},
                                 'side_effect_tolerance': {'type': 'string',
                                                           'enum': ['NONE',
                                                                    'LOW',
                                                                    'MEDIUM',
                                                                    'HIGH']},
                                 'parent_cast_id': {'type': 'string',
                                                    'description': 'Optional parent cast_id to '
                                                                   'chain this cast as a child in '
                                                                   'the lineage tree.'},
                                 'branch_id': {'type': 'string',
                                               'description': 'Optional explicit lineage branch '
                                                              'id; inherits from parent when '
                                                              'omitted.'},
                                 'chained': {'type': 'boolean',
                                             'description': 'If true, apply channel continuity '
                                                            'constraints using branch_id as the '
                                                            'channel key.'},
                                 'force': {'type': 'boolean',
                                           'description': 'If true, allow chained casts even when '
                                                          'the channel is DECOHERENT.'},
                                 'include_arcane_transcript': {'type': 'boolean',
                                                               'description': 'If true, include '
                                                                              'presentation-only '
                                                                              'arcane_transcript '
                                                                              '(derived from this '
                                                                              'cast result; no '
                                                                              'default wire '
                                                                              'change).'}},
                  'required': ['aspects',
                               'objective',
                               'scope',
                               'reversibility',
                               'side_effect_tolerance']}},
 {'name': 'fluid_cast',
  'description': 'Interpolate a FluidSigil from a raw semantic vector and evaluate against a '
                 'declared Intent.',
  'inputSchema': {'type': 'object',
                  'properties': {'vector': {'type': 'array',
                                            'items': {'type': 'number'},
                                            'description': 'Six or more floats. First six '
                                                           'correspond to VOID, FORM, MOTION, '
                                                           'MIND, DECAY, LIGHT. Each in range -1.0 '
                                                           'to 1.0.'},
                                 'objective': {'type': 'string'},
                                 'scope': {'type': 'string'},
                                 'reversibility': {'type': 'string',
                                                   'enum': ['REVERSIBLE',
                                                            'PARTIAL',
                                                            'IRREVERSIBLE']},
                                 'side_effect_tolerance': {'type': 'string',
                                                           'enum': ['NONE',
                                                                    'LOW',
                                                                    'MEDIUM',
                                                                    'HIGH']},
                                 'parent_cast_id': {'type': 'string'},
                                 'branch_id': {'type': 'string'},
                                 'include_arcane_transcript': {'type': 'boolean',
                                                               'description': 'If true, include '
                                                                              'presentation-only '
                                                                              'arcane_transcript.'}},
                  'required': ['vector',
                               'objective',
                               'scope',
                               'reversibility',
                               'side_effect_tolerance']}},
 {'name': 'auto_cast',
  'description': 'Self-healing fluid cast: iteratively refine vector until coherent or max depth.',
  'inputSchema': {'type': 'object',
                  'properties': {'vector': {'type': 'array', 'items': {'type': 'number'}},
                                 'objective': {'type': 'string'},
                                 'scope': {'type': 'string'},
                                 'reversibility': {'type': 'string'},
                                 'side_effect_tolerance': {'type': 'string'},
                                 'max_depth': {'type': 'integer'},
                                 'target_resonance': {'type': 'number'},
                                 'blend_alpha': {'type': 'number'},
                                 'include_diagnostics': {'type': 'boolean'},
                                 'include_arcane_transcript': {'type': 'boolean',
                                                               'description': 'If true, include '
                                                                              'presentation-only '
                                                                              'arcane_transcript '
                                                                              'for the final cast '
                                                                              'in the chain.'}},
                  'required': ['vector',
                               'objective',
                               'scope',
                               'reversibility',
                               'side_effect_tolerance']}},
 {'name': 'geometric_cast',
  'description': 'Cast using a packed geometric payload (vector-first).',
  'inputSchema': {'type': 'object',
                  'properties': {'payload': {'type': 'array', 'items': {'type': 'number'}},
                                 'version': {'type': 'integer'},
                                 'branch_id': {'type': 'string'},
                                 'force': {'type': 'boolean'}},
                  'required': ['payload']}}]



def cast_result_to_dict(tools: "VermythTools", result: CastResult) -> dict[str, Any]:
    warnings: list[str] = []
    lineage_dict: dict[str, Any] | None = None
    if result.lineage is not None:
        lineage_dict = {
            "parent_cast_id": result.lineage.parent_cast_id,
            "depth": result.lineage.depth,
            "branch_id": result.lineage.branch_id,
        }
        if result.lineage.divergence_vector is not None:
            lineage_dict["divergence_vector"] = [
                round(c, 6) for c in result.lineage.divergence_vector.components
            ]
        report: DivergenceReport | None = tools._divergence_cache.get(result.cast_id)
        if report is None:
            try:
                report = tools._grimoire.read_divergence_report(result.cast_id)
            except Exception:
                report = None
        if report is not None:
            lineage_dict["divergence"] = {
                "l2_magnitude": round(float(report.l2_magnitude), 6),
                "cosine_distance": round(float(report.cosine_distance), 6),
                "status": report.status.name,
            }
            if report.status.name != "STABLE":
                warnings.append(
                    f"{report.status.name}: parent-child semantic drift exceeded thresholds"
                )
    provenance_dict: dict[str, Any] | None = None
    if result.provenance is not None:
        provenance_dict = {
            "source": result.provenance.source,
            "crystallized_sigil_name": result.provenance.crystallized_sigil_name,
            "generation": result.provenance.generation,
            "narrative_coherence": result.provenance.narrative_coherence,
            "causal_root_cast_id": result.provenance.causal_root_cast_id,
        }
    out = {
        "cast_id": result.cast_id,
        "timestamp": result.timestamp.isoformat(),
        "verdict": result.verdict.verdict_type.name,
        "resonance": round(result.verdict.resonance.adjusted, 4),
        "effect_class": result.sigil.effect_class.name,
        "sigil_name": result.sigil.name,
        "sigil_aspects": sorted([a.name for a in result.sigil.aspects]),
        "effect_description": result.verdict.effect_description,
        "casting_note": result.verdict.casting_note,
        "incoherence_reason": result.verdict.incoherence_reason,
        "proof": result.verdict.resonance.proof,
        "projection_method": result.verdict.intent_vector.projection_method.name,
        "intent_confidence": round(result.verdict.intent_vector.confidence, 4),
        "semantic_vector": [round(c, 6) for c in result.sigil.semantic_vector.components],
        "intent_vector": [
            round(c, 6) for c in result.verdict.intent_vector.vector.components
        ],
        "lineage": lineage_dict,
        "glyph_seed_id": result.glyph_seed_id,
        "provenance": provenance_dict,
    }
    if warnings:
        out["warnings"] = warnings
    return out


def _attach_arcane_transcript_if_requested(
    out: dict[str, Any],
    result: CastResult,
    include_arcane_transcript: bool,
) -> None:
    if include_arcane_transcript:
        out["arcane_transcript"] = arcane_transcript_for_cast_result(result)


def tool_cast(
    tools: "VermythTools",
    aspects: list[str],
    intent: dict[str, Any],
    *,
    parent_cast_id: str | None = None,
    branch_id: str | None = None,
    chained: bool = False,
    force: bool = False,
    include_arcane_transcript: bool = False,
) -> dict[str, Any]:
    try:
        registry = AspectRegistry.get()
        resolved = []
        for name in aspects:
            try:
                resolved.append(registry.resolve(name))
            except KeyError as exc:
                raise ValueError(f"Unknown aspect: {name}") from exc
        aspects_set = frozenset(resolved)
        intent_obj = Intent(**intent)
        if chained:
            chan: ChannelState | None = None
            if branch_id is not None:
                try:
                    chan = tools._grimoire.read_channel_state(str(branch_id))
                except KeyError:
                    chan = None
            result_obj, new_state = tools._engine.chained_cast(
                aspects_set, intent_obj, chan, force=bool(force)
            )
            if branch_id is not None and chan is None:
                new_state = ChannelState.model_construct(
                    branch_id=str(branch_id),
                    cast_count=new_state.cast_count,
                    cumulative_resonance=new_state.cumulative_resonance,
                    mean_resonance=new_state.mean_resonance,
                    coherence_streak=new_state.coherence_streak,
                    last_verdict_type=new_state.last_verdict_type,
                    status=new_state.status,
                    last_cast_id=new_state.last_cast_id,
                    constraint_vector=new_state.constraint_vector,
                    updated_at=new_state.updated_at,
                )
            tools._grimoire.write_channel_state(new_state)
            result = CastResult.model_construct(
                cast_id=result_obj.cast_id,
                timestamp=result_obj.timestamp,
                intent=result_obj.intent,
                sigil=result_obj.sigil,
                verdict=result_obj.verdict,
                immutable=True,
                lineage=result_obj.lineage,
                glyph_seed_id=result_obj.glyph_seed_id,
                provenance=CastProvenance(source="base"),
            )
        else:
            crystal = tools._grimoire.crystallized_for_aspects(aspects_set)
            if crystal is not None:
                verdict = tools._engine.evaluate(crystal.sigil, intent_obj)
                provenance_obj = CastProvenance(
                    source="crystallized",
                    crystallized_sigil_name=crystal.name,
                    generation=crystal.generation,
                )
                result = CastResult.model_construct(
                    cast_id=str(ULID()),
                    timestamp=datetime.now(timezone.utc),
                    intent=intent_obj,
                    sigil=crystal.sigil,
                    verdict=verdict,
                    immutable=True,
                    lineage=None,
                    glyph_seed_id=None,
                    provenance=provenance_obj,
                )
            else:
                provenance_obj = CastProvenance(source="base")
                base = tools._engine.cast(aspects_set, intent_obj)
                result = CastResult.model_construct(
                    cast_id=base.cast_id,
                    timestamp=base.timestamp,
                    intent=base.intent,
                    sigil=base.sigil,
                    verdict=base.verdict,
                    immutable=True,
                    lineage=base.lineage,
                    glyph_seed_id=base.glyph_seed_id,
                    provenance=provenance_obj,
                )
        if parent_cast_id is not None:
            parent = tools._grimoire.read(parent_cast_id)
            pc = parent.sigil.semantic_vector.components
            cc = result.sigil.semantic_vector.components
            dim = max(len(cc), len(pc))
            diff = tuple(
                float(cc[i] if i < len(cc) else 0.0)
                - float(pc[i] if i < len(pc) else 0.0)
                for i in range(dim)
            )
            div_vec = SemanticVector(components=diff)
            depth = parent.lineage.depth + 1 if parent.lineage is not None else 1
            if branch_id is not None:
                bid_for_lineage = branch_id
            elif parent.lineage is not None:
                bid_for_lineage = parent.lineage.branch_id
            else:
                bid_for_lineage = None
            lin_payload: dict[str, Any] = {
                "parent_cast_id": parent_cast_id,
                "depth": depth,
                "divergence_vector": div_vec,
            }
            if bid_for_lineage is not None:
                lin_payload["branch_id"] = bid_for_lineage
            lineage_obj = Lineage.model_validate(lin_payload)
            result = CastResult.model_construct(
                cast_id=result.cast_id,
                timestamp=result.timestamp,
                intent=result.intent,
                sigil=result.sigil,
                verdict=result.verdict,
                immutable=True,
                lineage=lineage_obj,
                glyph_seed_id=result.glyph_seed_id,
                provenance=result.provenance,
            )
            report = DivergenceReport.classify(
                cast_id=result.cast_id,
                parent_cast_id=parent_cast_id,
                parent_vector=parent.sigil.semantic_vector,
                child_vector=result.sigil.semantic_vector,
                thresholds=tools._active_thresholds,
            )
            tools._grimoire.write_divergence_report(report)
            tools._divergence_cache[result.cast_id] = report
        seeds = tools._grimoire.query_seeds(aspect_pattern=aspects_set, crystallized=None)
        seed_by_pattern = {s.aspect_pattern: s for s in seeds}
        seed = tools._engine.accumulate(result, seeds)
        if seed is not None:
            prev = seed_by_pattern.get(seed.aspect_pattern)
            if prev is not None:
                seed = GlyphSeed.model_construct(
                    seed_id=prev.seed_id,
                    aspect_pattern=seed.aspect_pattern,
                    observed_count=seed.observed_count,
                    mean_resonance=seed.mean_resonance,
                    coherence_rate=seed.coherence_rate,
                    candidate_effect_class=seed.candidate_effect_class,
                    crystallized=seed.crystallized,
                    generation=getattr(seed, "generation", getattr(prev, "generation", 1) or 1),
                    semantic_vector=seed.semantic_vector,
                )
            tools._grimoire.write_seed(seed)
        out = cast_result_to_dict(tools, result)
        if seed is not None:
            sig = tools._engine.crystallize(seed)
            if sig is not None:
                out["crystallized_sigil"] = {
                    "name": sig.name,
                    "effect_class": sig.effect_class.name,
                    "resonance_ceiling": sig.resonance_ceiling,
                }
                crystal_row = CrystallizedSigil(
                    name=sig.name,
                    sigil=sig,
                    source_seed_id=seed.seed_id,
                    crystallized_at=datetime.now(timezone.utc),
                    generation=int(getattr(seed, "generation", 1) or 1),
                )
                tools._grimoire.write_crystallized_sigil(crystal_row)

                reset = GlyphSeed.model_construct(
                    seed_id=seed.seed_id,
                    aspect_pattern=seed.aspect_pattern,
                    observed_count=0,
                    mean_resonance=0.0,
                    coherence_rate=0.0,
                    candidate_effect_class=seed.candidate_effect_class,
                    crystallized=False,
                    generation=int(getattr(seed, "generation", 1) or 1) + 1,
                    semantic_vector=seed.semantic_vector,
                )
                tools._grimoire.write_seed(reset)
        tools._grimoire.write(result)
        _attach_arcane_transcript_if_requested(out, result, include_arcane_transcript)
        return out
    except ValueError:
        raise
    except KeyError:
        raise
    except Exception as exc:
        if (
            type(exc).__name__ == "ValidationError"
            and type(exc).__module__.startswith("pydantic")
        ):
            raise
        raise RuntimeError(f"cast failed: {exc}") from exc


def tool_fluid_cast(
    tools: "VermythTools",
    vector: list[float],
    intent: dict[str, Any],
    *,
    parent_cast_id: str | None = None,
    branch_id: str | None = None,
    include_arcane_transcript: bool = False,
) -> dict[str, Any]:
    try:
        if len(vector) < 6:
            raise ValueError("vector must contain at least 6 floats")
        comps = tuple(float(x) for x in vector)
        for x in comps[:6]:
            if x < -1.0 or x > 1.0:
                raise ValueError("vector components must be between -1.0 and 1.0")
        vec = SemanticVector(components=comps)
        intent_obj = Intent(**intent)

        base = tools._engine.fluid_cast(vec, intent_obj)
        result = base

        if parent_cast_id is not None:
            parent = tools._grimoire.read(parent_cast_id)
            pc = parent.sigil.semantic_vector.components
            cc = result.sigil.semantic_vector.components
            dim = max(len(cc), len(pc))
            diff = tuple(
                float(cc[i] if i < len(cc) else 0.0)
                - float(pc[i] if i < len(pc) else 0.0)
                for i in range(dim)
            )
            div_vec = SemanticVector(components=diff)
            depth = parent.lineage.depth + 1 if parent.lineage is not None else 1
            if branch_id is not None:
                bid_for_lineage = branch_id
            elif parent.lineage is not None:
                bid_for_lineage = parent.lineage.branch_id
            else:
                bid_for_lineage = None
            lin_payload: dict[str, Any] = {
                "parent_cast_id": parent_cast_id,
                "depth": depth,
                "divergence_vector": div_vec,
            }
            if bid_for_lineage is not None:
                lin_payload["branch_id"] = bid_for_lineage
            lineage_obj = Lineage.model_validate(lin_payload)
            result = CastResult.model_construct(
                cast_id=result.cast_id,
                timestamp=result.timestamp,
                intent=result.intent,
                sigil=result.sigil,
                verdict=result.verdict,
                immutable=True,
                lineage=lineage_obj,
                glyph_seed_id=result.glyph_seed_id,
                provenance=result.provenance,
            )
            report = DivergenceReport.classify(
                cast_id=result.cast_id,
                parent_cast_id=parent_cast_id,
                parent_vector=parent.sigil.semantic_vector,
                child_vector=result.sigil.semantic_vector,
                thresholds=tools._active_thresholds,
            )
            tools._grimoire.write_divergence_report(report)
            tools._divergence_cache[result.cast_id] = report

        seeds = tools._grimoire.query_seeds(
            aspect_pattern=frozenset(result.sigil.aspects), crystallized=None
        )
        seed_by_pattern = {s.aspect_pattern: s for s in seeds}
        seed = tools._engine.accumulate(result, seeds)
        if seed is not None:
            prev = seed_by_pattern.get(seed.aspect_pattern)
            if prev is not None:
                seed = GlyphSeed.model_construct(
                    seed_id=prev.seed_id,
                    aspect_pattern=seed.aspect_pattern,
                    observed_count=seed.observed_count,
                    mean_resonance=seed.mean_resonance,
                    coherence_rate=seed.coherence_rate,
                    candidate_effect_class=seed.candidate_effect_class,
                    crystallized=seed.crystallized,
                    generation=getattr(
                        seed, "generation", getattr(prev, "generation", 1) or 1
                    ),
                    semantic_vector=seed.semantic_vector,
                )
            tools._grimoire.write_seed(seed)

        out = cast_result_to_dict(tools, result)
        if seed is not None:
            sig = tools._engine.crystallize(seed)
            if sig is not None:
                out["crystallized_sigil"] = {
                    "name": sig.name,
                    "effect_class": sig.effect_class.name,
                    "resonance_ceiling": sig.resonance_ceiling,
                }
                crystal_row = CrystallizedSigil(
                    name=sig.name,
                    sigil=sig,
                    source_seed_id=seed.seed_id,
                    crystallized_at=datetime.now(timezone.utc),
                    generation=int(getattr(seed, "generation", 1) or 1),
                )
                tools._grimoire.write_crystallized_sigil(crystal_row)

                reset = GlyphSeed.model_construct(
                    seed_id=seed.seed_id,
                    aspect_pattern=seed.aspect_pattern,
                    observed_count=0,
                    mean_resonance=0.0,
                    coherence_rate=0.0,
                    candidate_effect_class=seed.candidate_effect_class,
                    crystallized=False,
                    generation=int(getattr(seed, "generation", 1) or 1) + 1,
                    semantic_vector=seed.semantic_vector,
                )
                tools._grimoire.write_seed(reset)

        tools._grimoire.write(result)
        _attach_arcane_transcript_if_requested(out, result, include_arcane_transcript)
        return out
    except ValueError:
        raise
    except KeyError:
        raise
    except Exception as exc:
        if (
            type(exc).__name__ == "ValidationError"
            and type(exc).__module__.startswith("pydantic")
        ):
            raise
        raise RuntimeError(f"fluid_cast failed: {exc}") from exc


def _write_fluid_result_to_grimoire(tools: "VermythTools", result: CastResult) -> None:
    if result.lineage is not None:
        parent = tools._grimoire.read(result.lineage.parent_cast_id)
        report = DivergenceReport.classify(
            cast_id=result.cast_id,
            parent_cast_id=result.lineage.parent_cast_id,
            parent_vector=parent.sigil.semantic_vector,
            child_vector=result.sigil.semantic_vector,
            thresholds=tools._active_thresholds,
        )
        tools._grimoire.write_divergence_report(report)
        tools._divergence_cache[result.cast_id] = report

    seeds = tools._grimoire.query_seeds(
        aspect_pattern=frozenset(result.sigil.aspects), crystallized=None
    )
    seed_by_pattern = {s.aspect_pattern: s for s in seeds}
    seed = tools._engine.accumulate(result, seeds)
    if seed is not None:
        prev = seed_by_pattern.get(seed.aspect_pattern)
        if prev is not None:
            seed = GlyphSeed.model_construct(
                seed_id=prev.seed_id,
                aspect_pattern=seed.aspect_pattern,
                observed_count=seed.observed_count,
                mean_resonance=seed.mean_resonance,
                coherence_rate=seed.coherence_rate,
                candidate_effect_class=seed.candidate_effect_class,
                crystallized=seed.crystallized,
                generation=getattr(seed, "generation", getattr(prev, "generation", 1) or 1),
                semantic_vector=seed.semantic_vector,
            )
        tools._grimoire.write_seed(seed)

        sig = tools._engine.crystallize(seed)
        if sig is not None:
            crystal_row = CrystallizedSigil(
                name=sig.name,
                sigil=sig,
                source_seed_id=seed.seed_id,
                crystallized_at=datetime.now(timezone.utc),
                generation=int(getattr(seed, "generation", 1) or 1),
            )
            tools._grimoire.write_crystallized_sigil(crystal_row)

            reset = GlyphSeed.model_construct(
                seed_id=seed.seed_id,
                aspect_pattern=seed.aspect_pattern,
                observed_count=0,
                mean_resonance=0.0,
                coherence_rate=0.0,
                candidate_effect_class=seed.candidate_effect_class,
                crystallized=False,
                generation=int(getattr(seed, "generation", 1) or 1) + 1,
                semantic_vector=seed.semantic_vector,
            )
            tools._grimoire.write_seed(reset)

    tools._grimoire.write(result)


def tool_auto_cast(
    tools: "VermythTools",
    vector: list[float],
    intent: dict[str, Any],
    *,
    max_depth: int = 5,
    target_resonance: float = 0.75,
    blend_alpha: float = 0.35,
    include_diagnostics: bool = False,
    include_arcane_transcript: bool = False,
) -> dict[str, Any]:
    if len(vector) < 6:
        raise ValueError("vector must contain at least 6 floats")
    comps = tuple(float(x) for x in vector)
    for x in comps[:6]:
        if x < -1.0 or x > 1.0:
            raise ValueError("vector components must be between -1.0 and 1.0")
    vec = SemanticVector(components=comps)
    intent_obj = Intent(**intent)
    if include_diagnostics:
        _final, chain, diagnostics = tools._engine.auto_cast(
            vec,
            intent_obj,
            max_depth=int(max_depth),
            target_resonance=float(target_resonance),
            blend_alpha=float(blend_alpha),
            with_diagnostics=True,
        )
    else:
        _final, chain = tools._engine.auto_cast(
            vec,
            intent_obj,
            max_depth=int(max_depth),
            target_resonance=float(target_resonance),
            blend_alpha=float(blend_alpha),
        )
        diagnostics = None
    chain_dicts: list[dict[str, Any]] = []
    for r in chain:
        _write_fluid_result_to_grimoire(tools, r)
        chain_dicts.append(cast_result_to_dict(tools, r))
    out = cast_result_to_dict(tools, chain[-1])
    out["auto_cast_chain"] = chain_dicts
    out["auto_cast_depth"] = len(chain)
    if diagnostics is not None:
        out["diagnostics"] = diagnostics.model_dump(mode="json")
    _attach_arcane_transcript_if_requested(out, chain[-1], include_arcane_transcript)
    return out


def tool_geometric_cast(
    tools: "VermythTools",
    payload: list[float],
    *,
    version: int = 1,
    branch_id: str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    if not isinstance(payload, list):
        raise ValueError("payload must be a list of floats")
    packet = GeometricPacket(payload=tuple(float(x) for x in payload), version=int(version))
    if not validate_proof(packet):
        raise ValueError("invalid geometric packet proof")

    vec, intent, _lineage = decode_packet(packet)
    channel: ChannelState | None = None
    if branch_id is not None:
        try:
            channel = tools._grimoire.read_channel_state(str(branch_id))
        except KeyError:
            channel = None
    if channel is not None and channel.status == ChannelStatus.DECOHERENT and not force:
        raise ValueError("channel is DECOHERENT; sync required")

    blended_vec = vec
    if channel is not None and channel.constraint_vector is not None:
        dim = max(len(vec.components), len(channel.constraint_vector.components))
        blended: list[float] = []
        for i in range(dim):
            a = vec.components[i] if i < len(vec.components) else 0.0
            b = (
                channel.constraint_vector.components[i]
                if i < len(channel.constraint_vector.components)
                else 0.0
            )
            blended.append(float(a) * 0.80 + float(b) * 0.20)
        s = sum(x * x for x in blended)
        n = s**0.5
        if n > 0:
            blended = [x / n for x in blended]
        blended_vec = SemanticVector(components=tuple(blended))

    result_obj = tools._engine.fluid_cast(blended_vec, intent)
    tools._grimoire.write(result_obj)
    channel_delta: SemanticVector | None = None
    if branch_id is not None:
        if channel is None:
            channel = ChannelState(
                branch_id=str(branch_id),
                cast_count=0,
                cumulative_resonance=0.0,
                mean_resonance=0.0,
                coherence_streak=0,
                last_verdict_type=VerdictType.PARTIAL,
                status=ChannelStatus.COHERENT,
                last_cast_id="",
                constraint_vector=None,
            )
        new_count = int(channel.cast_count) + 1
        new_cum = float(channel.cumulative_resonance) + float(
            result_obj.verdict.resonance.adjusted
        )
        new_mean = new_cum / float(new_count)
        if new_mean >= 0.65:
            new_status = ChannelStatus.COHERENT
        elif new_mean >= 0.40:
            new_status = ChannelStatus.STRAINED
        else:
            new_status = ChannelStatus.DECOHERENT
        new_streak = (
            int(channel.coherence_streak) + 1
            if result_obj.verdict.verdict_type == VerdictType.COHERENT
            else 0
        )
        updated = ChannelState(
            branch_id=str(branch_id),
            cast_count=new_count,
            cumulative_resonance=new_cum,
            mean_resonance=new_mean,
            coherence_streak=new_streak,
            last_verdict_type=result_obj.verdict.verdict_type,
            status=new_status,
            last_cast_id=result_obj.cast_id,
            constraint_vector=result_obj.sigil.semantic_vector,
        )
        tools._grimoire.write_channel_state(updated)
        channel_delta = updated.constraint_vector

    resp = encode_response(
        verdict_vector=result_obj.sigil.semantic_vector,
        resonance=float(result_obj.verdict.resonance.adjusted),
        channel_delta=channel_delta,
    )
    return {
        "verdict_vector": [round(c, 6) for c in resp.verdict_vector.components],
        "resonance": round(float(resp.resonance), 6),
        "channel_delta": (
            [round(c, 6) for c in resp.channel_delta.components]
            if resp.channel_delta is not None
            else None
        ),
        "proof_hash": float(resp.proof_hash),
        "cast_id": result_obj.cast_id,
    }


def dispatch_cast(tools: "VermythTools", arguments: dict[str, Any]) -> dict[str, Any]:
    return tool_cast(
        tools,
        aspects=arguments.get("aspects", []),
        intent={
            "objective": arguments.get("objective", ""),
            "scope": arguments.get("scope", ""),
            "reversibility": arguments.get("reversibility", "PARTIAL"),
            "side_effect_tolerance": arguments.get("side_effect_tolerance", "MEDIUM"),
        },
        parent_cast_id=arguments.get("parent_cast_id"),
        branch_id=arguments.get("branch_id"),
        chained=bool(arguments.get("chained", False)),
        force=bool(arguments.get("force", False)),
        include_arcane_transcript=bool(arguments.get("include_arcane_transcript", False)),
    )


def dispatch_fluid_cast(tools: "VermythTools", arguments: dict[str, Any]) -> dict[str, Any]:
    return tool_fluid_cast(
        tools,
        vector=arguments.get("vector", []),
        intent={
            "objective": arguments.get("objective", ""),
            "scope": arguments.get("scope", ""),
            "reversibility": arguments.get("reversibility", "PARTIAL"),
            "side_effect_tolerance": arguments.get("side_effect_tolerance", "MEDIUM"),
        },
        parent_cast_id=arguments.get("parent_cast_id"),
        branch_id=arguments.get("branch_id"),
        include_arcane_transcript=bool(arguments.get("include_arcane_transcript", False)),
    )


def dispatch_auto_cast(tools: "VermythTools", arguments: dict[str, Any]) -> dict[str, Any]:
    return tool_auto_cast(
        tools,
        vector=arguments.get("vector", []),
        intent={
            "objective": arguments.get("objective", ""),
            "scope": arguments.get("scope", ""),
            "reversibility": arguments.get("reversibility", "PARTIAL"),
            "side_effect_tolerance": arguments.get("side_effect_tolerance", "MEDIUM"),
        },
        max_depth=int(arguments.get("max_depth", 5)),
        target_resonance=float(arguments.get("target_resonance", 0.75)),
        blend_alpha=float(arguments.get("blend_alpha", 0.35)),
        include_diagnostics=bool(arguments.get("include_diagnostics", False)),
        include_arcane_transcript=bool(arguments.get("include_arcane_transcript", False)),
    )


def dispatch_geometric_cast(tools: "VermythTools", arguments: dict[str, Any]) -> dict[str, Any]:
    return tool_geometric_cast(
        tools,
        payload=arguments.get("payload", []),
        version=int(arguments.get("version", 1)),
        branch_id=arguments.get("branch_id"),
        force=bool(arguments.get("force", False)),
    )


DISPATCH = {
    "cast": dispatch_cast,
    "fluid_cast": dispatch_fluid_cast,
    "auto_cast": dispatch_auto_cast,
    "geometric_cast": dispatch_geometric_cast,
}

