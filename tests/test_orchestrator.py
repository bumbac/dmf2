from __future__ import annotations

from pathlib import Path

from dmf2_agents.bootstrap import build_app
from dmf2_agents.providers import AgentDecision, ProviderClient, ToolCallDecision


class SequenceProvider(ProviderClient):
    def __init__(self, decisions: list[AgentDecision]):
        self.decisions = decisions
        self.index = 0

    def decide(self, **kwargs) -> AgentDecision:
        if self.index >= len(self.decisions):
            return self.decisions[-1]
        decision = self.decisions[self.index]
        self.index += 1
        return decision


def test_session_orchestrator_runs_all_stages(project_root: Path) -> None:
    app = build_app(project_root=project_root)
    session_id = app.run("Produce a staged implementation outline")
    assert session_id
    messages = app.repository.list_messages(session_id)
    assert any(item.role == "assistant" for item in messages)
    assert any(item.role == "tool" for item in messages)
    events = app.repository.list_events(session_id)
    event_types = [item.event_type for item in events]
    assert "session.started" in event_types
    assert "stage.completed" in event_types
    assert "session.finished" in event_types


def test_orchestrator_retries_stage_until_required_artifact_exists(project_root: Path) -> None:
    app = build_app(project_root=project_root)
    app.runner.provider = SequenceProvider(
        [
            AgentDecision(response="first attempt", tool_calls=[]),
            AgentDecision(
                response="second attempt",
                tool_calls=[
                    ToolCallDecision(
                        tool_name="write_artifact",
                        arguments={"kind": "discover_note", "title": "Discover", "content": "artifact body"},
                    )
                ],
            ),
            AgentDecision(response="discover finalized", mark_stage_complete=True, tool_calls=[]),
            AgentDecision(
                response="design",
                tool_calls=[
                    ToolCallDecision(
                        tool_name="write_artifact",
                        arguments={"kind": "design_note", "title": "Design", "content": "artifact body"},
                    )
                ],
            ),
            AgentDecision(response="design finalized", mark_stage_complete=True, tool_calls=[]),
            AgentDecision(
                response="execute",
                tool_calls=[
                    ToolCallDecision(
                        tool_name="write_artifact",
                        arguments={"kind": "execute_note", "title": "Execute", "content": "artifact body"},
                    )
                ],
            ),
            AgentDecision(response="execute finalized", mark_stage_complete=True, tool_calls=[]),
            AgentDecision(
                response="validate",
                tool_calls=[
                    ToolCallDecision(
                        tool_name="write_artifact",
                        arguments={"kind": "validate_note", "title": "Validate", "content": "artifact body"},
                    )
                ],
            ),
            AgentDecision(response="validate finalized", mark_stage_complete=True, tool_calls=[]),
        ]
    )

    session_id = app.run("Produce a staged implementation outline")

    events = app.repository.list_events(session_id)
    event_types = [item.event_type for item in events]
    stage_progress = [item for item in events if item.event_type == "stage.progressed" and item.payload.get("stage_id") == "discover"]
    session = app.repository.get_session(session_id)

    assert session is not None
    assert session.status == "completed"
    assert len(stage_progress) == 2
    assert "stage.retry_scheduled" in event_types


def test_orchestrator_halts_when_stage_exceeds_max_loops(project_root: Path) -> None:
    app = build_app(project_root=project_root)
    app.runner.provider = SequenceProvider(
        [
            AgentDecision(response="first attempt", tool_calls=[]),
            AgentDecision(response="second attempt", tool_calls=[]),
        ]
    )

    session_id = app.run("Produce a staged implementation outline")

    session = app.repository.get_session(session_id)
    assert session is not None
    assert session.status == "failed"
    events = app.repository.list_events(session_id)
    event_types = [item.event_type for item in events]
    halted = [item for item in events if item.event_type == "stage.halted"]
    entered = [item.payload.get("stage_id") for item in events if item.event_type == "stage.entered"]

    assert "stage.halted" in event_types
    assert len(halted) == 1
    assert halted[0].payload["stage_id"] == "discover"
    assert halted[0].payload["attempt"] == 2
    assert set(entered) == {"discover"}
