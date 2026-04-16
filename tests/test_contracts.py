import inspect

import pytest

import vermyth.contracts as contracts
from vermyth.contracts import (
    CLIContract,
    CompositionContract,
    EngineContract,
    EvaluationContract,
    ExtensionContract,
    GrimoireContract,
    MCPServerContract,
    ProjectionBackend,
)


def _abstract_callables(cls: type) -> dict[str, object]:
    out: dict[str, object] = {}
    for name in dir(cls):
        if name.startswith("_"):
            continue
        attr = getattr(cls, name)
        if getattr(attr, "__isabstractmethod__", False):
            out[name] = attr
    return out


def test_all_contract_classes_importable():
    for name in (
        "CompositionContract",
        "EvaluationContract",
        "EngineContract",
        "GrimoireContract",
        "MCPServerContract",
        "CLIContract",
        "ExtensionContract",
    ):
        assert getattr(contracts, name) is not None


@pytest.mark.parametrize(
    "cls",
    [
        CompositionContract,
        EvaluationContract,
        EngineContract,
        GrimoireContract,
        MCPServerContract,
        CLIContract,
        ExtensionContract,
    ],
)
def test_contract_cannot_instantiate(cls):
    with pytest.raises(TypeError):
        cls()


def test_engine_contract_abstract_methods():
    names = frozenset(_abstract_callables(EngineContract))
    assert names == frozenset(
        {
            "compose",
            "register_sigil_entry",
            "load_registered_sigils",
            "interpolate",
            "evaluate",
            "cast",
            "accumulate",
            "crystallize",
            "fluid_cast",
            "chained_cast",
            "sync_channel",
            "auto_cast",
            "swarm_cast",
            "compile_program",
            "execute_program",
            "propose_genesis",
            "infer_causal_edge",
            "evaluate_narrative",
            "predictive_cast",
            "decide",
        }
    )


def test_grimoire_contract_abstract_methods():
    names = frozenset(_abstract_callables(GrimoireContract))
    assert names == frozenset(
        {
            "write",
            "read",
            "query",
            "semantic_search",
            "write_seed",
            "read_seed",
            "query_seeds",
            "write_crystallized_sigil",
            "read_crystallized_sigil",
            "crystallized_for_aspects",
            "query_crystallized_sigils",
            "write_channel_state",
            "read_channel_state",
            "query_channel_states",
            "write_session",
            "read_session",
            "close_session",
            "advance_session_sequence",
            "write_session_packet",
            "write_session_response",
            "query_session_packets",
            "query_session_responses",
            "write_registered_aspect",
            "query_registered_aspects",
            "write_basis_version",
            "read_basis_version",
            "read_latest_basis_version",
            "write_registered_sigil",
            "read_registered_sigil",
            "query_registered_sigils",
            "write_divergence_report",
            "read_divergence_report",
            "query_divergence_reports",
            "write_divergence_thresholds",
            "read_divergence_thresholds",
            "write_swarm_state",
            "read_swarm_state",
            "upsert_swarm_member",
            "query_swarm_members",
            "apply_gossip_sync",
            "write_program",
            "read_program",
            "query_programs",
            "write_execution",
            "read_execution",
            "query_executions",
            "write_emergent_aspect",
            "read_emergent_aspect",
            "query_emergent_aspects",
            "accept_emergent_aspect",
            "reject_emergent_aspect",
            "write_causal_edge",
            "read_causal_edge",
            "query_causal_edges",
            "causal_subgraph",
            "delete_causal_edge",
            "write_policy_decision",
            "read_policy_decision",
            "query_policy_decisions",
            "delete",
        }
    )


def test_mcp_server_contract_abstract_methods():
    names = frozenset(_abstract_callables(MCPServerContract))
    assert names == frozenset(
        {
            "tool_decide",
            "tool_cast",
            "tool_query",
            "tool_semantic_search",
            "tool_inspect",
            "tool_seeds",
            "tool_crystallized_sigils",
            "tool_register_aspect",
            "tool_register_sigil",
            "tool_registered_aspects",
            "tool_registered_sigils",
            "tool_divergence",
            "tool_set_divergence_thresholds",
            "tool_divergence_thresholds",
        }
    )


def test_cli_contract_abstract_methods():
    names = frozenset(_abstract_callables(CLIContract))
    assert names == frozenset(
        {
            "cmd_decide",
            "cmd_cast",
            "cmd_query",
            "cmd_search",
            "cmd_inspect",
            "cmd_seeds",
            "cmd_crystallized_sigils",
            "cmd_register_aspect",
            "cmd_register_sigil",
            "cmd_aspects",
            "cmd_registered_sigils",
            "cmd_divergence",
            "cmd_set_thresholds",
            "cmd_thresholds",
        }
    )


def test_extension_contract_abstract_methods():
    names = frozenset(_abstract_callables(ExtensionContract))
    assert names == frozenset({"register_aspect", "register_sigil"})


@pytest.mark.parametrize(
    "cls",
    [
        EngineContract,
        GrimoireContract,
        MCPServerContract,
        CLIContract,
        ExtensionContract,
    ],
)
def test_every_abstract_method_has_docstring_and_annotations(cls):
    empty = inspect.Parameter.empty
    for name, fn in _abstract_callables(cls).items():
        doc = inspect.getdoc(fn)
        assert doc is not None and doc.strip() != ""
        sig = inspect.signature(fn)
        for param in sig.parameters.values():
            if param.name == "self":
                continue
            assert (
                param.annotation is not empty
            ), f"{cls.__name__}.{name} missing annotation for {param.name}"
        assert (
            sig.return_annotation is not empty
        ), f"{cls.__name__}.{name} missing return annotation"


def test_projection_backend_importable():
    assert getattr(contracts, "ProjectionBackend") is ProjectionBackend


def test_projection_backend_cannot_instantiate():
    with pytest.raises(TypeError):
        ProjectionBackend()


def test_projection_backend_declares_only_project():
    assert frozenset(_abstract_callables(ProjectionBackend)) == frozenset(
        {"project"}
    )


def test_projection_backend_project_has_docstring():
    doc = inspect.getdoc(ProjectionBackend.project)
    assert doc is not None and doc.strip() != ""


def test_projection_backend_project_has_annotations():
    fn = ProjectionBackend.project
    empty = inspect.Parameter.empty
    sig = inspect.signature(fn)
    for param in sig.parameters.values():
        if param.name == "self":
            continue
        assert param.annotation is not empty
    assert sig.return_annotation is not empty


def test_projection_backend_concrete_six_zeros():
    class ZeroBackend(ProjectionBackend):
        def project(self, objective: str, scope: str) -> list[float]:
            return [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

    b = ZeroBackend()
    assert b.project("any", "any") == [0.0] * 6


def test_projection_backend_fewer_than_six_floats_is_detectable():
    assert "ValueError" in (ProjectionBackend.project.__doc__ or "")
    assert "at least 6" in (ProjectionBackend.project.__doc__ or "").lower()

    class ShortBackend(ProjectionBackend):
        def project(self, objective: str, scope: str) -> list[float]:
            return [0.0, 0.0, 0.0, 0.0, 0.0]

    out = ShortBackend().project("o", "s")
    assert len(out) < 6
