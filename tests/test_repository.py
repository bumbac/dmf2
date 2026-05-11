from __future__ import annotations

from dmf2_agents.domain import ArtifactRecord, SessionRecord
from dmf2_agents.repository import Repository
from dmf2_agents.storage import Database


def test_artifact_versions_increment() -> None:
    database = Database("sqlite+pysqlite:///:memory:")
    database.create_all()
    repo = Repository(database)
    session = repo.create_session(SessionRecord(title="t"))
    first = repo.add_artifact(ArtifactRecord(session_id=session.id, kind="report", title="A", content="one"))
    second = repo.add_artifact(ArtifactRecord(session_id=session.id, kind="report", title="B", content="two"))
    assert first.version == 1
    assert second.version == 2


def test_repository_updates_artifact_reference_fields() -> None:
    database = Database("sqlite+pysqlite:///:memory:")
    database.create_all()
    repo = Repository(database)
    session = repo.create_session(SessionRecord(title="t"))
    artifact = repo.add_artifact(ArtifactRecord(session_id=session.id, kind="report", title="A", content="one"))

    artifact.storage_kind = "file"
    artifact.file_path = "runtime/artifacts/s1/a.md"
    repo.update_artifact(artifact)

    stored = repo.list_artifacts(session.id)[0]
    assert stored.storage_kind == "file"
    assert stored.file_path == "runtime/artifacts/s1/a.md"
