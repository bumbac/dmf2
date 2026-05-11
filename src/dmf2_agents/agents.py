from __future__ import annotations

from .domain import AgentDefinition


class AgentRegistry:
    def __init__(self):
        self._agents = {
            "planner": AgentDefinition(
                name="planner",
                description="Creates plans, summaries, and stage handoffs",
                mode="primary",
                system_prompt=(
                    "You are a planning agent. Produce explicit plans, progress updates, and stage completion decisions. "
                    "When stage goals reference concrete files, inspect them with read-only tools before concluding."
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
                system_prompt="You are an execution agent. Produce deliverables and stage artifacts in a controlled way.",
                allowed_tools=["write_artifact", "update_progress", "load_skill", "run_task_agent", "read_file", "write_file", "run_command"],
                allowed_skills=["artifact-writing"],
            ),
            "reviewer": AgentDefinition(
                name="reviewer",
                description="Validates outputs against stage goals",
                mode="subagent",
                system_prompt=(
                    "You are a reviewer. Check whether stage outputs satisfy the stated goal and report risks. "
                    "Inspect produced files directly when they are available."
                ),
                allowed_tools=["write_artifact", "update_progress", "read_file"],
                allowed_skills=["code-review"],
            ),
        }

    def get(self, name: str) -> AgentDefinition | None:
        return self._agents.get(name)

    def list(self) -> list[AgentDefinition]:
        return list(self._agents.values())
