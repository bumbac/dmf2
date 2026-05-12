from __future__ import annotations

from pathlib import Path

from .agents import AgentRegistry
from .artifacts import ArtifactService
from .config import build_provider_settings, get_settings
from .evaluators import HumanConfirmationStageEvaluationClient, ProviderStageEvaluationClient, StageEvaluator
from .events import EventBus
from .logging import configure_logging
from .memory import MemoryService
from .orchestrator import SessionOrchestrator
from .prompting import PromptBuilder
from .providers import GatewayConfig, build_provider
from .repository import Repository
from .runner import AgentRunner
from .skills import SkillRegistry
from .stages import StageRegistry
from .storage import Database
from .tasks import TaskService
from .tools import PermissionService, ToolRegistry


def build_app(project_root: Path | None = None, workflow_path: Path | None = None) -> SessionOrchestrator:
    settings = get_settings()
    configure_logging(level=settings.log_level, log_file=settings.log_file)
    root = project_root or settings.project_root
    database = Database(settings.database_url)
    database.create_all()
    repository = Repository(database)
    memory = MemoryService(repository)
    artifacts = ArtifactService(repository, root=root)
    events = EventBus(repository)
    stages = StageRegistry(workflow_path or settings.default_stage_file)
    agents = AgentRegistry()
    skills = SkillRegistry(root / "skills")
    permission = PermissionService({agent.name: set(agent.allowed_tools) for agent in agents.list()})
    tools = ToolRegistry(root=root, memory=memory, artifacts=artifacts, skills=skills, permission=permission)
    provider_settings = build_provider_settings(settings)
    provider = build_provider(GatewayConfig.model_validate(provider_settings))
    evaluation_client = HumanConfirmationStageEvaluationClient(auto_approve=settings.human_confirmation_auto_approve)
    if settings.stage_evaluation_mode == "provider":
        evaluation_client = ProviderStageEvaluationClient(provider)
    evaluator = StageEvaluator(repository=repository, memory=memory, artifacts=artifacts, client=evaluation_client)
    runner = AgentRunner(memory=memory, artifacts=artifacts, tools=tools, prompt_builder=PromptBuilder(), provider=provider)
    tools.task_executor = TaskService(repository=repository, memory=memory, artifacts=artifacts, agents=agents, runner=runner)
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
