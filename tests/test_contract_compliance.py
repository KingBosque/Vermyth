import inspect

import pytest

from vermyth.contracts import GrimoireContract, MCPServerContract
from vermyth.grimoire.store import Grimoire
from vermyth.mcp.tools import VermythTools


def _public_callables(cls: type) -> dict[str, object]:
    out: dict[str, object] = {}
    for name in dir(cls):
        if name.startswith("_"):
            continue
        out[name] = getattr(cls, name)
    return out


def _abstract_methods(cls: type) -> set[str]:
    out: set[str] = set()
    for name, attr in _public_callables(cls).items():
        if getattr(attr, "__isabstractmethod__", False):
            out.add(name)
    return out


def test_grimoire_implements_grimoire_contract_methods():
    required = _abstract_methods(GrimoireContract)
    implemented = set(_public_callables(Grimoire).keys())
    missing = required - implemented
    assert not missing, f"Grimoire missing: {sorted(missing)}"


def test_vermyth_tools_implements_mcp_server_contract_methods():
    required = _abstract_methods(MCPServerContract)
    implemented = set(_public_callables(VermythTools).keys())
    missing = required - implemented
    assert not missing, f"VermythTools missing: {sorted(missing)}"


@pytest.mark.parametrize("method", sorted(_abstract_methods(GrimoireContract)))
def test_grimoire_method_signatures_compatible(method):
    # Compatible means: can be called with the contract's parameters.
    contract_sig = inspect.signature(getattr(GrimoireContract, method))
    impl_sig = inspect.signature(getattr(Grimoire, method))
    assert all(
        name in impl_sig.parameters
        for name in contract_sig.parameters
        if name != "self"
    ), f"Signature mismatch for {method}: {contract_sig} vs {impl_sig}"

