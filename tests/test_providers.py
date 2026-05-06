from __future__ import annotations

import json
from pathlib import Path

import pytest

from dmf2_agents.agents import AgentRegistry
from dmf2_agents.config import build_provider_settings, get_settings
from dmf2_agents.providers import AgentDecision, GatewayConfig, GatewayProvider, ProviderMessage, StubProvider, ToolCallDecision, build_provider
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
        messages=[ProviderMessage(role="user", content="prompt")],
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
    assert provider_settings["provider"] == "azure_openai"
    assert provider_settings["model"] == "gpt-deployment"


def test_gateway_provider_parses_structured_response(project_root: Path) -> None:
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

    class FakeGatewayClient:
        def create_response(self, *, messages: list[ProviderMessage], tools: list[ToolDefinition]):
            return FakeCompletion()

    provider = GatewayProvider(FakeGatewayClient())
    agent = AgentRegistry().get("planner")
    stage = StageRegistry(project_root / "examples" / "pipeline.yaml").get("discover")
    assert agent is not None
    assert stage is not None
    decision = provider.decide(
        agent=agent,
        stage=stage,
        messages=[ProviderMessage(role="user", content="prompt")],
        tools=[ToolDefinition(name="write_artifact", description="artifact")],
    )
    assert isinstance(decision, AgentDecision)
    assert decision.response == "done"
    assert decision.mark_stage_complete is True
    assert decision.tool_calls == [
        ToolCallDecision(tool_name="write_artifact", arguments={"kind": "note", "title": "t", "content": "c"})
    ]


def test_gateway_provider_rejects_invalid_tool_arguments(project_root: Path) -> None:
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
                        {"name": "write_artifact", "arguments": "{"},
                    )()
                },
            )()
        ]

    class FakeChoice:
        message = FakeMessage()

    class FakeCompletion:
        choices = [FakeChoice()]

    class FakeGatewayClient:
        def create_response(self, *, messages: list[ProviderMessage], tools: list[ToolDefinition]):
            return FakeCompletion()

    provider = GatewayProvider(FakeGatewayClient())
    agent = AgentRegistry().get("planner")
    stage = StageRegistry(project_root / "examples" / "pipeline.yaml").get("discover")
    assert agent is not None
    assert stage is not None

    with pytest.raises(ValueError, match="invalid JSON arguments"):
        provider.decide(
            agent=agent,
            stage=stage,
            messages=[ProviderMessage(role="user", content="prompt")],
            tools=[ToolDefinition(name="write_artifact", description="artifact")],
        )


def test_build_provider_uses_stub_backend() -> None:
    provider = build_provider(GatewayConfig(provider="stub", model="stub-model"))
    assert isinstance(provider, StubProvider)
