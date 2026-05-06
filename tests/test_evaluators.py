from __future__ import annotations

from dmf2_agents.artifacts import ArtifactService
from dmf2_agents.domain import ArtifactRecord, StageDefinition
from dmf2_agents.evaluators import StageEvaluator
from dmf2_agents.repository import Repository
from dmf2_agents.storage import Database


def test_stage_evaluator_requires_matching_stage_and_kind() -> None:
    database = Database("sqlite+pysqlite:///:memory:")
    database.create_all()
    repository = Repository(database)
    artifacts = ArtifactService(repository)
    evaluator = StageEvaluator(artifacts)
    stage = StageDefinition(
        id="design",
        name="Design",
        goal="Produce plan",
        assigned_agents=["planner"],
        output_artifacts=["design_note"],
    )

    artifacts.write_artifact(
        ArtifactRecord(
            session_id="s1",
            stage_id="discover",
            author_agent="planner",
            kind="design_note",
            title="Wrong stage",
            content="artifact",
        )
    )

    result = evaluator.evaluate(session_id="s1", stage=stage)

    assert result.passed is False
    assert result.missing_artifacts == ["design_note"]

    artifacts.write_artifact(
        ArtifactRecord(
            session_id="s1",
            stage_id="design",
            author_agent="planner",
            kind="design_note",
            title="Right stage",
            content="artifact",
        )
    )

    result = evaluator.evaluate(session_id="s1", stage=stage)

    assert result.passed is True
    assert result.missing_artifacts == []
