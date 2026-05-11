from __future__ import annotations

from pathlib import Path

import pytest

from dmf2_agents.agents import AgentRegistry
from dmf2_agents.artifacts import ArtifactService
from dmf2_agents.domain import AgentDefinition, StageDefinition
from dmf2_agents.memory import MemoryService
from dmf2_agents.prompting import PromptBuilder
from dmf2_agents.providers import AgentDecision, ToolCallDecision
from dmf2_agents.repository import Repository
from dmf2_agents.runner import AgentRunner
from dmf2_agents.skills import SkillRegistry
from dmf2_agents.storage import Database
from dmf2_agents.tasks import TaskService
from dmf2_agents.tools import PermissionService, ToolRegistry


class FakeProvider:
    def __init__(self, decision: AgentDecision):
        self.decision = decision

    async def decide(self, **kwargs) -> AgentDecision:
        return self.decision


class SequenceProvider:
    def __init__(self, decisions: list[AgentDecision]):
        self.decisions = decisions
        self.index = 0
        self.calls: list[dict[str, object]] = []

    async def decide(self, **kwargs) -> AgentDecision:
        self.calls.append(kwargs)
        if self.index >= len(self.decisions):
            return self.decisions[-1]
        decision = self.decisions[self.index]
        self.index += 1
        return decision


def build_runner(project_root: Path, decision: AgentDecision) -> tuple[AgentRunner, Repository]:
    database = Database("sqlite+pysqlite:///:memory:")
    database.create_all()
    repo = Repository(database)
    memory = MemoryService(repo)
    artifacts = ArtifactService(repo, root=project_root)
    tools = ToolRegistry(
        root=project_root,
        memory=memory,
        artifacts=artifacts,
        skills=SkillRegistry(project_root / "skills"),
        permission=PermissionService({agent.name: set(agent.allowed_tools) for agent in AgentRegistry().list()}),
    )
    runner = AgentRunner(
        memory=memory,
        artifacts=artifacts,
        tools=tools,
        prompt_builder=PromptBuilder(),
        provider=FakeProvider(decision),
    )
    tools.task_executor = TaskService(repository=repo, memory=memory, artifacts=artifacts, agents=AgentRegistry(), runner=runner)
    return runner, repo


def build_repository_runner(project_root: Path, provider) -> tuple[AgentRunner, Repository, ToolRegistry]:
    database = Database("sqlite+pysqlite:///:memory:")
    database.create_all()
    repo = Repository(database)
    memory = MemoryService(repo)
    artifacts = ArtifactService(repo, root=project_root)
    tools = ToolRegistry(
        root=project_root,
        memory=memory,
        artifacts=artifacts,
        skills=SkillRegistry(project_root / "skills"),
        permission=PermissionService({agent.name: set(agent.allowed_tools) for agent in AgentRegistry().list()}),
    )
    runner = AgentRunner(
        memory=memory,
        artifacts=artifacts,
        tools=tools,
        prompt_builder=PromptBuilder(),
        provider=provider,
    )
    tools.task_executor = TaskService(repository=repo, memory=memory, artifacts=artifacts, agents=AgentRegistry(), runner=runner)
    return runner, repo, tools


@pytest.mark.anyio
async def test_runner_executes_provider_tool_calls(project_root: Path) -> None:
    runner, repo, _ = build_repository_runner(
        project_root,
        SequenceProvider(
            [
                AgentDecision(
                    response="working",
                    tool_calls=[
                        ToolCallDecision(tool_name="update_progress", arguments={"message": "working", "status": "in_progress"}),
                        ToolCallDecision(
                            tool_name="write_artifact",
                            arguments={"kind": "discover_note", "title": "Discover", "content": "artifact body"},
                        ),
                    ],
                ),
                AgentDecision(response="done", tool_calls=[]),
            ]
        ),
    )
    stage = StageDefinition(id="discover", name="Discover", goal="Understand", assigned_agents=["planner"])
    agent = AgentRegistry().get("planner")
    assert agent is not None
    outcome = await runner.run(session_id="s1", stage=stage, agent=agent, user_input="hello")
    assert outcome.response == "done"
    assert outcome.progress_updates == ["working"]
    assert len(outcome.artifacts) == 1
    assert (await repo.list_progress("s1"))[0].message == "working"
    assert (await repo.list_artifacts("s1"))[0].kind == "discover_note"
    messages = await repo.list_messages("s1")
    assert [item.role for item in messages] == ["assistant", "tool", "tool", "assistant"]


@pytest.mark.anyio
async def test_runner_replays_tool_results_into_follow_up_provider_turn(project_root: Path) -> None:
    runner, repo, _ = build_repository_runner(
        project_root,
        SequenceProvider(
        [
            AgentDecision(
                response="starting",
                tool_calls=[
                    ToolCallDecision(
                        tool_name="update_progress",
                        arguments={"message": "working", "status": "in_progress"},
                    )
                ],
            ),
            AgentDecision(response="done", tool_calls=[]),
        ]
        ),
    )
    provider = runner.provider

    agent = AgentRegistry().get("planner")
    assert agent is not None
    outcome = await runner.run(
        session_id="s1",
        stage=StageDefinition(id="discover", name="Discover", goal="Understand", assigned_agents=["planner"]),
        agent=agent,
        user_input="hello",
    )

    assert outcome.response == "done"
    assert len(provider.calls) == 2
    second_call_messages = provider.calls[1]["messages"]
    assert any(message.role == "tool" and "update_progress" in message.content for message in second_call_messages)
    stored_messages = await repo.list_messages("s1")
    assert [item.role for item in stored_messages] == ["assistant", "tool", "assistant"]


@pytest.mark.anyio
async def test_runner_stops_at_agent_iteration_limit(project_root: Path) -> None:
    runner, repo, _ = build_repository_runner(
        project_root,
        SequenceProvider(
        [
            AgentDecision(
                response="loop 1",
                tool_calls=[
                    ToolCallDecision(
                        tool_name="update_progress",
                        arguments={"message": "step 1", "status": "in_progress"},
                    )
                ],
            ),
            AgentDecision(
                response="loop 2",
                tool_calls=[
                    ToolCallDecision(
                        tool_name="update_progress",
                        arguments={"message": "step 2", "status": "in_progress"},
                    )
                ],
            ),
        ]
        ),
    )
    provider = runner.provider

    outcome = await runner.run(
        session_id="s1",
        stage=StageDefinition(id="discover", name="Discover", goal="Understand", assigned_agents=["planner"]),
        agent=AgentDefinition(
            name="planner",
            description="p",
            system_prompt="prompt",
            allowed_tools=["update_progress"],
            max_iterations=1,
        ),
        user_input="hello",
    )

    assert outcome.response.endswith("Iteration limit reached.")
    assert len(provider.calls) == 1
    assert [item.message for item in await repo.list_progress("s1")] == ["step 1"]


@pytest.mark.anyio
async def test_runner_denied_tool_call_raises(project_root: Path) -> None:
    database = Database("sqlite+pysqlite:///:memory:")
    database.create_all()
    repo = Repository(database)
    memory = MemoryService(repo)
    artifacts = ArtifactService(repo, root=project_root)
    tools = ToolRegistry(
        root=project_root,
        memory=memory,
        artifacts=artifacts,
        skills=SkillRegistry(project_root / "skills"),
        permission=PermissionService({"planner": {"write_artifact"}}),
    )
    runner = AgentRunner(
        memory=memory,
        artifacts=artifacts,
        tools=tools,
        prompt_builder=PromptBuilder(),
        provider=FakeProvider(
            AgentDecision(
                response="done",
                tool_calls=[ToolCallDecision(tool_name="run_command", arguments={"command": ["pwd"]})],
            )
        ),
    )
    with pytest.raises(PermissionError):
        await runner.run(
            session_id="s1",
            stage=StageDefinition(id="execute", name="Execute", goal="Build", assigned_agents=["planner"]),
            agent=AgentDefinition(
                name="planner",
                description="p",
                system_prompt="prompt",
                allowed_tools=["write_artifact"],
            ),
            user_input="hello",
        )


@pytest.mark.anyio
async def test_runner_planner_can_read_files_but_not_write(project_root: Path) -> None:
    runner, repo, _ = build_repository_runner(
        project_root,
        SequenceProvider(
            [
                AgentDecision(
                    response="inspecting inputs",
                    tool_calls=[ToolCallDecision(tool_name="read_file", arguments={"path": "examples/pipeline.yaml"})],
                ),
                AgentDecision(response="done", tool_calls=[]),
            ]
        ),
    )
    agent = AgentRegistry().get("planner")
    assert agent is not None

    outcome = await runner.run(
        session_id="s1",
        stage=StageDefinition(id="discover", name="Discover", goal="Inspect the workflow file", assigned_agents=["planner"]),
        agent=agent,
        user_input="inspect",
    )

    assert outcome.response == "done"
    stored_messages = await repo.list_messages("s1")
    assert any(message.role == "tool" and "stages:" in message.content for message in stored_messages)

    denied_runner, _, _ = build_repository_runner(
        project_root,
        FakeProvider(
            AgentDecision(
                response="attempting write",
                tool_calls=[ToolCallDecision(tool_name="write_file", arguments={"path": "tmp/out.txt", "content": "nope"})],
            )
        ),
    )
    with pytest.raises(PermissionError):
        await denied_runner.run(
            session_id="s2",
            stage=StageDefinition(id="discover", name="Discover", goal="Do not write", assigned_agents=["planner"]),
            agent=agent,
            user_input="inspect",
        )


@pytest.mark.anyio
async def test_runner_reviewer_can_read_files_for_validation(project_root: Path) -> None:
    runner, repo, _ = build_repository_runner(
        project_root,
        SequenceProvider(
            [
                AgentDecision(
                    response="reviewing output",
                    tool_calls=[
                        ToolCallDecision(tool_name="read_file", arguments={"path": "examples/migration-clean.yaml"}),
                        ToolCallDecision(
                            tool_name="write_artifact",
                            arguments={"kind": "validation_report", "title": "Validation", "content": "Reviewed output files."},
                        ),
                    ],
                ),
                AgentDecision(response="validated", tool_calls=[]),
            ]
        ),
    )
    agent = AgentRegistry().get("reviewer")
    assert agent is not None

    outcome = await runner.run(
        session_id="s1",
        stage=StageDefinition(id="validate", name="Validate", goal="Inspect generated outputs", assigned_agents=["reviewer"]),
        agent=agent,
        user_input="validate",
    )

    assert outcome.response == "validated"
    assert (await repo.list_artifacts("s1"))[0].kind == "validation_report"
    assert any(message.role == "tool" and "Discover Migration Inputs" in message.content for message in await repo.list_messages("s1"))


@pytest.mark.anyio
async def test_runner_creates_real_child_session_for_task_tool(project_root: Path) -> None:
    class TaskAwareProvider:
        def __init__(self):
            self.parent_calls = 0
            self.child_calls = 0

        async def decide(self, **kwargs) -> AgentDecision:
            session_messages = kwargs["messages"]
            user_prompt = session_messages[0].content
            if "Review the current stage artifacts." in user_prompt:
                if self.child_calls == 0:
                    self.child_calls += 1
                    return AgentDecision(
                        response="review complete",
                        tool_calls=[
                            ToolCallDecision(
                                tool_name="write_artifact",
                                arguments={"kind": "review_report", "title": "Child Review", "content": "approved"},
                            )
                        ],
                    )
                self.child_calls += 1
                return AgentDecision(response="review finalized", tool_calls=[])
            if self.parent_calls == 0:
                self.parent_calls += 1
                return AgentDecision(
                    response="delegating",
                    tool_calls=[
                        ToolCallDecision(
                            tool_name="run_task_agent",
                            arguments={"subagent_name": "reviewer", "prompt": "Review the current stage artifacts."},
                        ),
                        ToolCallDecision(
                            tool_name="write_artifact",
                            arguments={"kind": "review_report", "title": "Review", "content": "looks good"},
                        ),
                    ],
                )
            self.parent_calls += 1
            return AgentDecision(response="review finalized", tool_calls=[])

    runner, repo, _ = build_repository_runner(project_root, TaskAwareProvider())
    stage = StageDefinition(id="validate", name="Validate", goal="Validate outputs", assigned_agents=["reviewer"])
    agent = AgentRegistry().get("planner")
    assert agent is not None
    outcome = await runner.run(session_id="parent-session", stage=stage, agent=agent, user_input="start validation")
    children = await repo.list_child_sessions("parent-session")
    assert len(children) == 1
    child = children[0]
    child_messages = await repo.list_messages(child.id)
    assert child_messages[0].role == "user"
    assert "Review the current stage artifacts." in child_messages[0].content
    assert child_messages[-1].role == "assistant"
    assert child.status == "completed"
    assert child.title == "Task: reviewer for validate"
    child_summary = await repo.latest_summary(child.id)
    assert child_summary is not None
    assert "review finalized" in child_summary.content
    child_artifacts = await repo.list_artifacts(child.id)
    assert len(child_artifacts) == 1
    assert child_artifacts[0].kind == "review_report"
    parent_artifacts = await repo.list_artifacts("parent-session")
    assert len(parent_artifacts) == 1
    assert parent_artifacts[0].title == "Review"
    assert "review finalized" in outcome.response
