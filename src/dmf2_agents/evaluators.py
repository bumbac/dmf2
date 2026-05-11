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
    async def evaluate(self, context: StageEvaluationContext) -> StageEvaluationResult: ...


class ProviderStageEvaluationClient:
    def __init__(self, provider: StageEvaluationProvider):
        self.provider = provider

    async def evaluate(self, context: StageEvaluationContext) -> StageEvaluationResult:
        decision = await self.provider.evaluate_stage(stage=context.stage, messages=context.messages)
        return StageEvaluationResult(passed=decision.passed, reasoning=decision.reasoning, source="provider")


class HumanConfirmationStageEvaluationClient:
    def __init__(self, auto_approve: bool = True):
        self.auto_approve = auto_approve

    async def evaluate(self, context: StageEvaluationContext) -> StageEvaluationResult:
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

    async def evaluate(self, *, session_id: str, stage: StageDefinition) -> StageEvaluationResult:
        if stage.evaluation_mode == "human_confirmation" and hasattr(self.client, "auto_approve"):
            return await HumanConfirmationStageEvaluationClient(auto_approve=self.client.auto_approve).evaluate(
                StageEvaluationContext(stage=stage, messages=[])
            )
        stage_messages = [
            ProviderMessage(role=message.role, content=message.content)
            for message in await self.repository.list_messages(session_id)
            if message.role in {"assistant", "tool", "user"}
        ]
        stage_progress = [
            ProviderMessage(role="system", content=f"Progress [{item.status}] {item.message}")
            for item in await self.memory.list_progress(session_id)
            if item.stage_id == stage.id
        ]
        stage_artifacts = [
            ProviderMessage(role="system", content=f"Artifact [{item.kind}] {item.title}\n{item.content}")
            for item in await self.artifacts.list_artifacts(session_id)
            if item.stage_id == stage.id
        ]
        context = StageEvaluationContext(stage=stage, messages=[*stage_messages, *stage_progress, *stage_artifacts])
        if stage.evaluation_mode == "provider":
            provider = getattr(self.client, "provider", None)
            if provider is not None:
                return await ProviderStageEvaluationClient(provider).evaluate(context)
        return await self.client.evaluate(context)
