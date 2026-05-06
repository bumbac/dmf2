from __future__ import annotations

from pathlib import Path

from .agents import AgentRegistry
from .artifacts import ArtifactService
from .config import build_provider_settings, get_settings
from .events import EventBus
from .memory import MemoryService
from .orchestrator import SessionOrchestrator
from .prompting import PromptBuilder
from .providers import GatewayConfig, build_provider
from .repository import Repository
from .runner import AgentRunner
from .skills import SkillRegistry
from .stages import StageRegistry
from .storage import Database
from .tools import PermissionService, ToolRegistry


def build_app(project_root: Path | None = None) -> SessionOrchestrator:
    settings = get_settings()
    root = project_root or settings.project_root
    database = Database(settings.database_url)
    database.create_all()
    repository = Repository(database)
    memory = MemoryService(repository)
    artifacts = ArtifactService(repository)
    events = EventBus(repository)
    stages = StageRegistry(root / "examples" / "pipeline.yaml")
    agents = AgentRegistry()
    skills = SkillRegistry(root / "skills")
    permission = PermissionService({agent.name: set(agent.allowed_tools) for agent in agents.list()})
    tools = ToolRegistry(root=root, memory=memory, artifacts=artifacts, skills=skills, permission=permission)
    provider = build_provider(GatewayConfig.model_validate(build_provider_settings(settings)))
    runner = AgentRunner(memory=memory, artifacts=artifacts, tools=tools, prompt_builder=PromptBuilder(), provider=provider)
    return SessionOrchestrator(
        repository=repository,
        memory=memory,
        artifacts=artifacts,
        events=events,
        stages=stages,
        agents=agents,
        runner=runner,
    )
