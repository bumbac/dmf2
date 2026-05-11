from __future__ import annotations

from dmf2_agents.agents import AgentRegistry
from dmf2_agents.domain import ArtifactRecord, MessageRecord, PlanRecord, ProgressRecord, StageDefinition, SummaryRecord
from dmf2_agents.prompting import PromptBuilder
from dmf2_agents.skills import SkillRegistry


def test_prompt_builder_includes_core_context(project_root) -> None:
    builder = PromptBuilder()
    agent = AgentRegistry().get("planner")
    assert agent is not None
    skill = SkillRegistry(project_root / "skills").get("planning")
    prompt = builder.build(
        agent=agent,
        stage=StageDefinition(id="discover", name="Discover", goal="Understand request", assigned_agents=["planner"]),
        summary=SummaryRecord(session_id="s1", content="summary"),
        plan=PlanRecord(session_id="s1", content="plan"),
        progress=[ProgressRecord(session_id="s1", status="in_progress", message="working")],
        artifacts=[
            ArtifactRecord(
                session_id="s1",
                kind="note",
                title="Note",
                content="This is a chunk describing the generated artifact output.",
                storage_kind="file",
                file_path="runtime/artifacts/s1/0001-note.md",
            )
        ],
        skills=[skill] if skill else [],
        messages=[MessageRecord(session_id="s1", role="tool", agent_name="planner", content="Stage 'discover' tool 'read_file' result: content")],
    )
    assert "summary" in prompt
    assert "plan" in prompt
    assert "working" in prompt
    assert "Title: Note" in prompt
    assert "This is a chunk describing the generated artifact output." in prompt
    assert "runtime/artifacts/s1/0001-note.md" in prompt
    assert "Use read_file" in prompt
    assert "Plan Mode - System Reminder" in prompt
    assert "Recent session messages:" in prompt
    assert "Stage 'discover' tool 'read_file' result: content" in prompt
