import json


def test_interpolate_exact_anchor(composition_engine):
    from vermyth.schema import AspectID, SemanticVector

    aspects = frozenset({AspectID.MIND})
    anchor = composition_engine.compose(aspects)
    v = SemanticVector.from_aspects(aspects)
    fluid = composition_engine.interpolate(v, k=3)

    assert fluid.nearest_canonical == anchor.name
    assert fluid.effect_class == anchor.effect_class
    assert 0.0 <= float(fluid.resonance_ceiling) <= 1.0
    assert fluid.semantic_vector.cosine_similarity(v) == 1.0


def test_fluid_cast_sets_provenance(resonance_engine):
    from vermyth.schema import Intent, ReversibilityClass, SemanticVector, SideEffectTolerance

    v = SemanticVector(components=(0.0, 0.0, 0.0, 1.0, 0.0, 0.0))
    intent = Intent(
        objective="probe",
        scope="unit-test",
        reversibility=ReversibilityClass.REVERSIBLE,
        side_effect_tolerance=SideEffectTolerance.HIGH,
    )
    result = resonance_engine.fluid_cast(v, intent)

    assert result.provenance is not None
    assert result.provenance.source == "fluid"
    assert result.sigil.name.startswith("Fluid:")


def test_tool_fluid_cast_persists(make_tools, valid_intent):
    out = make_tools.tool_fluid_cast(
        vector=[0.0, 0.0, 0.0, 1.0, 0.0, 0.0],
        intent=valid_intent,
    )
    assert out["provenance"]["source"] == "fluid"

    inspected = make_tools.tool_inspect(out["cast_id"])
    assert inspected["cast_id"] == out["cast_id"]
    assert inspected["provenance"]["source"] == "fluid"


def test_cli_fluid_cast_outputs(make_cli, capsys):
    make_cli.run(
        [
            "fluid-cast",
            "--vector",
            "0",
            "0",
            "0",
            "1",
            "0",
            "0",
            "--objective",
            "study",
            "--scope",
            "repo",
            "--reversibility",
            "REVERSIBLE",
            "--side-effect-tolerance",
            "HIGH",
        ]
    )
    captured = capsys.readouterr()
    assert "Sigil" in captured.out
    assert "Provenance  fluid" in captured.out

