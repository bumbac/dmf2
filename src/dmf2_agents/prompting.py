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
            "Execution guidance:",
            (
                "If the stage goal references concrete file paths, inspect those files with available read-only tools before deciding. "
                "If you can write files and the stage requires deliverables, prefer creating inspectable checked output files while also persisting artifacts that summarize what you produced."
            ),
            (
                "When using write_file, choose explicit project-relative output paths and then record those paths in a write_artifact or update_progress entry so later stages can inspect them. "
                "Do not mark the stage complete until the expected files or review evidence exist."
            ),
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
