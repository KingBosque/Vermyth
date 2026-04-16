from __future__ import annotations

from tempfile import TemporaryDirectory

import pytest

from vermyth.grimoire.store import Grimoire
from vermyth.registry import AspectRegistry
from vermyth.schema import (
    DivergenceReport,
    DivergenceThresholds_DEFAULT,
    RegisteredAspect,
    SemanticVector,
)


def test_semantic_vector_requires_explicit_basis_upgrade() -> None:
    left = SemanticVector(components=(1.0, 0.0, 0.0, 0.0, 0.0, 0.0), basis_version=0)
    right = SemanticVector(components=(1.0, 0.0, 0.0, 0.0, 0.0, 0.0), basis_version=1)

    with pytest.raises(ValueError):
        left.cosine_similarity(right)

    upgraded = left.upsample_to(1, target_dim=6)
    assert upgraded.basis_version == 1
    assert upgraded.cosine_similarity(right) == pytest.approx(1.0)


def test_divergence_report_notes_cross_basis_comparison() -> None:
    parent = SemanticVector(components=(1.0, 0.0, 0.0, 0.0, 0.0, 0.0), basis_version=0)
    child = SemanticVector(
        components=(1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
        basis_version=1,
    )
    report = DivergenceReport.classify(
        cast_id="c",
        parent_cast_id="p",
        parent_vector=parent,
        child_vector=child,
        thresholds=DivergenceThresholds_DEFAULT,
    )
    assert report.basis_note is not None
    assert "upsampled" in report.basis_note


def test_grimoire_tracks_basis_versions_for_registered_aspects() -> None:
    AspectRegistry.reset()
    registry = AspectRegistry.get()
    with TemporaryDirectory() as td:
        grimoire = Grimoire(db_path=f"{td}/basis.db")
        latest = grimoire.read_latest_basis_version()
        assert latest.version == 0

        aspect = RegisteredAspect(
            name="ECHO",
            polarity=1,
            entropy_coefficient=0.4,
            symbol="✧",
        )
        registry.register(aspect)
        grimoire.write_registered_aspect(aspect, ordinal=6)

        latest = grimoire.read_latest_basis_version()
        assert latest.version == 1
        assert latest.dimensionality == 7
        assert latest.aspect_order[-1] == "ECHO"
        grimoire._conn.close()
    AspectRegistry.reset()

