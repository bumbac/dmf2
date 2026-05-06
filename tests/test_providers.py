from __future__ import annotations

import json
from pathlib import Path

import pytest

from dmf2_agents.agents import AgentRegistry
from dmf2_agents.config import build_provider_settings, get_settings
from dmf2_agents.providers import AgentDecision, AzureOpenAIProvider, StubProvider, ToolCallDecision
from dmf2_agents.stages import StageRegistry
from dmf2_agents.tools import ToolDefinition


def test_stub_provider_returns_tool_calls(project_root: Path) -> None:
    agent = AgentRegistry().get("planner")
    stage = StageRegistry(project_root / "examples" / "pipeline.yaml").get("discover")
    assert agent is not None
    assert stage is not None
    decision = StubProvider().decide(
        agent=agent,
        stage=stage,
        prompt="prompt",
        tools=[
            ToolDefinition(name="update_progress", description="progress"),
            ToolDefinition(name="write_artifact", description="artifact"),
        ],
    )
    assert decision.mark_stage_complete is True
    assert [call.tool_name for call in decision.tool_calls] == ["update_progress", "write_artifact"]


def test_settings_enable_azure_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "key")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "gpt-deployment")
    get_settings.cache_clear()
    settings = get_settings()
    assert settings.model_backend == "azure_openai"
    provider_settings = build_provider_settings(settings)
    assert provider_settings["deployment"] == "gpt-deployment"


def test_azure_provider_parses_structured_response(monkeypatch: pytest.MonkeyPatch, project_root: Path) -> None:
    class FakeMessage:
        content = json.dumps({"response": "done", "mark_stage_complete": True})
        tool_calls = [
            type(
                "ToolCall",
                (),
                {
                    "function": type(
                        "Function",
                        (),
                        {"name": "write_artifact", "arguments": json.dumps({"kind": "note", "title": "t", "content": "c"})},
                    )()
                },
            )()
        ]

    class FakeChoice:
        message = FakeMessage()

    class FakeCompletion:
        choices = [FakeChoice()]

    class FakeClient:
        class chat:
            class completions:
                @staticmethod
                def create(**kwargs):
                    return FakeCompletion()

    monkeypatch.setattr("dmf2_agents.providers.AzureOpenAI", lambda **kwargs: FakeClient())
    provider = AzureOpenAIProvider(
        endpoint="https://example.openai.azure.com",
        api_key="key",
        api_version="2024-08-01-preview",
        deployment="gpt-deployment",
    )
    agent = AgentRegistry().get("planner")
    stage = StageRegistry(project_root / "examples" / "pipeline.yaml").get("discover")
    assert agent is not None
    assert stage is not None
    decision = provider.decide(
        agent=agent,
        stage=stage,
        prompt="prompt",
        tools=[ToolDefinition(name="write_artifact", description="artifact")],
    )
    assert isinstance(decision, AgentDecision)
    assert decision.response == "done"
    assert decision.mark_stage_complete is True
    assert decision.tool_calls == [
        ToolCallDecision(tool_name="write_artifact", arguments={"kind": "note", "title": "t", "content": "c"})
    ]
