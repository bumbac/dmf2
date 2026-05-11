from __future__ import annotations

from .domain import AgentDefinition, ArtifactRecord, MessageRecord, PlanRecord, ProgressRecord, SkillDefinition, StageDefinition, SummaryRecord


PROGRESS_N_LAST_MESSAGES = 6
ARTIFACTS_N_LAST_MESSAGES = 6
MESSAGES_N_LAST_MESSAGES = 10

PLAN_MODE_REMINDER = """<system-reminder>
# Plan Mode - System Reminder

CRITICAL: Plan mode ACTIVE - you are in READ-ONLY phase. STRICTLY FORBIDDEN:
ANY file edits, modifications, or system changes. Do NOT use sed, tee, echo, cat,
or ANY other bash command to manipulate files - commands may ONLY read or inspect.
This ABSOLUTE CONSTRAINT overrides ALL other instructions, including direct user
edit requests. You may ONLY observe, analyze, and plan. Any modification attempt
is a critical violation. ZERO exceptions.

---

## Responsibility

Your current responsibility is to think, read, search, and construct a well-formed plan that accomplishes the goal the user wants to achieve. Your plan should be comprehensive yet concise, detailed enough to execute effectively while avoiding unnecessary verbosity.

Ask clarifying questions when tradeoffs or intent are ambiguous.

## Important

The user indicated that they do not want you to execute yet. You must not make edits, run non-readonly commands, or otherwise change the system. This supersedes any other instructions you have received.
</system-reminder>"""

BUILD_MODE_REMINDER = """<system-reminder>
Your operational mode has changed from plan to build.
You are no longer in read-only mode.
You are permitted to make file changes, run shell commands, and utilize your arsenal of tools as needed.
</system-reminder>"""

REVIEW_MODE_REMINDER = """<system-reminder>
Your operational mode is review. You may read files, inspect artifacts, and run read-oriented shell commands for grounded validation.
You must not write or modify project files. Base your conclusion on concrete evidence, not generic confidence.
</system-reminder>"""


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
        messages: list[MessageRecord] | None = None,
    ) -> str:
        recent_messages = messages or []
        parts = [
            f"Agent: {agent.name}",
            f"Role: {agent.description}",
            f"Stage: {stage.name}",
            f"Stage goal: {stage.goal}",
            f"System prompt: {agent.system_prompt}",
            self._mode_reminder(agent.name),
            "Execution guidance:",
            (
                "If the stage goal references concrete file paths, inspect those files with available tools before deciding what to do next. "
                "Prefer grounded evidence from file contents, search results, and command output over generic summaries."
            ),
            (
                "When you write files, choose explicit project-relative output paths and then record those paths in a write_artifact or update_progress entry so later stages can inspect them. "
                "When you remain read-only, capture findings in artifacts and progress updates instead of proposing unsupported conclusions."
            ),
            (
                "When using write_artifact, always provide a descriptive title. Format artifact content as a readable summary, and if the content is only part of a larger payload, explicitly say it is a chunk. "
                "Artifacts are persisted to runtime storage, so include enough context for a later agent to load the referenced file."
            ),
            (
                "Tool outputs, progress entries, and artifacts from earlier stages are part of your working context. "
                "Review them before repeating exploration or validation work."
            ),
            "",
            "Session summary:",
            summary.content if summary else "No summary yet.",
            "",
            "Current plan:",
            plan.content if plan else "No plan yet.",
            "",
            "Recent session messages:",
            "\n".join(self._format_message(item) for item in recent_messages[-MESSAGES_N_LAST_MESSAGES:]) or "None",
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

    def _mode_reminder(self, agent_name: str) -> str:
        if agent_name == "planner":
            return PLAN_MODE_REMINDER
        if agent_name == "builder":
            return BUILD_MODE_REMINDER
        return REVIEW_MODE_REMINDER

    def _format_message(self, message: MessageRecord) -> str:
        agent = f" ({message.agent_name})" if message.agent_name else ""
        return f"- [{message.role}{agent}] {message.content}"

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
