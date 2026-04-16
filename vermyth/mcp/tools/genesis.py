from __future__ import annotations

from typing import TYPE_CHECKING, Any

from vermyth.schema import SemanticQuery

if TYPE_CHECKING:
    from vermyth.mcp.tools.facade import VermythTools

TOOLS = [{'name': 'accept_genesis',
  'description': 'Accept and register an emergent aspect.',
  'inputSchema': {'type': 'object',
                  'properties': {'genesis_id': {'type': 'string'}},
                  'required': ['genesis_id']}},
 {'name': 'genesis_proposals',
  'description': 'List emergent aspect proposals.',
  'inputSchema': {'type': 'object',
                  'properties': {'status': {'type': 'string',
                                            'enum': ['PROPOSED',
                                                     'ACCEPTED',
                                                     'REJECTED',
                                                     'INTEGRATED']},
                                 'limit': {'type': 'integer'}},
                  'required': []}},
 {'name': 'propose_genesis',
  'description': 'Analyze cast history and propose emergent aspects.',
  'inputSchema': {'type': 'object',
                  'properties': {'history_limit': {'type': 'integer'},
                                 'min_cluster_size': {'type': 'integer'},
                                 'min_unexplained_variance': {'type': 'number'},
                                 'min_coherence_rate': {'type': 'number'}},
                  'required': []}},
{'name': 'review_genesis',
  'description': 'Review an emergent aspect proposal before accept/reject.',
  'inputSchema': {'type': 'object',
                  'properties': {'genesis_id': {'type': 'string'},
                                 'reviewer': {'type': 'string'},
                                 'note': {'type': 'string'}},
                  'required': ['genesis_id', 'reviewer']}},
 {'name': 'reject_genesis',
  'description': 'Reject an emergent aspect proposal.',
  'inputSchema': {'type': 'object',
                  'properties': {'genesis_id': {'type': 'string'}},
                  'required': ['genesis_id']}}]



def emergent_aspect_to_dict(aspect) -> dict[str, Any]:
    return {
        "genesis_id": aspect.genesis_id,
        "proposed_name": aspect.proposed_name,
        "derived_polarity": aspect.derived_polarity,
        "derived_entropy": aspect.derived_entropy,
        "proposed_symbol": aspect.proposed_symbol,
        "centroid_vector": list(aspect.centroid_vector.components),
        "support_count": aspect.support_count,
        "mean_resonance": aspect.mean_resonance,
        "coherence_rate": aspect.coherence_rate,
        "status": aspect.status.value,
        "proposed_at": aspect.proposed_at.isoformat(),
        "decided_at": aspect.decided_at.isoformat() if aspect.decided_at else None,
        "reviewed_by": aspect.reviewed_by,
        "reviewed_at": aspect.reviewed_at.isoformat() if aspect.reviewed_at else None,
        "review_note": aspect.review_note,
        "evidence_cast_ids": list(aspect.evidence_cast_ids),
    }


def tool_propose_genesis(
    tools: "VermythTools",
    *,
    history_limit: int = 500,
    min_cluster_size: int = 15,
    min_unexplained_variance: float = 0.3,
    min_coherence_rate: float = 0.6,
) -> list[dict[str, Any]]:
    history = tools._grimoire.query(SemanticQuery(limit=int(history_limit)))
    proposals = tools._engine.propose_genesis(
        history,
        min_cluster_size=int(min_cluster_size),
        min_unexplained_variance=float(min_unexplained_variance),
        min_coherence_rate=float(min_coherence_rate),
    )
    for proposal in proposals:
        tools._grimoire.write_emergent_aspect(proposal)
    return [emergent_aspect_to_dict(p) for p in proposals]


def tool_genesis_proposals(
    tools: "VermythTools", *, status: str | None = None, limit: int = 50
) -> list[dict[str, Any]]:
    rows = tools._grimoire.query_emergent_aspects(status=status, limit=int(limit))
    return [emergent_aspect_to_dict(r) for r in rows]


def tool_accept_genesis(tools: "VermythTools", genesis_id: str) -> dict[str, Any]:
    accepted = tools._grimoire.accept_emergent_aspect(genesis_id)
    return emergent_aspect_to_dict(accepted)


def tool_reject_genesis(tools: "VermythTools", genesis_id: str) -> dict[str, Any]:
    rejected = tools._grimoire.reject_emergent_aspect(genesis_id)
    return emergent_aspect_to_dict(rejected)


def tool_review_genesis(
    tools: "VermythTools",
    *,
    genesis_id: str,
    reviewer: str,
    note: str | None = None,
) -> dict[str, Any]:
    reviewed = tools._grimoire.review_emergent_aspect(genesis_id, reviewer, note)
    return emergent_aspect_to_dict(reviewed)


def dispatch_propose_genesis(
    tools: "VermythTools", arguments: dict[str, Any]
) -> list[dict[str, Any]]:
    return tool_propose_genesis(
        tools,
        history_limit=int(arguments.get("history_limit", 500)),
        min_cluster_size=int(arguments.get("min_cluster_size", 15)),
        min_unexplained_variance=float(arguments.get("min_unexplained_variance", 0.3)),
        min_coherence_rate=float(arguments.get("min_coherence_rate", 0.6)),
    )


def dispatch_genesis_proposals(
    tools: "VermythTools", arguments: dict[str, Any]
) -> list[dict[str, Any]]:
    return tool_genesis_proposals(
        tools,
        status=arguments.get("status"),
        limit=int(arguments.get("limit", 50)),
    )


def dispatch_accept_genesis(
    tools: "VermythTools", arguments: dict[str, Any]
) -> dict[str, Any]:
    return tool_accept_genesis(tools, genesis_id=arguments.get("genesis_id", ""))


def dispatch_reject_genesis(
    tools: "VermythTools", arguments: dict[str, Any]
) -> dict[str, Any]:
    return tool_reject_genesis(tools, genesis_id=arguments.get("genesis_id", ""))


def dispatch_review_genesis(
    tools: "VermythTools", arguments: dict[str, Any]
) -> dict[str, Any]:
    return tool_review_genesis(
        tools,
        genesis_id=arguments.get("genesis_id", ""),
        reviewer=arguments.get("reviewer", ""),
        note=arguments.get("note"),
    )


DISPATCH = {
    "accept_genesis": dispatch_accept_genesis,
    "genesis_proposals": dispatch_genesis_proposals,
    "propose_genesis": dispatch_propose_genesis,
    "review_genesis": dispatch_review_genesis,
    "reject_genesis": dispatch_reject_genesis,
}
