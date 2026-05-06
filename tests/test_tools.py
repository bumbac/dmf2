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
        artifacts=ArtifactService(repo),
        skills=SkillRegistry(project_root / "skills"),
        permission=PermissionService({"planner": {"write_artifact"}}),
    )
    try:
        tools.run("planner", "run_command", ToolContext(session_id="s1", agent_name="planner"), command=["pwd"])
    except PermissionError:
        assert True
    else:
        assert False
