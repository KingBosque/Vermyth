from __future__ import annotations

import fnmatch
import os
from typing import Any, Callable

from vermyth.adapters.a2a.security import verify_capability_token
from vermyth.adapters.a2a.types import Artifact, Task, TaskResult


class TaskGateway:
    def __init__(
        self,
        *,
        tools: object,
        tool_dispatch: dict[str, Callable[[object, dict[str, Any]], dict[str, Any]]],
    ) -> None:
        self._tools = tools
        self._tool_dispatch = tool_dispatch

    def execute_task(self, payload: dict[str, Any]) -> dict[str, Any]:
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
        handler = self._tool_dispatch.get(task.skill_id)
        if handler is None:
            result = TaskResult(task_id=task.task_id, status="failed", error="unknown_skill")
            return result.model_dump(mode="json")
        try:
            if hasattr(self._tools, "enforce_tool_scope"):
                self._tools.enforce_tool_scope(task.skill_id)
            out = handler(self._tools, task.input)
            result = TaskResult(
                task_id=task.task_id,
                status="completed",
                artifact=Artifact(content=out),
            )
            return result.model_dump(mode="json")
        except Exception as exc:
            result = TaskResult(task_id=task.task_id, status="failed", error=str(exc))
            return result.model_dump(mode="json")

