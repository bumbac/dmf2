from __future__ import annotations

from dmf2_agents.agents import AgentRegistry
from dmf2_agents.domain import ArtifactRecord, PlanRecord, ProgressRecord, StageDefinition, SummaryRecord
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
        artifacts=[ArtifactRecord(session_id="s1", kind="note", title="Note", content="artifact")],
        skills=[skill] if skill else [],
    )
    assert "summary" in prompt
    assert "plan" in prompt
    assert "working" in prompt
    assert "Note" in prompt
