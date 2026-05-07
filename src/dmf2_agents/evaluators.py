from __future__ import annotations

from typing import Literal, Protocol

from pydantic import BaseModel, Field

from .artifacts import ArtifactService
from .domain import StageDefinition
from .memory import MemoryService
from .providers import ProviderMessage, StageEvaluationDecision, StageEvaluationProvider
from .repository import Repository


class StageEvaluationResult(BaseModel):
    passed: bool
    reasoning: str
    source: Literal["provider", "human_confirmation"]


class StageEvaluationContext(BaseModel):
    stage: StageDefinition
    messages: list[ProviderMessage] = Field(default_factory=list)


class StageEvaluationClient(Protocol):
    def evaluate(self, context: StageEvaluationContext) -> StageEvaluationResult: ...


class ProviderStageEvaluationClient:
    def __init__(self, provider: StageEvaluationProvider):
        self.provider = provider

    def evaluate(self, context: StageEvaluationContext) -> StageEvaluationResult:
        decision = self.provider.evaluate_stage(stage=context.stage, messages=context.messages)
        return StageEvaluationResult(passed=decision.passed, reasoning=decision.reasoning, source="provider")


class HumanConfirmationStageEvaluationClient:
    def __init__(self, auto_approve: bool = True):
        self.auto_approve = auto_approve

    def evaluate(self, context: StageEvaluationContext) -> StageEvaluationResult:
        if self.auto_approve:
            return StageEvaluationResult(
                passed=True,
                reasoning=f"Human confirmation auto-approved stage goal '{context.stage.goal}'.",
                source="human_confirmation",
            )
        return StageEvaluationResult(
            passed=False,
            reasoning=f"Human confirmation is required for stage goal '{context.stage.goal}' but auto-approve is disabled.",
            source="human_confirmation",
        )


class StageEvaluator:
    def __init__(self, repository: Repository, memory: MemoryService, artifacts: ArtifactService, client: StageEvaluationClient):
        self.repository = repository
        self.memory = memory
        self.artifacts = artifacts
        self.client = client

    def evaluate(self, *, session_id: str, stage: StageDefinition) -> StageEvaluationResult:
        stage_messages = [
            ProviderMessage(role=message.role, content=message.content)
            for message in self.repository.list_messages(session_id)
            if message.role in {"assistant", "tool", "user"}
        ]
        stage_progress = [
            ProviderMessage(role="system", content=f"Progress [{item.status}] {item.message}")
            for item in self.memory.list_progress(session_id)
            if item.stage_id == stage.id
        ]
        stage_artifacts = [
            ProviderMessage(role="system", content=f"Artifact [{item.kind}] {item.title}\n{item.content}")
            for item in self.artifacts.list_artifacts(session_id)
            if item.stage_id == stage.id
        ]
        return self.client.evaluate(
            StageEvaluationContext(stage=stage, messages=[*stage_messages, *stage_progress, *stage_artifacts])
        )
