from __future__ import annotations

from typing import TYPE_CHECKING, Any

from vermyth.schema import CausalEdge, CausalEdgeType, CausalQuery, Intent

from vermyth.mcp.tools.casting import cast_result_to_dict

if TYPE_CHECKING:
    from vermyth.mcp.tools.facade import VermythTools

TOOLS = [{'name': 'add_causal_edge',
  'description': 'Add a causal edge explicitly.',
  'inputSchema': {'type': 'object',
                  'properties': {'edge_id': {'type': 'string'},
                                 'source_cast_id': {'type': 'string'},
                                 'target_cast_id': {'type': 'string'},
                                 'edge_type': {'type': 'string',
                                               'enum': ['CAUSES',
                                                        'INHIBITS',
                                                        'ENABLES',
                                                        'REQUIRES']},
                                 'weight': {'type': 'number'},
                                 'evidence': {'type': 'string'}},
                  'required': ['source_cast_id', 'target_cast_id', 'edge_type', 'weight']}},
 {'name': 'causal_subgraph',
  'description': 'Traverse the causal graph from a root cast.',
  'inputSchema': {'type': 'object',
                  'properties': {'root_cast_id': {'type': 'string'},
                                 'edge_types': {'type': 'array', 'items': {'type': 'string'}},
                                 'direction': {'type': 'string',
                                               'enum': ['forward', 'backward', 'both']},
                                 'max_depth': {'type': 'integer'},
                                 'min_weight': {'type': 'number'}},
                  'required': ['root_cast_id']}},
 {'name': 'evaluate_narrative',
  'description': 'Evaluate coherence of a set of causal edges.',
  'inputSchema': {'type': 'object',
                  'properties': {'edge_ids': {'type': 'array', 'items': {'type': 'string'}}},
                  'required': ['edge_ids']}},
 {'name': 'infer_causal_edge',
  'description': 'Infer and persist a causal edge between two casts.',
  'inputSchema': {'type': 'object',
                  'properties': {'source_cast_id': {'type': 'string'},
                                 'target_cast_id': {'type': 'string'}},
                  'required': ['source_cast_id', 'target_cast_id']}},
 {'name': 'predictive_cast',
  'description': 'Generate a predictive cast from a causal subgraph root.',
  'inputSchema': {'type': 'object',
                  'properties': {'root_cast_id': {'type': 'string'},
                                 'objective': {'type': 'string'},
                                 'scope': {'type': 'string'},
                                 'reversibility': {'type': 'string'},
                                 'side_effect_tolerance': {'type': 'string'}},
                  'required': ['root_cast_id',
                               'objective',
                               'scope',
                               'reversibility',
                               'side_effect_tolerance']}}]



def causal_edge_to_dict(edge: CausalEdge) -> dict[str, Any]:
    return {
        "edge_id": edge.edge_id,
        "source_cast_id": edge.source_cast_id,
        "target_cast_id": edge.target_cast_id,
        "edge_type": edge.edge_type.value,
        "weight": edge.weight,
        "created_at": edge.created_at.isoformat(),
        "evidence": edge.evidence,
    }


def causal_subgraph_to_dict(graph) -> dict[str, Any]:
    return {
        "root_cast_id": graph.root_cast_id,
        "nodes": list(graph.nodes),
        "edges": [causal_edge_to_dict(e) for e in graph.edges],
        "narrative_coherence": graph.narrative_coherence,
    }


def tool_infer_causal_edge(
    tools: "VermythTools", source_cast_id: str, target_cast_id: str
) -> dict[str, Any]:
    source = tools._grimoire.read(str(source_cast_id))
    target = tools._grimoire.read(str(target_cast_id))
    edge = tools._engine.infer_causal_edge(source, target)
    if edge is None:
        return {"edge": None}
    tools._grimoire.write_causal_edge(edge)
    return {"edge": causal_edge_to_dict(edge)}


def tool_add_causal_edge(tools: "VermythTools", payload: dict[str, Any]) -> dict[str, Any]:
    edge = CausalEdge.model_validate(payload)
    tools._grimoire.write_causal_edge(edge)
    return causal_edge_to_dict(edge)


def tool_causal_subgraph(
    tools: "VermythTools",
    *,
    root_cast_id: str,
    edge_types: list[str] | None = None,
    direction: str = "both",
    max_depth: int = 5,
    min_weight: float = 0.0,
) -> dict[str, Any]:
    query_payload: dict[str, Any] = {
        "root_cast_id": str(root_cast_id),
        "direction": str(direction),
        "max_depth": int(max_depth),
        "min_weight": float(min_weight),
    }
    if edge_types is not None:
        query_payload["edge_types"] = edge_types
    graph = tools._grimoire.causal_subgraph(CausalQuery.model_validate(query_payload))
    return causal_subgraph_to_dict(graph)


def tool_evaluate_narrative(tools: "VermythTools", edge_ids: list[str]) -> dict[str, Any]:
    edges = [tools._grimoire.read_causal_edge(eid) for eid in edge_ids]
    score = tools._engine.evaluate_narrative(edges)
    return {"narrative_coherence": score, "edge_count": len(edges)}


def tool_predictive_cast(
    tools: "VermythTools", root_cast_id: str, intent: dict[str, Any]
) -> dict[str, Any]:
    graph = tools._grimoire.causal_subgraph(CausalQuery(root_cast_id=str(root_cast_id)))
    result = tools._engine.predictive_cast(graph, Intent.model_validate(intent))
    tools._grimoire.write(result)

    outgoing = {e.source_cast_id for e in graph.edges}
    leaves = [nid for nid in graph.nodes if nid not in outgoing]
    for leaf_id in leaves:
        try:
            leaf = tools._grimoire.read(leaf_id)
        except Exception:
            continue
        inferred = tools._engine.infer_causal_edge(leaf, result)
        if inferred is not None:
            try:
                tools._grimoire.write_causal_edge(
                    CausalEdge.model_construct(
                        edge_id=inferred.edge_id,
                        source_cast_id=inferred.source_cast_id,
                        target_cast_id=inferred.target_cast_id,
                        edge_type=CausalEdgeType.CAUSES,
                        weight=inferred.weight,
                        created_at=inferred.created_at,
                        evidence=inferred.evidence,
                    )
                )
            except Exception:
                continue
    return cast_result_to_dict(result)


def dispatch_infer_causal_edge(
    tools: "VermythTools", arguments: dict[str, Any]
) -> dict[str, Any]:
    return tool_infer_causal_edge(
        tools,
        source_cast_id=arguments.get("source_cast_id", ""),
        target_cast_id=arguments.get("target_cast_id", ""),
    )


def dispatch_add_causal_edge(
    tools: "VermythTools", arguments: dict[str, Any]
) -> dict[str, Any]:
    return tool_add_causal_edge(tools, arguments)


def dispatch_causal_subgraph(
    tools: "VermythTools", arguments: dict[str, Any]
) -> dict[str, Any]:
    return tool_causal_subgraph(
        tools,
        root_cast_id=arguments.get("root_cast_id", ""),
        edge_types=arguments.get("edge_types"),
        direction=arguments.get("direction", "both"),
        max_depth=int(arguments.get("max_depth", 5)),
        min_weight=float(arguments.get("min_weight", 0.0)),
    )


def dispatch_evaluate_narrative(
    tools: "VermythTools", arguments: dict[str, Any]
) -> dict[str, Any]:
    return tool_evaluate_narrative(tools, edge_ids=arguments.get("edge_ids", []))


def dispatch_predictive_cast(
    tools: "VermythTools", arguments: dict[str, Any]
) -> dict[str, Any]:
    return tool_predictive_cast(
        tools,
        root_cast_id=arguments.get("root_cast_id", ""),
        intent={
            "objective": arguments.get("objective", ""),
            "scope": arguments.get("scope", ""),
            "reversibility": arguments.get("reversibility", "PARTIAL"),
            "side_effect_tolerance": arguments.get("side_effect_tolerance", "MEDIUM"),
        },
    )


DISPATCH = {
    "add_causal_edge": dispatch_add_causal_edge,
    "causal_subgraph": dispatch_causal_subgraph,
    "evaluate_narrative": dispatch_evaluate_narrative,
    "infer_causal_edge": dispatch_infer_causal_edge,
    "predictive_cast": dispatch_predictive_cast,
}
