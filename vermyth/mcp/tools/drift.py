from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from vermyth.registry import AspectRegistry
from vermyth.schema import CastResult, DivergenceReport, DivergenceStatus, DivergenceThresholds

if TYPE_CHECKING:
    from vermyth.mcp.tools.facade import VermythTools

TOOLS = [{'name': 'channel_status',
  'description': 'Read the current ChannelState for a branch_id.',
  'inputSchema': {'type': 'object',
                  'properties': {'branch_id': {'type': 'string'}},
                  'required': ['branch_id']}},
 {'name': 'divergence',
  'description': 'Read the divergence report for a cast_id.',
  'inputSchema': {'type': 'object',
                  'properties': {'cast_id': {'type': 'string'}},
                  'required': ['cast_id']}},
 {'name': 'divergence_reports',
  'description': 'List divergence reports ordered newest-first (optionally filtered).',
  'inputSchema': {'type': 'object',
                  'properties': {'status': {'type': 'string',
                                            'enum': ['STABLE', 'DRIFTING', 'DIVERGED']},
                                 'limit': {'type': 'integer'},
                                 'since': {'type': 'string',
                                           'description': 'ISO datetime; include reports computed '
                                                          'at/after this time.'}},
                  'required': []}},
 {'name': 'divergence_thresholds',
  'description': 'Read active divergence thresholds.',
  'inputSchema': {'type': 'object', 'properties': {}, 'required': []}},
 {'name': 'drift_branches',
  'description': 'Rank branches by drift severity (diverged/drifting counts and max drift).',
  'inputSchema': {'type': 'object', 'properties': {'limit': {'type': 'integer'}}, 'required': []}},
 {'name': 'lineage_drift',
  'description': "Summarize drift across a cast's lineage chain (cumulative/max + contributors).",
  'inputSchema': {'type': 'object',
                  'properties': {'cast_id': {'type': 'string'},
                                 'max_depth': {'type': 'integer'},
                                 'top_k': {'type': 'integer'}},
                  'required': ['cast_id']}},
 {'name': 'set_divergence_thresholds',
  'description': 'Update divergence thresholds used for STABLE/DRIFTING/DIVERGED classification.',
  'inputSchema': {'type': 'object',
                  'properties': {'l2_stable_max': {'type': 'number'},
                                 'l2_diverged_min': {'type': 'number'},
                                 'cosine_stable_max': {'type': 'number'},
                                 'cosine_diverged_min': {'type': 'number'}},
                  'required': []}},
 {'name': 'sync_channel',
  'description': 'Sync (recover) a channel using crystallization-derived constraints.',
  'inputSchema': {'type': 'object',
                  'properties': {'branch_id': {'type': 'string'}},
                  'required': ['branch_id']}}]



def tool_divergence(tools: "VermythTools", cast_id: str) -> dict[str, Any]:
    report = tools._grimoire.read_divergence_report(cast_id)
    return {
        "cast_id": report.cast_id,
        "parent_cast_id": report.parent_cast_id,
        "l2_magnitude": round(float(report.l2_magnitude), 6),
        "cosine_distance": round(float(report.cosine_distance), 6),
        "status": report.status.name,
        "computed_at": report.computed_at.isoformat(),
    }


def tool_set_divergence_thresholds(
    tools: "VermythTools", payload: dict[str, Any]
) -> dict[str, Any]:
    thresholds = DivergenceThresholds(
        l2_stable_max=float(payload.get("l2_stable_max", tools._active_thresholds.l2_stable_max)),
        l2_diverged_min=float(payload.get("l2_diverged_min", tools._active_thresholds.l2_diverged_min)),
        cosine_stable_max=float(payload.get("cosine_stable_max", tools._active_thresholds.cosine_stable_max)),
        cosine_diverged_min=float(payload.get("cosine_diverged_min", tools._active_thresholds.cosine_diverged_min)),
    )
    tools._grimoire.write_divergence_thresholds(thresholds)
    tools._active_thresholds = thresholds
    return {
        "l2_stable_max": thresholds.l2_stable_max,
        "l2_diverged_min": thresholds.l2_diverged_min,
        "cosine_stable_max": thresholds.cosine_stable_max,
        "cosine_diverged_min": thresholds.cosine_diverged_min,
    }


def tool_divergence_thresholds(tools: "VermythTools") -> dict[str, Any]:
    thresholds = tools._active_thresholds
    return {
        "l2_stable_max": thresholds.l2_stable_max,
        "l2_diverged_min": thresholds.l2_diverged_min,
        "cosine_stable_max": thresholds.cosine_stable_max,
        "cosine_diverged_min": thresholds.cosine_diverged_min,
    }


def tool_divergence_reports(
    tools: "VermythTools",
    *,
    status: str | None = None,
    limit: int = 50,
    since: str | None = None,
) -> list[dict[str, Any]]:
    st: DivergenceStatus | None = None
    if status is not None:
        st = DivergenceStatus[str(status)]
    since_dt: datetime | None = None
    if since is not None:
        since_dt = datetime.fromisoformat(str(since))
    rows = tools._grimoire.query_divergence_reports(st, int(limit), since=since_dt)
    out: list[dict[str, Any]] = []
    for row in rows:
        out.append(
            {
                "cast_id": row.cast_id,
                "parent_cast_id": row.parent_cast_id,
                "status": row.status.name,
                "l2_magnitude": round(float(row.l2_magnitude), 6),
                "cosine_distance": round(float(row.cosine_distance), 6),
                "computed_at": row.computed_at.isoformat(),
            }
        )
    return out


def tool_drift_branches(tools: "VermythTools", *, limit: int = 25) -> list[dict[str, Any]]:
    rows = tools._grimoire.drift_branches(limit=int(limit))
    out: list[dict[str, Any]] = []
    for row in rows:
        out.append(
            {
                "branch_id": row["branch_id"],
                "casts_with_divergence": int(row["casts_with_divergence"]),
                "diverged_count": int(row["diverged_count"]),
                "drifting_count": int(row["drifting_count"]),
                "max_l2": round(float(row["max_l2"]), 6),
                "max_cosine_distance": round(float(row["max_cosine_distance"]), 6),
                "latest_computed_at": row["latest_computed_at"],
            }
        )
    return out


def tool_lineage_drift(
    tools: "VermythTools",
    *,
    cast_id: str,
    max_depth: int = 50,
    top_k: int = 3,
) -> dict[str, Any]:
    registry = AspectRegistry.get()
    order = list(registry.full_order)
    chain_rev: list[CastResult] = []
    cur_id = str(cast_id)
    for _ in range(int(max_depth)):
        cr = tools._grimoire.read(cur_id)
        chain_rev.append(cr)
        if cr.lineage is None:
            break
        cur_id = cr.lineage.parent_cast_id
    chain = list(reversed(chain_rev))
    hops: list[dict[str, Any]] = []
    cumulative_l2 = 0.0
    cumulative_cos = 0.0
    max_l2 = 0.0
    max_cos = 0.0
    agg_contrib: dict[str, float] = {}
    for cr in chain:
        if cr.lineage is None:
            continue
        div_vec = cr.lineage.divergence_vector
        report: DivergenceReport | None
        try:
            report = tools._grimoire.read_divergence_report(cr.cast_id)
        except Exception:
            report = None
        if report is None:
            try:
                parent = tools._grimoire.read(cr.lineage.parent_cast_id)
                report = DivergenceReport.classify(
                    cast_id=cr.cast_id,
                    parent_cast_id=cr.lineage.parent_cast_id,
                    parent_vector=parent.sigil.semantic_vector,
                    child_vector=cr.sigil.semantic_vector,
                    thresholds=tools._active_thresholds,
                )
            except Exception:
                report = None
        l2 = float(report.l2_magnitude) if report is not None else 0.0
        cos = float(report.cosine_distance) if report is not None else 0.0
        cumulative_l2 += l2
        cumulative_cos += cos
        max_l2 = max(max_l2, l2)
        max_cos = max(max_cos, cos)
        top: list[dict[str, Any]] = []
        if div_vec is not None:
            comps = div_vec.components
            scored: list[tuple[float, str]] = []
            for i, value in enumerate(comps):
                name = order[i].name if i < len(order) else f"DIM_{i}"
                scored.append((abs(float(value)), name))
                agg_contrib[name] = agg_contrib.get(name, 0.0) + abs(float(value))
            scored.sort(reverse=True, key=lambda t: t[0])
            for mag, name in scored[: max(0, int(top_k))]:
                top.append({"aspect": name, "abs_delta": round(float(mag), 6)})
        hops.append(
            {
                "cast_id": cr.cast_id,
                "parent_cast_id": cr.lineage.parent_cast_id,
                "branch_id": cr.lineage.branch_id,
                "status": report.status.name if report is not None else "UNKNOWN",
                "l2_magnitude": round(l2, 6),
                "cosine_distance": round(cos, 6),
                "top_contributors": top,
            }
        )
    agg_sorted = sorted(agg_contrib.items(), key=lambda kv: kv[1], reverse=True)
    agg_top = [
        {"aspect": key, "abs_delta_sum": round(float(value), 6)}
        for key, value in agg_sorted[: max(0, int(top_k))]
    ]
    return {
        "cast_id": str(cast_id),
        "chain_length": len(chain),
        "hops": hops,
        "cumulative_l2": round(cumulative_l2, 6),
        "cumulative_cosine_distance": round(cumulative_cos, 6),
        "max_l2": round(max_l2, 6),
        "max_cosine_distance": round(max_cos, 6),
        "top_contributors": agg_top,
    }


def tool_channel_status(tools: "VermythTools", branch_id: str) -> dict[str, Any]:
    state = tools._grimoire.read_channel_state(str(branch_id))
    return tools._channel_state_to_dict(state)


def tool_sync_channel(tools: "VermythTools", branch_id: str) -> dict[str, Any]:
    state = tools._grimoire.read_channel_state(str(branch_id))
    seeds = tools._grimoire.query_seeds(aspect_pattern=None, crystallized=None)
    synced = tools._engine.sync_channel(state, seeds)
    tools._grimoire.write_channel_state(synced)
    return tools._channel_state_to_dict(synced)


def dispatch_divergence(tools: "VermythTools", arguments: dict[str, Any]) -> dict[str, Any]:
    return tool_divergence(tools, cast_id=arguments.get("cast_id", ""))


def dispatch_set_divergence_thresholds(
    tools: "VermythTools", arguments: dict[str, Any]
) -> dict[str, Any]:
    return tool_set_divergence_thresholds(tools, arguments)


def dispatch_divergence_thresholds(
    tools: "VermythTools", arguments: dict[str, Any]
) -> dict[str, Any]:
    _ = arguments
    return tool_divergence_thresholds(tools)


def dispatch_divergence_reports(
    tools: "VermythTools", arguments: dict[str, Any]
) -> list[dict[str, Any]]:
    return tool_divergence_reports(
        tools,
        status=arguments.get("status"),
        limit=int(arguments.get("limit", 50)),
        since=arguments.get("since"),
    )


def dispatch_drift_branches(
    tools: "VermythTools", arguments: dict[str, Any]
) -> list[dict[str, Any]]:
    return tool_drift_branches(tools, limit=int(arguments.get("limit", 25)))


def dispatch_lineage_drift(
    tools: "VermythTools", arguments: dict[str, Any]
) -> dict[str, Any]:
    return tool_lineage_drift(
        tools,
        cast_id=arguments.get("cast_id", ""),
        max_depth=int(arguments.get("max_depth", 50)),
        top_k=int(arguments.get("top_k", 3)),
    )


def dispatch_channel_status(
    tools: "VermythTools", arguments: dict[str, Any]
) -> dict[str, Any]:
    return tool_channel_status(tools, branch_id=arguments.get("branch_id", ""))


def dispatch_sync_channel(
    tools: "VermythTools", arguments: dict[str, Any]
) -> dict[str, Any]:
    return tool_sync_channel(tools, branch_id=arguments.get("branch_id", ""))


DISPATCH = {
    "channel_status": dispatch_channel_status,
    "divergence": dispatch_divergence,
    "divergence_reports": dispatch_divergence_reports,
    "divergence_thresholds": dispatch_divergence_thresholds,
    "drift_branches": dispatch_drift_branches,
    "lineage_drift": dispatch_lineage_drift,
    "set_divergence_thresholds": dispatch_set_divergence_thresholds,
    "sync_channel": dispatch_sync_channel,
}
