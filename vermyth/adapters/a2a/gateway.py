from __future__ import annotations

import fnmatch
import json
import os
from typing import Any, Callable

from vermyth.adapters.a2a.security import verify_capability_token
from vermyth.adapters.a2a.types import Artifact, Task, TaskResult
from vermyth.arcane.invoke import expand_task_input


class TaskGateway:
    def __init__(
        self,
        *,
        tools: object,
        tool_dispatch: dict[str, Callable[[object, dict[str, Any]], dict[str, Any]]],
        idempotency_store: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        self._tools = tools
        self._tool_dispatch = tool_dispatch
        self._idempotency_store = idempotency_store

    def execute_task(
        self,
        payload: dict[str, Any],
        *,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        if self._idempotency_store is not None and idempotency_key:
            composite = f"{idempotency_key}:{json.dumps(payload, sort_keys=True, default=str)}"
            if composite in self._idempotency_store:
                return dict(self._idempotency_store[composite])
        task = Task.model_validate(payload)
        requires_capability = bool(
            int((os.environ.get("VERMYTH_REQUIRE_CAPABILITY_TOKENS", "0") or "0"))
        )
        if requires_capability:
            token_payload = task.input.get("capability_token")
            if not isinstance(token_payload, dict):
                result = TaskResult(
                    task_id=task.task_id,
                    status="failed",
                    error="missing_capability_token",
                )
                return result.model_dump(mode="json")
            try:
                token = verify_capability_token(
                    token_payload,
                    shared_secret=os.environ.get("VERMYTH_CAPABILITY_SECRET"),
                )
            except Exception as exc:
                result = TaskResult(
                    task_id=task.task_id,
                    status="failed",
                    error=str(exc),
                )
                return result.model_dump(mode="json")
            if not fnmatch.fnmatch(task.skill_id, token.tool_scope):
                result = TaskResult(
                    task_id=task.task_id,
                    status="failed",
                    error="capability_scope_denied",
                )
                return result.model_dump(mode="json")
        skill_id, inp, arc_prov = expand_task_input(
            task.skill_id, dict(task.input), telemetry_surface="a2a"
        )
        handler = self._tool_dispatch.get(skill_id)
        if handler is None:
            result = TaskResult(task_id=task.task_id, status="failed", error="unknown_skill")
            return result.model_dump(mode="json")
        try:
            if hasattr(self._tools, "enforce_tool_scope"):
                self._tools.enforce_tool_scope(skill_id)
            out = handler(self._tools, inp)
            if arc_prov is not None:
                out = {"result": out, "arcane_provenance": arc_prov}
            result = TaskResult(
                task_id=task.task_id,
                status="completed",
                artifact=Artifact(content=out),
            )
            dumped = result.model_dump(mode="json")
            if self._idempotency_store is not None and idempotency_key:
                ck = f"{idempotency_key}:{json.dumps(payload, sort_keys=True, default=str)}"
                self._idempotency_store[ck] = dumped
            return dumped
        except Exception as exc:
            result = TaskResult(task_id=task.task_id, status="failed", error=str(exc))
            return result.model_dump(mode="json")

