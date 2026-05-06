from __future__ import annotations

from .domain import ArtifactRecord
from .repository import Repository


class ArtifactService:
    def __init__(self, repository: Repository):
        self.repository = repository

    def write_artifact(self, record: ArtifactRecord) -> ArtifactRecord:
        return self.repository.add_artifact(record)

    def list_artifacts(self, session_id: str) -> list[ArtifactRecord]:
        return self.repository.list_artifacts(session_id)
