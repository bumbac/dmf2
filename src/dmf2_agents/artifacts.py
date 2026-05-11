from __future__ import annotations

from pathlib import Path

from .domain import ArtifactRecord
from .repository import Repository


class ArtifactService:
    def __init__(self, repository: Repository, root: Path | None = None):
        self.repository = repository
        self.root = root or Path.cwd()

    def write_artifact(self, record: ArtifactRecord) -> ArtifactRecord:
        persisted = self.repository.add_artifact(record)
        target = self._artifact_path_for(persisted)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(persisted.content)
        if persisted.file_path != target.as_posix() or persisted.storage_kind != "file":
            persisted.file_path = target.as_posix()
            persisted.storage_kind = "file"
            persisted = self.repository.update_artifact(persisted)
        return persisted

    def list_artifacts(self, session_id: str) -> list[ArtifactRecord]:
        return self.repository.list_artifacts(session_id)

    def _artifact_path_for(self, record: ArtifactRecord) -> Path:
        safe_title = "-".join(record.title.lower().split()) or "artifact"
        return self.root / "runtime" / "artifacts" / record.session_id / f"{record.version:04d}-{record.id}-{safe_title}.md"
