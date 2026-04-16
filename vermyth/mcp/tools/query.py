from __future__ import annotations

from typing import TYPE_CHECKING, Any

from vermyth.schema import CastResult, SemanticQuery, SemanticVector, VerdictType

if TYPE_CHECKING:
    from vermyth.mcp.tools.facade import VermythTools

TOOLS = [{'name': 'inspect',
  'description': 'Retrieve a single CastResult by cast_id.',
  'inputSchema': {'type': 'object',
                  'properties': {'cast_id': {'type': 'string',
                                             'description': 'The ULID cast_id of the CastResult to '
                                                            'retrieve.'}},
                  'required': ['cast_id']}},
 {'name': 'lineage',
  'description': 'Walk the parent chain from a cast_id and return CastResults root-first.',
  'inputSchema': {'type': 'object',
                  'properties': {'cast_id': {'type': 'string',
                                             'description': 'Starting cast id (typically a leaf); '
                                                            'walks toward the root.'},
                                 'max_depth': {'type': 'integer',
                                               'description': 'Maximum number of parent hops. '
                                                              'Default 50.'}},
                  'required': ['cast_id']}},
 {'name': 'query',
  'description': 'Query the grimoire for CastResults by field filters.',
  'inputSchema': {'type': 'object',
                  'properties': {'verdict_filter': {'type': 'string',
                                                    'enum': ['COHERENT', 'PARTIAL', 'INCOHERENT'],
                                                    'description': 'Optional verdict type filter.'},
                                 'min_resonance': {'type': 'number',
                                                   'description': 'Minimum adjusted resonance '
                                                                  'score. 0.0 to 1.0.'},
                                 'branch_id': {'type': 'string',
                                               'description': 'Filter by lineage branch ID.'},
                                 'limit': {'type': 'integer',
                                           'description': 'Maximum results to return. Default 20, '
                                                          'max 100.'}},
                  'required': []}},
 {'name': 'semantic_search',
  'description': 'Search the grimoire by semantic proximity to a given aspect vector.',
  'inputSchema': {'type': 'object',
                  'properties': {'proximity_vector': {'type': 'array',
                                                      'items': {'type': 'number'},
                                                      'description': 'Six floats in canonical '
                                                                     'aspect order: VOID, FORM, '
                                                                     'MOTION, MIND, DECAY, LIGHT. '
                                                                     'Each in range -1.0 to 1.0.'},
                                 'threshold': {'type': 'number',
                                               'description': 'Minimum cosine similarity. 0.0 to '
                                                              '1.0.'},
                                 'limit': {'type': 'integer',
                                           'description': 'Maximum results to return. Default 20, '
                                                          'max 100.'}},
                  'required': ['proximity_vector', 'threshold']}}]



def tool_query(tools: "VermythTools", filters: dict[str, Any]) -> list[dict[str, Any]]:
    try:
        kwargs: dict[str, Any] = {}
        vf = filters.get("verdict_filter")
        if vf is not None:
            kwargs["verdict_filter"] = VerdictType[vf]
        mr = filters.get("min_resonance")
        if mr is not None:
            kwargs["min_resonance"] = float(mr)
        bid = filters.get("branch_id")
        if bid is not None:
            kwargs["branch_id"] = str(bid)
        if "limit" in filters and filters["limit"] is not None:
            kwargs["limit"] = int(filters["limit"])
        else:
            kwargs["limit"] = 20
        query = SemanticQuery(**kwargs)
        rows = tools._grimoire.query(query)
        return [tools._cast_result_to_dict(row) for row in rows]
    except ValueError:
        raise
    except Exception as exc:
        if (
            type(exc).__name__ == "ValidationError"
            and type(exc).__module__.startswith("pydantic")
        ):
            raise
        raise RuntimeError(f"query failed: {exc}") from exc


def tool_semantic_search(
    tools: "VermythTools",
    proximity_vector: list[float],
    threshold: float,
    limit: int,
) -> list[dict[str, Any]]:
    try:
        if len(proximity_vector) != 6:
            raise ValueError("proximity_vector must have exactly 6 elements")
        for x in proximity_vector:
            xf = float(x)
            if xf < -1.0 or xf > 1.0:
                raise ValueError(
                    "proximity_vector components must be between -1.0 and 1.0"
                )
        if threshold < 0.0 or threshold > 1.0:
            raise ValueError("threshold must be between 0.0 and 1.0")
        vector = SemanticVector(components=tuple(float(c) for c in proximity_vector))
        query = SemanticQuery(
            proximity_to=vector,
            proximity_threshold=float(threshold),
            limit=int(limit),
        )
        rows = tools._grimoire.semantic_search(query)
        return [tools._cast_result_to_dict(row) for row in rows]
    except ValueError:
        raise
    except Exception as exc:
        raise RuntimeError(f"semantic_search failed: {exc}") from exc


def tool_inspect(tools: "VermythTools", cast_id: str) -> dict[str, Any]:
    try:
        result = tools._grimoire.read(cast_id)
        return tools._cast_result_to_dict(result)
    except KeyError:
        raise
    except Exception as exc:
        raise RuntimeError(f"inspect failed: {exc}") from exc


def tool_lineage(
    tools: "VermythTools",
    cast_id: str,
    max_depth: int = 50,
) -> list[dict[str, Any]]:
    try:
        chain_rev: list[CastResult] = []
        cur_id = cast_id
        for _ in range(max_depth):
            row = tools._grimoire.read(cur_id)
            chain_rev.append(row)
            if row.lineage is None:
                break
            cur_id = row.lineage.parent_cast_id
        chain = list(reversed(chain_rev))
        return [tools._cast_result_to_dict(row) for row in chain]
    except KeyError:
        raise
    except Exception as exc:
        raise RuntimeError(f"lineage failed: {exc}") from exc


def dispatch_query(tools: "VermythTools", arguments: dict[str, Any]) -> list[dict[str, Any]]:
    return tool_query(tools, arguments)


def dispatch_semantic_search(
    tools: "VermythTools", arguments: dict[str, Any]
) -> list[dict[str, Any]]:
    return tool_semantic_search(
        tools,
        proximity_vector=arguments.get("proximity_vector", []),
        threshold=float(arguments.get("threshold", 0.5)),
        limit=int(arguments.get("limit", 20)),
    )


def dispatch_inspect(tools: "VermythTools", arguments: dict[str, Any]) -> dict[str, Any]:
    return tool_inspect(tools, cast_id=arguments.get("cast_id", ""))


def dispatch_lineage(
    tools: "VermythTools", arguments: dict[str, Any]
) -> list[dict[str, Any]]:
    return tool_lineage(
        tools,
        cast_id=arguments.get("cast_id", ""),
        max_depth=int(arguments.get("max_depth", 50)),
    )


DISPATCH = {
    "inspect": dispatch_inspect,
    "lineage": dispatch_lineage,
    "query": dispatch_query,
    "semantic_search": dispatch_semantic_search,
}
