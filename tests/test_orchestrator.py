from __future__ import annotations

from pathlib import Path

from dmf2_agents.agents import AgentRegistry
from dmf2_agents.artifacts import ArtifactService
from dmf2_agents.evaluators import StageEvaluator
from dmf2_agents.events import EventBus
from dmf2_agents.memory import MemoryService
from dmf2_agents.orchestrator import SessionOrchestrator
from dmf2_agents.prompting import PromptBuilder
from dmf2_agents.providers import AgentDecision, ProviderClient, ToolCallDecision
from dmf2_agents.repository import Repository
from dmf2_agents.runner import AgentRunner
from dmf2_agents.skills import SkillRegistry
from dmf2_agents.stages import StageRegistry
from dmf2_agents.storage import Database
from dmf2_agents.tools import PermissionService, ToolRegistry


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


def build_orchestrator(project_root: Path, workflow_path: Path, provider, evaluation_client) -> SessionOrchestrator:
    database = Database("sqlite+pysqlite:///:memory:")
    database.create_all()
    repository = Repository(database)
    memory = MemoryService(repository)
    artifacts = ArtifactService(repository, root=project_root)
    events = EventBus(repository)
    stages = StageRegistry(workflow_path)
    agents = AgentRegistry()
    permission = PermissionService({agent.name: set(agent.allowed_tools) for agent in agents.list()})
    tools = ToolRegistry(
        root=project_root,
        memory=memory,
        artifacts=artifacts,
        skills=SkillRegistry(project_root / "skills"),
        permission=permission,
    )
    runner = AgentRunner(
        memory=memory,
        artifacts=artifacts,
        tools=tools,
        prompt_builder=PromptBuilder(),
        provider=provider,
    )
    evaluator = StageEvaluator(repository=repository, memory=memory, artifacts=artifacts, client=evaluation_client)
    return SessionOrchestrator(
        repository=repository,
        memory=memory,
        artifacts=artifacts,
        events=events,
        stages=stages,
        agents=agents,
        runner=runner,
        evaluator=evaluator,
    )


def test_session_orchestrator_runs_all_stages(project_root: Path) -> None:
    app = build_orchestrator(
        project_root,
        project_root / "examples" / "pipeline.yaml",
        SequenceProvider(
            [
                AgentDecision(
                    response="discover",
                    tool_calls=[ToolCallDecision(tool_name="update_progress", arguments={"message": "discovering", "status": "in_progress"})],
                ),
                AgentDecision(
                    response="design",
                    tool_calls=[ToolCallDecision(tool_name="update_progress", arguments={"message": "designing", "status": "in_progress"})],
                ),
                AgentDecision(
                    response="execute",
                    tool_calls=[ToolCallDecision(tool_name="write_artifact", arguments={"kind": "deliverable", "title": "Output", "content": "done"})],
                ),
                AgentDecision(response="validate", tool_calls=[]),
            ]
        ),
        SequenceEvaluationClient(
            [
                type("EvaluationResult", (), {"passed": True, "reasoning": "ok", "source": "provider"})(),
                type("EvaluationResult", (), {"passed": True, "reasoning": "ok", "source": "provider"})(),
                type("EvaluationResult", (), {"passed": True, "reasoning": "ok", "source": "provider"})(),
                type("EvaluationResult", (), {"passed": True, "reasoning": "ok", "source": "provider"})(),
            ]
        ),
    )
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
    app = build_orchestrator(
        project_root,
        project_root / "examples" / "pipeline.yaml",
        SequenceProvider([AgentDecision(response="first attempt", tool_calls=[]), AgentDecision(response="second attempt", tool_calls=[])]),
        SequenceEvaluationClient(
            [
                type("EvaluationResult", (), {"passed": False, "reasoning": "Need more evidence", "source": "provider"})(),
                type("EvaluationResult", (), {"passed": True, "reasoning": "Goal satisfied", "source": "provider"})(),
                type("EvaluationResult", (), {"passed": True, "reasoning": "Goal satisfied", "source": "provider"})(),
                type("EvaluationResult", (), {"passed": True, "reasoning": "Goal satisfied", "source": "provider"})(),
                type("EvaluationResult", (), {"passed": True, "reasoning": "Goal satisfied", "source": "provider"})(),
            ]
        ),
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
    app = build_orchestrator(
        project_root,
        project_root / "examples" / "pipeline.yaml",
        SequenceProvider([AgentDecision(response="first attempt", tool_calls=[]), AgentDecision(response="second attempt", tool_calls=[])]),
        SequenceEvaluationClient(
            [
                type("EvaluationResult", (), {"passed": False, "reasoning": "Goal not yet satisfied", "source": "provider"})(),
                type("EvaluationResult", (), {"passed": False, "reasoning": "Goal not yet satisfied", "source": "provider"})(),
            ]
        ),
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


def test_orchestrator_uses_workflow_agent_mapping_with_arbitrary_stage_names(project_root: Path) -> None:
    app = build_orchestrator(
        project_root,
        project_root / "tests" / "fixtures" / "arbitrary_stage_names.yaml",
        SequenceProvider(
            [
                AgentDecision(response="scope", tool_calls=[]),
                AgentDecision(response="shape", tool_calls=[]),
                AgentDecision(
                    response="ship",
                    tool_calls=[ToolCallDecision(tool_name="write_artifact", arguments={"kind": "deliverable", "title": "Ship", "content": "artifact"})],
                ),
                AgentDecision(response="inspect", tool_calls=[]),
            ]
        ),
        SequenceEvaluationClient(
            [
                type("EvaluationResult", (), {"passed": True, "reasoning": "ok", "source": "provider"})(),
                type("EvaluationResult", (), {"passed": True, "reasoning": "ok", "source": "provider"})(),
                type("EvaluationResult", (), {"passed": True, "reasoning": "ok", "source": "provider"})(),
                type("EvaluationResult", (), {"passed": True, "reasoning": "ok", "source": "provider"})(),
            ]
        ),
    )

    session_id = app.run("Do the work")
    plan = app.repository.latest_plan(session_id)
    events = app.repository.list_events(session_id)

    assert plan is not None
    assert "1. Scope The Work" in plan.content
    assert "2. Pick An Approach" in plan.content
    assert "3. Build The Thing" in plan.content
    assert "4. Quality Gate" in plan.content
    assert [event.payload.get("stage_id") for event in events if event.event_type == "stage.completed"] == ["intake", "shape", "ship", "inspect"]
