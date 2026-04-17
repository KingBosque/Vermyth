"""Static validation for semantic programs (compile-time diagnostics)."""

from __future__ import annotations

from dataclasses import dataclass, field

from vermyth.schema import (
    EffectType,
    NodeType,
    Postcondition,
    RollbackStrategy,
    SemanticProgram,
)


@dataclass
class ProgramValidationReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    ok: bool = True

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)
        self.ok = False

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)


def _post_keys(posts: list[Postcondition] | None) -> set[str]:
    if not posts:
        return set()
    return {p.predicate for p in posts}


def validate_program(program: SemanticProgram) -> ProgramValidationReport:
    """Validate graph and node payloads; effect/retry/rollback policy checks."""
    rep = ProgramValidationReport()
    nodes = {n.node_id: n for n in program.nodes}

    for nid, node in nodes.items():
        if node.timeout_ms is not None and node.timeout_ms > 3_600_000:
            rep.add_error(f"node {nid}: timeout_ms exceeds maximum (1h)")
        if node.retry_policy is not None:
            rp = node.retry_policy
            if rp.max_attempts > 20:
                rep.add_error(f"node {nid}: retry_policy.max_attempts too large")
            if rp.backoff_ms > 600_000:
                rep.add_warning(f"node {nid}: very large backoff_ms")
        if node.effects:
            for eff in node.effects:
                et = getattr(eff, "effect_type", None)
                if et is None:
                    rep.add_error(f"node {nid}: effect missing effect_type")
                    continue
                if et in (EffectType.WRITE, EffectType.EXEC, EffectType.NETWORK):
                    if node.rollback in (None, RollbackStrategy.NONE) and node.node_type != NodeType.GATE:
                        rep.add_warning(
                            f"node {nid}: destructive effect {et.value} without rollback strategy"
                        )
        if node.postconditions and len(_post_keys(node.postconditions)) < len(node.postconditions):
            rep.add_warning(f"node {nid}: duplicate postcondition keys")

    # Impossible paths: GATE with no successors but not terminal
    for nid, node in nodes.items():
        if node.node_type == NodeType.GATE and not node.successors:
            rep.add_warning(f"node {nid}: GATE with no successors (dead end)")

    return rep
