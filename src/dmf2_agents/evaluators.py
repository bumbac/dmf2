from __future__ import annotations

from pydantic import BaseModel, Field

from .artifacts import ArtifactService
from .domain import StageDefinition


class StageEvaluationResult(BaseModel):
    passed: bool
    missing_artifacts: list[str] = Field(default_factory=list)


class StageEvaluator:
    def __init__(self, artifacts: ArtifactService):
        self.artifacts = artifacts

    def evaluate(self, *, session_id: str, stage: StageDefinition) -> StageEvaluationResult:
        if not stage.output_artifacts:
            return StageEvaluationResult(passed=True)
        stage_artifacts = {
            artifact.kind
            for artifact in self.artifacts.list_artifacts(session_id)
            if artifact.stage_id == stage.id
        }
        missing_artifacts = [artifact_kind for artifact_kind in stage.output_artifacts if artifact_kind not in stage_artifacts]
        return StageEvaluationResult(passed=not missing_artifacts, missing_artifacts=missing_artifacts)
