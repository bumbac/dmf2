from __future__ import annotations

from .agents import AgentRegistry
from .artifacts import ArtifactService
from .domain import MessageRecord, SessionRecord, StageDefinition, TaskResult
from .memory import MemoryService
from .repository import Repository
from .runner import AgentRunner


class TaskService:
    def __init__(
        self,
        repository: Repository,
        memory: MemoryService,
        artifacts: ArtifactService,
        agents: AgentRegistry,
        runner: AgentRunner,
    ):
        self.repository = repository
        self.memory = memory
        self.artifacts = artifacts
        self.agents = agents
        self.runner = runner

    def run_subagent(
        self,
        *,
        parent_session_id: str,
        stage: StageDefinition,
        subagent_name: str,
        prompt: str,
    ) -> TaskResult:
        agent = self.agents.get(subagent_name)
        if agent is None:
            raise ValueError(f"unknown subagent: {subagent_name}")
        child = self.repository.create_session(
            SessionRecord(
                title=f"Task: {subagent_name} for {stage.id}",
                parent_session_id=parent_session_id,
            )
        )
        self.memory.append_message(MessageRecord(session_id=child.id, role="user", content=prompt))
        outcome = self.runner.run(session_id=child.id, stage=stage, agent=agent, user_input=prompt)
        summary = self.memory.update_summary(child.id)
        self.repository.update_session_status(child.id, "completed")
        return TaskResult(
            task_id=child.id,
            status="completed",
            summary=summary.content,
            artifact_ids=[artifact["id"] for artifact in outcome.artifacts],
            recommended_next_action="Continue current stage with the child session summary and artifacts in context.",
        )
