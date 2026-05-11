from __future__ import annotations

from .domain import AgentDefinition, ArtifactRecord, PlanRecord, ProgressRecord, SkillDefinition, StageDefinition, SummaryRecord


PROGRESS_N_LAST_MESSAGES = 6
ARTIFACTS_N_LAST_MESSAGES = 6
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
            (
                "When using write_artifact, always provide a descriptive title. Format artifact content as a readable summary, and if the content is only part of a larger payload, explicitly say it is a chunk. "
                "Artifacts are persisted to runtime storage, so include enough context for a later agent to load the referenced file."
            ),
            "",
            "Session summary:",
            summary.content if summary else "No summary yet.",
            "",
            "Current plan:",
            plan.content if plan else "No plan yet.",
            "",
            "Recent progress:",
            "\n".join(f"- [{item.status}] {item.message}" for item in progress[-PROGRESS_N_LAST_MESSAGES:]) or "None",
            "",
            "Artifacts:",
            "\n\n".join(self._format_artifact(item) for item in artifacts[-ARTIFACTS_N_LAST_MESSAGES:]) or "None",
            "",
            "Loaded skills:",
            "\n\n".join(f"## {skill.name}\n{skill.content}" for skill in skills) or "None",
        ]
        return "\n".join(parts)

    def _format_artifact(self, artifact: ArtifactRecord) -> str:
        content = artifact.content.strip()
        if content and "chunk" not in content.lower():
            content = f"Full payload summary: {content}"
        reference = artifact.file_path or artifact.id
        load_hint = (
            f"Use read_file with path '{artifact.file_path}' to inspect the persisted artifact payload."
            if artifact.file_path
            else f"Use the artifact id '{artifact.id}' from persistence records to locate this artifact."
        )
        return "\n".join(
            [
                f"- Title: {artifact.title}",
                f"  Kind: {artifact.kind}",
                f"  Content: {content or 'No content recorded.'}",
                f"  Reference: {reference}",
                f"  Load hint: {load_hint}",
            ]
        )
