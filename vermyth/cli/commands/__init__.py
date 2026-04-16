"""Command modules split from CLI main parser wiring."""

from vermyth.cli.commands.auto_cast import cmd_auto_cast
from vermyth.cli.commands.cast import cmd_cast, cmd_fluid_cast
from vermyth.cli.commands.causal import (
    cmd_add_cause,
    cmd_causal_graph,
    cmd_evaluate_narrative,
    cmd_infer_cause,
    cmd_predictive_cast,
)
from vermyth.cli.commands.decide import cmd_decide
from vermyth.cli.commands.drift import (
    cmd_backfill_divergence,
    cmd_divergence,
    cmd_divergences,
    cmd_drift_branches,
    cmd_lineage_drift,
    cmd_set_thresholds,
    cmd_thresholds,
)
from vermyth.cli.commands.genesis import (
    cmd_accept_genesis,
    cmd_genesis_proposals,
    cmd_propose_genesis,
    cmd_reject_genesis,
)
from vermyth.cli.commands.programs import (
    cmd_compile_program,
    cmd_execution_status,
    cmd_execute_program,
    cmd_list_programs,
    cmd_program_status,
)
from vermyth.cli.commands.query import (
    cmd_crystallized_sigils,
    cmd_inspect,
    cmd_lineage,
    cmd_query,
    cmd_search,
    cmd_seeds,
)
from vermyth.cli.commands.registry import (
    cmd_aspects,
    cmd_register_aspect,
    cmd_register_sigil,
    cmd_registered_sigils,
)
from vermyth.cli.commands.swarm import (
    cmd_gossip_sync,
    cmd_swarm_cast,
    cmd_swarm_join,
    cmd_swarm_status,
)

__all__ = [
    "cmd_accept_genesis",
    "cmd_add_cause",
    "cmd_auto_cast",
    "cmd_aspects",
    "cmd_cast",
    "cmd_causal_graph",
    "cmd_divergence",
    "cmd_divergences",
    "cmd_drift_branches",
    "cmd_evaluate_narrative",
    "cmd_crystallized_sigils",
    "cmd_decide",
    "cmd_fluid_cast",
    "cmd_backfill_divergence",
    "cmd_genesis_proposals",
    "cmd_inspect",
    "cmd_infer_cause",
    "cmd_lineage",
    "cmd_lineage_drift",
    "cmd_predictive_cast",
    "cmd_propose_genesis",
    "cmd_query",
    "cmd_register_aspect",
    "cmd_register_sigil",
    "cmd_registered_sigils",
    "cmd_reject_genesis",
    "cmd_search",
    "cmd_set_thresholds",
    "cmd_compile_program",
    "cmd_execution_status",
    "cmd_execute_program",
    "cmd_list_programs",
    "cmd_program_status",
    "cmd_seeds",
    "cmd_gossip_sync",
    "cmd_swarm_cast",
    "cmd_swarm_join",
    "cmd_swarm_status",
    "cmd_thresholds",
]

