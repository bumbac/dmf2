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


class SequenceEvaluationClient:
    def __init__(self, results: list[object]):
        self.results = results
        self.index = 0

    def evaluate(self, context):
        if self.index >= len(self.results):
            return self.results[-1]
        result = self.results[self.index]
        self.index += 1
        return result


def test_session_orchestrator_runs_all_stages(project_root: Path) -> None:
    app = build_app(project_root=project_root)
    session_id = app.run("Produce a staged implementation outline")
    assert session_id
    plan = app.repository.latest_plan(session_id)
    messages = app.repository.list_messages(session_id)
    assert any(item.role == "assistant" for item in messages)
    assert any(item.role == "tool" for item in messages)
    events = app.repository.list_events(session_id)
    event_types = [item.event_type for item in events]
    assert plan is not None
    assert "Workflow Plan:" in plan.content
    assert "1. Discover: Understand the request and capture the important problem details." in plan.content
    assert "session.started" in event_types
    assert "stage.completed" in event_types
    assert "session.finished" in event_types


def test_orchestrator_retries_stage_until_provider_evaluation_passes(project_root: Path) -> None:
    app = build_app(project_root=project_root)
    app.runner.provider = SequenceProvider([AgentDecision(response="first attempt", tool_calls=[]), AgentDecision(response="second attempt", tool_calls=[])])
    app.evaluator.client = SequenceEvaluationClient(
        [
            type("EvaluationResult", (), {"passed": False, "reasoning": "Need more evidence", "source": "provider"})(),
            type("EvaluationResult", (), {"passed": True, "reasoning": "Goal satisfied", "source": "provider"})(),
            type("EvaluationResult", (), {"passed": True, "reasoning": "Goal satisfied", "source": "provider"})(),
            type("EvaluationResult", (), {"passed": True, "reasoning": "Goal satisfied", "source": "provider"})(),
            type("EvaluationResult", (), {"passed": True, "reasoning": "Goal satisfied", "source": "provider"})(),
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
    app.evaluator.client = SequenceEvaluationClient(
        [
            type("EvaluationResult", (), {"passed": False, "reasoning": "Goal not yet satisfied", "source": "provider"})(),
            type("EvaluationResult", (), {"passed": False, "reasoning": "Goal not yet satisfied", "source": "provider"})(),
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
    assert halted[0].payload["evaluation_reason"] == "Goal not yet satisfied"
    assert set(entered) == {"discover"}
