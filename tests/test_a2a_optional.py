"""Optional [a2a] extra: SDK-shaped agent card (skipped when a2a-sdk not installed)."""

from __future__ import annotations

import pytest

from vermyth.mcp.tool_definitions import TOOL_DEFINITIONS


def test_build_sdk_agent_card_when_a2a_installed():
    pytest.importorskip("a2a")
    from vermyth.adapters.a2a.sdk_factory import build_sdk_agent_card

    card = build_sdk_agent_card(
        agent_url="http://127.0.0.1:7777/a2a",
        tool_definitions=TOOL_DEFINITIONS,
    )
    assert getattr(card, "name", None)
    assert getattr(card, "skills", None) is not None
