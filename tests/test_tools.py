from __future__ import annotations

from pathlib import Path

from dmf2_agents.artifacts import ArtifactService
from dmf2_agents.memory import MemoryService
from dmf2_agents.repository import Repository
from dmf2_agents.skills import SkillRegistry
from dmf2_agents.storage import Database
from dmf2_agents.tools import PermissionService, ToolContext, ToolRegistry


def test_permission_service_denies_unscoped_tool(project_root: Path) -> None:
    database = Database("sqlite+pysqlite:///:memory:")
    database.create_all()
    repo = Repository(database)
    tools = ToolRegistry(
        root=project_root,
        memory=MemoryService(repo),
        artifacts=ArtifactService(repo, root=project_root),
        skills=SkillRegistry(project_root / "skills"),
        permission=PermissionService({"planner": {"write_artifact"}}),
    )
    try:
        tools.run("planner", "run_command", ToolContext(session_id="s1", agent_name="planner"), command=["pwd"])
    except PermissionError:
        assert True
    else:
        assert False


def test_tool_registry_no_longer_exposes_stage_completion_tool(project_root: Path) -> None:
    database = Database("sqlite+pysqlite:///:memory:")
    database.create_all()
    repo = Repository(database)
    tools = ToolRegistry(
        root=project_root,
        memory=MemoryService(repo),
        artifacts=ArtifactService(repo, root=project_root),
        skills=SkillRegistry(project_root / "skills"),
        permission=PermissionService({"planner": {"write_artifact"}}),
    )
    descriptions = [tool.name for tool in tools.discover_for_agent("planner")]
    assert "mark_stage_complete" not in descriptions


def test_write_artifact_persists_runtime_file(project_root: Path) -> None:
    database = Database("sqlite+pysqlite:///:memory:")
    database.create_all()
    repo = Repository(database)
    tools = ToolRegistry(
        root=project_root,
        memory=MemoryService(repo),
        artifacts=ArtifactService(repo, root=project_root),
        skills=SkillRegistry(project_root / "skills"),
        permission=PermissionService({"planner": {"write_artifact"}}),
    )

    artifact_id = tools.run(
        "planner",
        "write_artifact",
        ToolContext(session_id="s1", stage_id="discover", agent_name="planner"),
        kind="note",
        title="Chunked Output",
        content="This is a chunk summarizing the persisted payload.",
    )

    stored = repo.list_artifacts("s1")
    assert artifact_id == stored[0].id
    assert stored[0].storage_kind == "file"
    assert stored[0].file_path is not None
    persisted = project_root / stored[0].file_path
    assert persisted.exists()
    assert persisted.read_text() == "This is a chunk summarizing the persisted payload."
