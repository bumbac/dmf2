from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def now_utc() -> datetime:
    return datetime.now(UTC)


class AgentDefinition(BaseModel):
    name: str
    description: str
    mode: Literal["primary", "subagent"] = "primary"
    system_prompt: str
    allowed_tools: list[str] = Field(default_factory=list)
    allowed_skills: list[str] = Field(default_factory=list)
    stage_roles: list[str] = Field(default_factory=list)
    max_iterations: int = 3


class SkillDefinition(BaseModel):
    name: str
    description: str
    content: str
    path: str


class StageDefinition(BaseModel):
    id: str
    name: str
    goal: str
    assigned_agents: list[str]
    completion_conditions: list[str] = Field(default_factory=list)
    max_loops: int = 3
    output_artifacts: list[str] = Field(default_factory=list)


class SessionRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    status: Literal["running", "completed", "failed"] = "running"
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)
    parent_session_id: str | None = None


class MessageRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    session_id: str
    role: Literal["system", "user", "assistant", "tool"]
    agent_name: str | None = None
    content: str
    created_at: datetime = Field(default_factory=now_utc)


class SummaryRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    session_id: str
    content: str
    created_at: datetime = Field(default_factory=now_utc)


class PlanRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    session_id: str
    content: str
    created_at: datetime = Field(default_factory=now_utc)


class ProgressRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    session_id: str
    stage_id: str | None = None
    agent_name: str | None = None
    status: Literal["pending", "in_progress", "completed", "failed"]
    message: str
    created_at: datetime = Field(default_factory=now_utc)


class ArtifactRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    session_id: str
    stage_id: str | None = None
    author_agent: str | None = None
    kind: str
    title: str
    content: str
    version: int = 1
    created_at: datetime = Field(default_factory=now_utc)


class EventRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    session_id: str
    event_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=now_utc)


class TaskResult(BaseModel):
    task_id: str
    status: Literal["completed", "failed"]
    summary: str
    artifact_ids: list[str] = Field(default_factory=list)
    progress_ids: list[str] = Field(default_factory=list)
    recommended_next_action: str | None = None


class AgentOutcome(BaseModel):
    response: str
    stage_complete: bool = False
    should_delegate: bool = False
    delegate_agent: str | None = None
    delegate_prompt: str | None = None
    loaded_skills: list[str] = Field(default_factory=list)
    tool_actions: list[dict[str, Any]] = Field(default_factory=list)
    artifacts: list[dict[str, str]] = Field(default_factory=list)
    progress_updates: list[str] = Field(default_factory=list)
