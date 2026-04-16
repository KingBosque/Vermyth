from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from ulid import ULID


class AgentSkill(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    description: str


class AgentCard(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    version: str
    description: str
    skills: list[AgentSkill] = Field(default_factory=list)


class Part(BaseModel):
    model_config = ConfigDict(extra="forbid")

    part_type: Literal["text", "data", "artifact"] = "data"
    content: Any


class Message(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant", "system"] = "user"
    parts: list[Part] = Field(default_factory=list)


class Artifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_id: str = Field(default_factory=lambda: str(ULID()))
    mime_type: str = "application/json"
    content: Any


class Task(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str = Field(default_factory=lambda: str(ULID()))
    skill_id: str
    input: dict[str, Any] = Field(default_factory=dict)
    messages: list[Message] = Field(default_factory=list)


class TaskResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str
    status: Literal["queued", "running", "completed", "failed"]
    artifact: Artifact | None = None
    error: str | None = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

