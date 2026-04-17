"""A2A extension URIs and metadata keys for Vermyth-specific semantics."""

from vermyth.arcane.constants import VERMYTH_EXT_SEMANTIC_BUNDLE

# Invoke Vermyth MCP tools via message/send (DataPart or metadata).
VERMYTH_EXT_INVOKE = "vermyth.io/v1/invoke"

# Trust level for inbound parts (multi-agent security).
VERMYTH_EXT_TRUST = "vermyth.io/v1/trust"

# Attach execution receipt id to task/artifact metadata.
VERMYTH_EXT_EXECUTION_RECEIPT = "vermyth.io/v1/execution_receipt"

# Declared protocol extension entries for AgentCard.capabilities.extensions
VERMYTH_EXTENSION_DECLARATIONS = (
    {
        "uri": VERMYTH_EXT_INVOKE,
        "description": "Structured tool invocation: metadata key maps to {skill_id, input, capability_token?}.",
        "required": False,
    },
    {
        "uri": VERMYTH_EXT_TRUST,
        "description": "Trust label for inbound content: low|high (default low).",
        "required": False,
    },
    {
        "uri": VERMYTH_EXT_SEMANTIC_BUNDLE,
        "description": "Named semantic bundle reference {bundle_id, version, params} or same under task.input.semantic_bundle.",
        "required": False,
    },
)
