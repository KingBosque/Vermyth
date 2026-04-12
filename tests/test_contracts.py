import inspect
import sys
from pathlib import Path

_root = Path(__file__).resolve().parents[1]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import pytest

import vermyth.contracts as contracts
from vermyth.contracts import (
    CLIContract,
    EngineContract,
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
        {"compose", "evaluate", "cast", "accumulate", "crystallize"}
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
            "delete",
        }
    )


def test_mcp_server_contract_abstract_methods():
    names = frozenset(_abstract_callables(MCPServerContract))
    assert names == frozenset(
        {
            "tool_cast",
            "tool_query",
            "tool_semantic_search",
            "tool_inspect",
            "tool_seeds",
        }
    )


def test_cli_contract_abstract_methods():
    names = frozenset(_abstract_callables(CLIContract))
    assert names == frozenset(
        {
            "cmd_cast",
            "cmd_query",
            "cmd_search",
            "cmd_inspect",
            "cmd_seeds",
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
    assert "six" in (ProjectionBackend.project.__doc__ or "").lower()

    class ShortBackend(ProjectionBackend):
        def project(self, objective: str, scope: str) -> list[float]:
            return [0.0, 0.0, 0.0, 0.0, 0.0]

    out = ShortBackend().project("o", "s")
    assert len(out) != 6
