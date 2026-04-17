"""Maps A2A message/send to Vermyth tool dispatch (requires optional a2a-sdk)."""

from __future__ import annotations

import asyncio
import fnmatch
import os
from collections.abc import Callable
from typing import Any
from uuid import uuid4

from vermyth.adapters.a2a.extensions import VERMYTH_EXT_INVOKE, VERMYTH_EXT_SEMANTIC_BUNDLE, VERMYTH_EXT_TRUST
from vermyth.arcane.invoke import expand_task_input
from vermyth.adapters.a2a.security import verify_capability_token

try:
    from a2a.server.agent_execution.agent_executor import AgentExecutor
    from a2a.server.agent_execution.context import RequestContext
    from a2a.server.events.event_queue import EventQueue
    from a2a.types import (
        Artifact,
        DataPart,
        Message,
        Part,
        Role,
        Task,
        TaskState,
        TaskStatus,
        TaskStatusUpdateEvent,
    )
except ImportError as e:
    raise ImportError(
        "Install optional extra: pip install -e .[a2a]"
    ) from e


def _extract_invoke_payload(context: RequestContext) -> dict[str, Any]:
    """Resolve skill_id + input from extension metadata or structured parts only."""
    inv: dict[str, Any] | None = None
    if context.metadata and VERMYTH_EXT_INVOKE in context.metadata:
        inv = context.metadata[VERMYTH_EXT_INVOKE]
    msg = context.message
    if msg and msg.metadata and VERMYTH_EXT_INVOKE in msg.metadata:
        inv = msg.metadata[VERMYTH_EXT_INVOKE]
    if isinstance(inv, dict) and inv.get("skill_id"):
        return inv
    if not msg:
        raise ValueError("message required")
    # Structured DataPart only (instruction/data separation: no raw text → tool args).
    for part in msg.parts:
        root = part.root if hasattr(part, "root") else part
        if getattr(root, "kind", None) == "data" and getattr(root, "data", None):
            data = root.data
            if isinstance(data, dict) and data.get("skill_id"):
                return data
    raise ValueError(
        f"missing structured invocation: set metadata['{VERMYTH_EXT_INVOKE}'] "
        "to {{skill_id, input}} or send a data part with that shape"
    )


def _trust_level(context: RequestContext) -> str:
    for src in (context.metadata, (context.message.metadata if context.message else None)):
        if isinstance(src, dict) and VERMYTH_EXT_TRUST in src:
            v = str(src[VERMYTH_EXT_TRUST]).lower()
            return v if v in ("low", "high") else "low"
    return "low"


class VermythAgentExecutor(AgentExecutor):
    """Executes Vermyth tools and emits A2A Task / status events."""

    def __init__(
        self,
        *,
        tools: object,
        tool_dispatch: dict[str, Callable[[object, dict[str, Any]], dict[str, Any]]],
    ) -> None:
        self._tools = tools
        self._tool_dispatch = tool_dispatch
        self._cancel_events: dict[str, asyncio.Event] = {}

    def _working_update(
        self, task_id: str, context_id: str, state: TaskState
    ) -> TaskStatusUpdateEvent:
        return TaskStatusUpdateEvent(
            task_id=task_id,
            context_id=context_id,
            final=False,
            status=TaskStatus(state=state, message=None, timestamp=None),
        )

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        task_id = context.task_id or ""
        context_id = context.context_id or ""
        if not task_id or not context_id:
            raise ValueError("task_id and context_id are required")

        ev = asyncio.Event()
        self._cancel_events[task_id] = ev

        await event_queue.enqueue_event(
            self._working_update(task_id, context_id, TaskState.working)
        )

        trust = _trust_level(context)
        if trust == "low" and os.environ.get("VERMYTH_DENY_LOW_TRUST_INVOKE", "0") == "1":
            task = Task(
                id=task_id,
                context_id=context_id,
                status=TaskStatus(
                    state=TaskState.rejected,
                    message=None,
                ),
                metadata={"error": "low_trust_invoke_denied"},
            )
            await event_queue.enqueue_event(task)
            self._cancel_events.pop(task_id, None)
            return

        try:
            payload = await asyncio.to_thread(_extract_invoke_payload, context)
            skill_id = str(payload["skill_id"])
            input_obj = payload.get("input")
            if not isinstance(input_obj, dict):
                input_obj = {}
            if context.metadata and VERMYTH_EXT_SEMANTIC_BUNDLE in context.metadata:
                input_obj = {
                    **input_obj,
                    "semantic_bundle": context.metadata[VERMYTH_EXT_SEMANTIC_BUNDLE],
                }
            skill_id, input_obj, arc_prov = await asyncio.to_thread(
                lambda: expand_task_input(
                    skill_id, input_obj, telemetry_surface="a2a"
                )
            )

            requires_capability = bool(
                int((os.environ.get("VERMYTH_REQUIRE_CAPABILITY_TOKENS", "0") or "0"))
            )
            if requires_capability:
                tok = input_obj.get("capability_token")
                if not isinstance(tok, dict):
                    raise ValueError("missing_capability_token")
                token = verify_capability_token(
                    tok,
                    shared_secret=os.environ.get("VERMYTH_CAPABILITY_SECRET"),
                )
                if not fnmatch.fnmatch(skill_id, token.tool_scope):
                    raise ValueError("capability_scope_denied")

            if ev.is_set():
                raise asyncio.CancelledError()

            handler = self._tool_dispatch.get(skill_id)
            if handler is None:
                task = Task(
                    id=task_id,
                    context_id=context_id,
                    status=TaskStatus(state=TaskState.failed, message=None),
                    metadata={"error": "unknown_skill", "skill_id": skill_id},
                )
                await event_queue.enqueue_event(task)
                return

            if hasattr(self._tools, "enforce_tool_scope"):
                self._tools.enforce_tool_scope(skill_id)

            result = await asyncio.to_thread(handler, self._tools, input_obj)

            if ev.is_set():
                raise asyncio.CancelledError()

            artifact = Artifact(
                artifact_id=str(uuid4()),
                name="tool_result",
                parts=[
                    Part(
                        root=DataPart(
                            data={"result": result},
                        )
                    )
                ],
                metadata={
                    "vermyth.io/v1/tool": skill_id,
                },
            )
            meta = self._result_metadata(result)
            if arc_prov:
                meta = {**meta, "vermyth.io/v1/arcane_provenance": arc_prov}
            task = Task(
                id=task_id,
                context_id=context_id,
                status=TaskStatus(state=TaskState.completed, message=None),
                artifacts=[artifact],
                metadata=meta,
            )
            await event_queue.enqueue_event(task)
        except asyncio.CancelledError:
            task = Task(
                id=task_id,
                context_id=context_id,
                status=TaskStatus(state=TaskState.canceled, message=None),
            )
            await event_queue.enqueue_event(task)
        except Exception as exc:
            task = Task(
                id=task_id,
                context_id=context_id,
                status=TaskStatus(state=TaskState.failed, message=None),
                metadata={"error": str(exc)},
            )
            await event_queue.enqueue_event(task)
        finally:
            self._cancel_events.pop(task_id, None)

    def _result_metadata(self, result: dict[str, Any]) -> dict[str, Any]:
        meta: dict[str, Any] = {}
        if isinstance(result, dict):
            dec = result.get("decision") or {}
            if isinstance(dec, dict) and dec.get("cast_id"):
                meta["vermyth.io/v1/cast_id"] = dec["cast_id"]
            ex = result.get("execution") or result.get("program_execution")
            if isinstance(ex, dict) and ex.get("execution_id"):
                meta["vermyth.io/v1/execution_id"] = ex["execution_id"]
        return meta

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        tid = context.task_id
        if tid and tid in self._cancel_events:
            self._cancel_events[tid].set()
