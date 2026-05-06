from __future__ import annotations

from .domain import AgentDefinition, ArtifactRecord, PlanRecord, ProgressRecord, SkillDefinition, StageDefinition, SummaryRecord


class PromptBuilder:
    def build(
        self,
        *,
        agent: AgentDefinition,
        stage: StageDefinition,
        summary: SummaryRecord | None,
        plan: PlanRecord | None,
        progress: list[ProgressRecord],
        artifacts: list[ArtifactRecord],
        skills: list[SkillDefinition],
    ) -> str:
        parts = [
            f"Agent: {agent.name}",
            f"Role: {agent.description}",
            f"Stage: {stage.name}",
            f"Stage goal: {stage.goal}",
            f"System prompt: {agent.system_prompt}",
            "",
            "Session summary:",
            summary.content if summary else "No summary yet.",
            "",
            "Current plan:",
            plan.content if plan else "No plan yet.",
            "",
            "Recent progress:",
            "\n".join(f"- [{item.status}] {item.message}" for item in progress[-6:]) or "None",
            "",
            "Artifacts:",
            "\n".join(f"- {item.kind}: {item.title}" for item in artifacts[-6:]) or "None",
            "",
            "Loaded skills:",
            "\n\n".join(f"## {skill.name}\n{skill.content}" for skill in skills) or "None",
        ]
        return "\n".join(parts)
