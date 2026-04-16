from __future__ import annotations

from typing import TYPE_CHECKING, Any

from vermyth.registry import AspectRegistry
from vermyth.schema import GossipPayload, Intent, SemanticVector, SwarmState, SwarmStatus

if TYPE_CHECKING:
    from vermyth.mcp.tools.facade import VermythTools

TOOLS = [{'name': 'gossip_sync',
  'description': 'Apply a signed federation gossip payload (seeds and crystallized sigils).',
  'inputSchema': {'type': 'object',
                  'properties': {'peer_id': {'type': 'string'},
                                 'key_id': {'type': 'string'},
                                 'seeds': {'type': 'array'},
                                 'crystallized': {'type': 'array'},
                                 'proof': {'type': 'string'}},
                  'required': ['peer_id', 'key_id', 'proof']}},
 {'name': 'swarm_cast',
  'description': 'Submit a vector to a swarm; aggregate weighted peers and evaluate consensus.',
  'inputSchema': {'type': 'object',
                  'properties': {'swarm_id': {'type': 'string'},
                                 'session_id': {'type': 'string'},
                                 'vector': {'type': 'array', 'items': {'type': 'number'}},
                                 'objective': {'type': 'string'},
                                 'scope': {'type': 'string'},
                                 'reversibility': {'type': 'string'},
                                 'side_effect_tolerance': {'type': 'string'},
                                 'consensus_threshold': {'type': 'number'}},
                  'required': ['swarm_id',
                               'session_id',
                               'vector',
                               'objective',
                               'scope',
                               'reversibility',
                               'side_effect_tolerance']}},
 {'name': 'swarm_join',
  'description': 'Join or create a swarm channel for multi-agent consensus casting.',
  'inputSchema': {'type': 'object',
                  'properties': {'swarm_id': {'type': 'string'},
                                 'session_id': {'type': 'string'},
                                 'consensus_threshold': {'type': 'number'}},
                  'required': ['swarm_id', 'session_id']}},
 {'name': 'swarm_status',
  'description': 'Read swarm aggregate state and member vectors.',
  'inputSchema': {'type': 'object',
                  'properties': {'swarm_id': {'type': 'string'}},
                  'required': ['swarm_id']}}]



def tool_swarm_join(
    tools: "VermythTools",
    swarm_id: str,
    session_id: str,
    *,
    consensus_threshold: float = 0.75,
) -> dict[str, Any]:
    dim = AspectRegistry.get().dimensionality
    zero = SemanticVector(components=tuple(0.0 for _ in range(dim)))
    try:
        _ = tools._grimoire.read_swarm_state(swarm_id)
    except KeyError:
        state = SwarmState(
            swarm_id=str(swarm_id),
            consensus_threshold=float(consensus_threshold),
            status=SwarmStatus.STRAINED,
            aggregated_vector=zero,
        )
        tools._grimoire.write_swarm_state(state)
    tools._grimoire.upsert_swarm_member(str(swarm_id), str(session_id), zero, 0)
    return {"swarm_id": swarm_id, "session_id": session_id, "joined": True}


def tool_swarm_cast(
    tools: "VermythTools",
    swarm_id: str,
    session_id: str,
    vector: list[float],
    intent: dict[str, Any],
    *,
    consensus_threshold: float | None = None,
) -> dict[str, Any]:
    if len(vector) < 6:
        raise ValueError("vector must contain at least 6 floats")
    comps = tuple(float(x) for x in vector)
    vec = SemanticVector(components=comps)
    intent_obj = Intent(**intent)
    state = tools._grimoire.read_swarm_state(swarm_id)
    thr = (
        float(consensus_threshold)
        if consensus_threshold is not None
        else float(state.consensus_threshold)
    )
    raw = tools._grimoire.query_swarm_members(swarm_id)
    by_session = {sid: (v, streak) for sid, v, streak in raw}
    if session_id not in by_session:
        by_session[session_id] = (vec, 0)
    else:
        _old, streak = by_session[session_id]
        by_session[session_id] = (vec, streak)
    member_inputs: list[tuple[str, SemanticVector, int]] = [
        (sid, v, st) for sid, (v, st) in sorted(by_session.items(), key=lambda x: x[0])
    ]
    result, agg_vec, status, streaks = tools._engine.swarm_cast(
        intent_obj,
        member_inputs,
        consensus_threshold=thr,
    )
    for sid, streak in streaks.items():
        v_out = vec if sid == session_id else by_session[sid][0]
        tools._grimoire.upsert_swarm_member(str(swarm_id), sid, v_out, streak)
    tools._grimoire.write_swarm_state(
        SwarmState(
            swarm_id=str(swarm_id),
            consensus_threshold=thr,
            status=SwarmStatus(str(status)),
            aggregated_vector=agg_vec,
            last_cast_id=result.cast_id,
        )
    )
    tools._grimoire.write(result)
    return {
        "cast_id": result.cast_id,
        "verdict": result.verdict.verdict_type.name,
        "resonance": round(float(result.verdict.resonance.adjusted), 4),
        "swarm_status": status,
        "aggregated_vector": [round(c, 6) for c in agg_vec.components],
        "member_streaks": streaks,
    }


def tool_swarm_status(tools: "VermythTools", swarm_id: str) -> dict[str, Any]:
    state = tools._grimoire.read_swarm_state(swarm_id)
    members = tools._grimoire.query_swarm_members(swarm_id)
    return {
        "swarm_id": state.swarm_id,
        "status": state.status.value,
        "consensus_threshold": state.consensus_threshold,
        "last_cast_id": state.last_cast_id,
        "aggregated_vector": [round(c, 6) for c in state.aggregated_vector.components],
        "members": [
            {
                "session_id": sid,
                "coherence_streak": streak,
                "vector": [round(c, 6) for c in vec.components],
            }
            for sid, vec, streak in members
        ],
    }


def tool_gossip_sync(tools: "VermythTools", payload: dict[str, Any]) -> dict[str, Any]:
    gp = GossipPayload.model_validate(payload)
    return tools._grimoire.apply_gossip_sync(gp)


def dispatch_swarm_join(tools: "VermythTools", arguments: dict[str, Any]) -> dict[str, Any]:
    return tool_swarm_join(
        tools,
        swarm_id=arguments.get("swarm_id", ""),
        session_id=arguments.get("session_id", ""),
        consensus_threshold=float(arguments.get("consensus_threshold", 0.75)),
    )


def dispatch_swarm_cast(tools: "VermythTools", arguments: dict[str, Any]) -> dict[str, Any]:
    return tool_swarm_cast(
        tools,
        swarm_id=arguments.get("swarm_id", ""),
        session_id=arguments.get("session_id", ""),
        vector=arguments.get("vector", []),
        intent={
            "objective": arguments.get("objective", ""),
            "scope": arguments.get("scope", ""),
            "reversibility": arguments.get("reversibility", "PARTIAL"),
            "side_effect_tolerance": arguments.get("side_effect_tolerance", "MEDIUM"),
        },
        consensus_threshold=arguments.get("consensus_threshold"),
    )


def dispatch_swarm_status(tools: "VermythTools", arguments: dict[str, Any]) -> dict[str, Any]:
    return tool_swarm_status(tools, swarm_id=arguments.get("swarm_id", ""))


def dispatch_gossip_sync(tools: "VermythTools", arguments: dict[str, Any]) -> dict[str, Any]:
    return tool_gossip_sync(tools, arguments)


DISPATCH = {
    "gossip_sync": dispatch_gossip_sync,
    "swarm_cast": dispatch_swarm_cast,
    "swarm_join": dispatch_swarm_join,
    "swarm_status": dispatch_swarm_status,
}
