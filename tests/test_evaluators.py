from __future__ import annotations

from dmf2_agents.artifacts import ArtifactService
from dmf2_agents.domain import ArtifactRecord, MessageRecord, ProgressRecord, StageDefinition
from dmf2_agents.evaluators import HumanConfirmationStageEvaluationClient, ProviderStageEvaluationClient, StageEvaluator
from dmf2_agents.memory import MemoryService
from dmf2_agents.providers import StageEvaluationDecision
from dmf2_agents.repository import Repository
from dmf2_agents.storage import Database


class FakeStageEvaluationProvider:
    def __init__(self, decision: StageEvaluationDecision):
        self.decision = decision
        self.calls: list[dict[str, object]] = []

    def evaluate_stage(self, **kwargs) -> StageEvaluationDecision:
        self.calls.append(kwargs)
        return self.decision


def build_evaluator(client) -> tuple[StageEvaluator, Repository, MemoryService, ArtifactService]:
    database = Database("sqlite+pysqlite:///:memory:")
    database.create_all()
    repository = Repository(database)
    memory = MemoryService(repository)
    artifacts = ArtifactService(repository)
    return StageEvaluator(repository=repository, memory=memory, artifacts=artifacts, client=client), repository, memory, artifacts


def test_stage_evaluator_provider_mode_uses_persisted_context() -> None:
    provider = FakeStageEvaluationProvider(
        StageEvaluationDecision(passed=True, reasoning="Goal satisfied from persisted context.")
    )
    evaluator, repository, memory, artifacts = build_evaluator(ProviderStageEvaluationClient(provider))
    stage = StageDefinition(id="design", name="Design", goal="Produce plan", assigned_agents=["planner"])

    repository.add_message(MessageRecord(session_id="s1", role="user", content="Need a plan"))
    repository.add_message(MessageRecord(session_id="s1", role="assistant", content="Drafted the plan"))
    memory.add_progress(
        ProgressRecord(session_id="s1", stage_id="design", agent_name="planner", status="completed", message="Plan drafted")
    )
    artifacts.write_artifact(
        ArtifactRecord(
            session_id="s1",
            stage_id="design",
            author_agent="planner",
            kind="design_note",
            title="Plan",
            content="Implementation plan",
        )
    )

    result = evaluator.evaluate(session_id="s1", stage=stage)

    assert result.passed is True
    assert result.reasoning == "Goal satisfied from persisted context."
    assert result.source == "provider"
    assert len(provider.calls) == 1
    assert any("Drafted the plan" in message.content for message in provider.calls[0]["messages"])
    assert any("Plan drafted" in message.content for message in provider.calls[0]["messages"])
    assert any("Artifact [design_note]" in message.content for message in provider.calls[0]["messages"])


def test_stage_evaluator_human_confirmation_auto_approves() -> None:
    evaluator, _, _, _ = build_evaluator(HumanConfirmationStageEvaluationClient(auto_approve=True))
    stage = StageDefinition(id="validate", name="Validate", goal="Validate outputs", assigned_agents=["reviewer"])

    result = evaluator.evaluate(session_id="s1", stage=stage)

    assert result.passed is True
    assert result.source == "human_confirmation"
    assert "auto-approved" in result.reasoning
