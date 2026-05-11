from __future__ import annotations

from .domain import AgentDefinition


class AgentRegistry:
    def __init__(self):
        self._agents = {
            "planner": AgentDefinition(
                name="planner",
                description="Produces read-only analysis, plans, and stage handoffs",
                mode="primary",
                system_prompt=(
                    "You are a planning agent operating in plan mode. You must remain read-only except for plan and analysis artifacts. "
                    "Inspect the codebase, gather evidence with read-only tools, produce concise implementation plans, and surface open questions before execution."
                ),
                allowed_tools=[
                    "write_artifact",
                    "update_progress",
                    "load_skill",
                    "run_task_agent",
                    "read_file",
                    "run_command",
                ],
                allowed_skills=["planning", "artifact-writing"],
            ),
            "builder": AgentDefinition(
                name="builder",
                description="Produces deliverables and execution artifacts",
                mode="primary",
                system_prompt=(
                    "You are an execution agent operating in build mode. You may inspect, modify, create, and validate files and run commands as needed to satisfy the stage goal. "
                    "Prefer small correct changes, keep outputs inspectable, and record what you changed and why through progress updates and artifacts."
                ),
                allowed_tools=["write_artifact", "update_progress", "load_skill", "run_task_agent", "read_file", "write_file", "run_command"],
                allowed_skills=["artifact-writing"],
            ),
            "reviewer": AgentDefinition(
                name="reviewer",
                description="Validates outputs against stage goals",
                mode="subagent",
                system_prompt=(
                    "You are a reviewer operating in validation mode. Inspect produced files, artifacts, progress, and command output to determine whether the stage goal is actually satisfied. "
                    "You may read files and run inspection commands, but you must not write or modify files. Report concrete findings, risks, and missing evidence."
                ),
                allowed_tools=["write_artifact", "update_progress", "read_file", "run_command"],
                allowed_skills=["code-review"],
            ),
        }

    def get(self, name: str) -> AgentDefinition | None:
        return self._agents.get(name)

    def list(self) -> list[AgentDefinition]:
        return list(self._agents.values())
