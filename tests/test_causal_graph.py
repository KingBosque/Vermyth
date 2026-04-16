from vermyth.schema import CausalEdge, CausalEdgeType, CausalQuery, Intent


def _intent() -> dict:
    return {
        "objective": "trace causality",
        "scope": "lab",
        "reversibility": "PARTIAL",
        "side_effect_tolerance": "MEDIUM",
    }


def test_infer_and_persist_causal_edge(make_tools):
    a = make_tools.tool_cast(["MIND", "LIGHT"], _intent())
    b = make_tools.tool_cast(["MIND", "FORM"], _intent())
    out = make_tools.tool_infer_causal_edge(a["cast_id"], b["cast_id"])
    if out["edge"] is not None:
        edge_id = out["edge"]["edge_id"]
        reread = make_tools._grimoire.read_causal_edge(edge_id)  # noqa: SLF001
        assert reread.edge_id == edge_id


def test_causal_subgraph_and_narrative(make_tools):
    a = make_tools.tool_cast(["MIND", "LIGHT"], _intent())
    b = make_tools.tool_cast(["MIND", "FORM"], _intent())
    c = make_tools.tool_cast(["MOTION", "LIGHT"], _intent())
    e1 = CausalEdge(
        source_cast_id=a["cast_id"],
        target_cast_id=b["cast_id"],
        edge_type=CausalEdgeType.CAUSES,
        weight=0.8,
    )
    e2 = CausalEdge(
        source_cast_id=b["cast_id"],
        target_cast_id=c["cast_id"],
        edge_type=CausalEdgeType.ENABLES,
        weight=0.7,
    )
    make_tools._grimoire.write_causal_edge(e1)  # noqa: SLF001
    make_tools._grimoire.write_causal_edge(e2)  # noqa: SLF001
    graph = make_tools._grimoire.causal_subgraph(  # noqa: SLF001
        CausalQuery(root_cast_id=a["cast_id"], max_depth=3)
    )
    assert a["cast_id"] in graph.nodes
    assert len(graph.edges) >= 1


def test_predictive_cast_from_graph(resonance_engine):
    graph = CausalQuery(root_cast_id="A")
    # build minimal subgraph object via model helper on grimoire-less path
    from vermyth.schema import CausalSubgraph

    sub = CausalSubgraph(root_cast_id=graph.root_cast_id, nodes=["A"], edges=[])
    result = resonance_engine.predictive_cast(
        sub,
        Intent.model_validate(_intent()),
    )
    assert result.cast_id
