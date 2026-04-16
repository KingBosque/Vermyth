from vermyth.schema import Intent, SemanticProgram


def _program_payload() -> dict:
    return {
        "name": "demo-program",
        "nodes": [
            {
                "node_id": "n1",
                "node_type": "CAST",
                "aspects": ["MIND", "LIGHT"],
                "intent": {
                    "objective": "stabilize signal",
                    "scope": "local",
                    "reversibility": "REVERSIBLE",
                    "side_effect_tolerance": "LOW",
                },
                "successors": ["n2"],
            },
            {
                "node_id": "n2",
                "node_type": "FLUID_CAST",
                "vector": {"components": [0, 0, 0, 1, 0, 1]},
                "intent": {
                    "objective": "refine signal",
                    "scope": "local",
                    "reversibility": "PARTIAL",
                    "side_effect_tolerance": "MEDIUM",
                },
                "successors": [],
            },
        ],
        "entry_node_ids": ["n1"],
        "metadata": {"owner": "tests"},
    }


def test_compile_and_execute_program(make_tools):
    compiled = make_tools.tool_compile_program(_program_payload())
    assert compiled["status"] == "COMPILED"
    execution = make_tools.tool_execute_program(compiled["program_id"])
    assert execution["status"] in {"COMPLETED", "FAILED"}
    assert execution["program_id"] == compiled["program_id"]


def test_program_roundtrip_in_grimoire(tmp_grimoire):
    program = SemanticProgram.model_validate(_program_payload())
    tmp_grimoire.write_program(program)
    got = tmp_grimoire.read_program(program.program_id)
    assert got.program_id == program.program_id
    assert got.name == "demo-program"
