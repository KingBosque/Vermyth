from __future__ import annotations

from typing import TYPE_CHECKING, Any

from vermyth.schema import ProgramExecution, SemanticProgram

if TYPE_CHECKING:
    from vermyth.mcp.tools.facade import VermythTools

TOOLS = [{'name': 'compile_program',
  'description': 'Validate and compile a semantic program graph.',
  'inputSchema': {'type': 'object',
                  'properties': {'program': {'type': 'object'}},
                  'required': ['program']}},
 {'name': 'execute_program',
  'description': 'Execute a compiled semantic program by id.',
  'inputSchema': {'type': 'object',
                  'properties': {'program_id': {'type': 'string'}},
                  'required': ['program_id']}},
 {'name': 'execution_status',
  'description': 'Read a semantic program execution by id.',
  'inputSchema': {'type': 'object',
                  'properties': {'execution_id': {'type': 'string'}},
                  'required': ['execution_id']}},
 {'name': 'list_programs',
  'description': 'List stored semantic programs.',
  'inputSchema': {'type': 'object', 'properties': {'limit': {'type': 'integer'}}, 'required': []}},
 {'name': 'program_status',
  'description': 'Read semantic program metadata by id.',
  'inputSchema': {'type': 'object',
                  'properties': {'program_id': {'type': 'string'}},
                  'required': ['program_id']}}]



def program_to_dict(program: SemanticProgram) -> dict[str, Any]:
    return {
        "program_id": program.program_id,
        "name": program.name,
        "status": program.status.value,
        "nodes": [n.model_dump(mode="json") for n in program.nodes],
        "entry_node_ids": list(program.entry_node_ids),
        "metadata": dict(program.metadata),
        "created_at": program.created_at.isoformat(),
        "updated_at": program.updated_at.isoformat(),
    }


def execution_to_dict(execution: ProgramExecution) -> dict[str, Any]:
    return {
        "execution_id": execution.execution_id,
        "program_id": execution.program_id,
        "status": execution.status.value,
        "node_results": dict(execution.node_results),
        "started_at": execution.started_at.isoformat(),
        "completed_at": (
            execution.completed_at.isoformat() if execution.completed_at is not None else None
        ),
        "branch_id": execution.branch_id,
    }


def tool_compile_program(tools: "VermythTools", payload: dict[str, Any]) -> dict[str, Any]:
    program = SemanticProgram.model_validate(payload)
    compiled = tools._engine.compile_program(program)
    tools._grimoire.write_program(compiled)
    return program_to_dict(compiled)


def tool_execute_program(tools: "VermythTools", program_id: str) -> dict[str, Any]:
    program = tools._grimoire.read_program(program_id)
    execution = tools._engine.execute_program(program)
    tools._grimoire.write_execution(execution)
    return execution_to_dict(execution)


def tool_program_status(tools: "VermythTools", program_id: str) -> dict[str, Any]:
    program = tools._grimoire.read_program(program_id)
    return program_to_dict(program)


def tool_list_programs(tools: "VermythTools", limit: int = 50) -> list[dict[str, Any]]:
    rows = tools._grimoire.query_programs(limit=int(limit))
    return [program_to_dict(p) for p in rows]


def tool_execution_status(tools: "VermythTools", execution_id: str) -> dict[str, Any]:
    execution = tools._grimoire.read_execution(execution_id)
    return execution_to_dict(execution)


def dispatch_compile_program(
    tools: "VermythTools", arguments: dict[str, Any]
) -> dict[str, Any]:
    return tool_compile_program(tools, arguments.get("program", {}))


def dispatch_execute_program(
    tools: "VermythTools", arguments: dict[str, Any]
) -> dict[str, Any]:
    return tool_execute_program(tools, program_id=arguments.get("program_id", ""))


def dispatch_program_status(
    tools: "VermythTools", arguments: dict[str, Any]
) -> dict[str, Any]:
    return tool_program_status(tools, program_id=arguments.get("program_id", ""))


def dispatch_list_programs(
    tools: "VermythTools", arguments: dict[str, Any]
) -> list[dict[str, Any]]:
    return tool_list_programs(tools, limit=int(arguments.get("limit", 50)))


def dispatch_execution_status(
    tools: "VermythTools", arguments: dict[str, Any]
) -> dict[str, Any]:
    return tool_execution_status(tools, execution_id=arguments.get("execution_id", ""))


DISPATCH = {
    "compile_program": dispatch_compile_program,
    "execute_program": dispatch_execute_program,
    "execution_status": dispatch_execution_status,
    "list_programs": dispatch_list_programs,
    "program_status": dispatch_program_status,
}
