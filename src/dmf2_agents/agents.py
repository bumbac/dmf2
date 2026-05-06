from __future__ import annotations

from .domain import AgentDefinition


class AgentRegistry:
    def __init__(self):
        self._agents = {
            "planner": AgentDefinition(
                name="planner",
                description="Creates plans, summaries, and stage handoffs",
                mode="primary",
                system_prompt="You are a planning agent. Produce explicit plans, progress updates, and stage completion decisions.",
                allowed_tools=["write_artifact", "update_progress", "load_skill", "run_task_agent", "mark_stage_complete"],
                allowed_skills=["planning", "artifact-writing"],
                stage_roles=["discover", "design"],
            ),
            "builder": AgentDefinition(
                name="builder",
                description="Produces deliverables and execution artifacts",
                mode="primary",
                system_prompt="You are an execution agent. Produce deliverables and stage artifacts in a controlled way.",
                allowed_tools=["write_artifact", "update_progress", "load_skill", "run_task_agent", "mark_stage_complete", "read_file", "write_file", "run_command"],
                allowed_skills=["artifact-writing"],
                stage_roles=["execute"],
            ),
            "reviewer": AgentDefinition(
                name="reviewer",
                description="Validates outputs against stage goals",
                mode="subagent",
                system_prompt="You are a reviewer. Check whether stage outputs satisfy the stated goal and report risks.",
                allowed_tools=["write_artifact", "update_progress", "mark_stage_complete"],
                allowed_skills=["code-review"],
                stage_roles=["validate"],
            ),
        }

    def get(self, name: str) -> AgentDefinition | None:
        return self._agents.get(name)

    def list(self) -> list[AgentDefinition]:
        return list(self._agents.values())
