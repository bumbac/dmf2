from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from .artifacts import ArtifactService
from .domain import ArtifactRecord, ProgressRecord, StageDefinition, TaskResult
from .memory import MemoryService
from .skills import SkillRegistry


class TaskExecutor:
    def run_subagent(
        self,
        *,
        parent_session_id: str,
        stage: StageDefinition,
        subagent_name: str,
        prompt: str,
    ) -> TaskResult:
        raise NotImplementedError


class ToolContext(BaseModel):
    session_id: str
    stage_id: str | None = None
    agent_name: str
    stage: StageDefinition | None = None


class ToolDefinition(BaseModel):
    name: str
    description: str


class PermissionService:
    def __init__(self, agent_tools: dict[str, set[str]]):
        self.agent_tools = agent_tools

    def ensure(self, agent_name: str, tool_name: str) -> None:
        allowed = self.agent_tools.get(agent_name, set())
        if tool_name not in allowed:
            raise PermissionError(f"agent '{agent_name}' cannot use tool '{tool_name}'")


class ToolRegistry:
    def __init__(
        self,
        root: Path,
        memory: MemoryService,
        artifacts: ArtifactService,
        skills: SkillRegistry,
        permission: PermissionService,
        task_executor: TaskExecutor | None = None,
    ):
        self.root = root
        self.memory = memory
        self.artifacts = artifacts
        self.skills = skills
        self.permission = permission
        self.task_executor = task_executor

    def discover_for_agent(self, agent_name: str) -> list[ToolDefinition]:
        return [ToolDefinition(name=name, description=desc) for name, desc in self._descriptions().items() if name in self.permission.agent_tools.get(agent_name, set())]

    def run(self, agent_name: str, tool_name: str, ctx: ToolContext, **kwargs: Any) -> Any:
        self.permission.ensure(agent_name, tool_name)
        handler = getattr(self, f"tool_{tool_name}")
        return handler(ctx, **kwargs)

    def _descriptions(self) -> dict[str, str]:
        return {
            "read_file": "Read a text file from the project root.",
            "write_file": "Write a text file under the project root.",
            "run_command": "Run a shell command in the project root.",
            "write_artifact": "Persist a stage artifact.",
            "update_progress": "Persist a progress entry.",
            "load_skill": "Load a reusable SKILL.md bundle.",
            "run_task_agent": "Run a subagent in an independent task session.",
        }

    def tool_read_file(self, ctx: ToolContext, path: str) -> str:
        return (self.root / path).read_text()

    def tool_write_file(self, ctx: ToolContext, path: str, content: str) -> str:
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
        return str(target)

    def tool_run_command(self, ctx: ToolContext, command: list[str]) -> dict[str, Any]:
        proc = subprocess.run(command, cwd=self.root, capture_output=True, text=True, check=False)
        return {"returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}

    def tool_write_artifact(
        self,
        ctx: ToolContext,
        kind: str,
        title: str,
        content: str,
        **_: Any,
    ) -> str:
        record = self.artifacts.write_artifact(
            ArtifactRecord(
                session_id=ctx.session_id,
                stage_id=ctx.stage_id,
                author_agent=ctx.agent_name,
                kind=kind,
                title=title,
                content=content,
            )
        )
        return record.id

    def tool_update_progress(self, ctx: ToolContext, message: str, status: str = "in_progress") -> str:
        record = self.memory.add_progress(
            ProgressRecord(
                session_id=ctx.session_id,
                stage_id=ctx.stage_id,
                agent_name=ctx.agent_name,
                status=status,
                message=message,
            )
        )
        return record.id

    def tool_load_skill(self, ctx: ToolContext, skill_name: str) -> str:
        skill = self.skills.get(skill_name)
        if skill is None:
            raise ValueError(f"unknown skill: {skill_name}")
        return skill.content

    def tool_run_task_agent(self, ctx: ToolContext, subagent_name: str, prompt: str) -> TaskResult:
        if self.task_executor is None:
            raise RuntimeError("task executor is not configured")
        if ctx.stage is None:
            raise ValueError("task execution requires the current stage definition")
        return self.task_executor.run_subagent(
            parent_session_id=ctx.session_id,
            stage=ctx.stage,
            subagent_name=subagent_name,
            prompt=prompt,
        )
