from __future__ import annotations

import json
from pathlib import Path

import pytest

from dmf2_agents.agents import AgentRegistry
from dmf2_agents.config import Settings, build_provider_settings, get_settings
from dmf2_agents.providers import AgentDecision, GatewayConfig, GatewayProvider, ProviderMessage, ToolCallDecision, build_provider
from dmf2_agents.stages import StageRegistry
from dmf2_agents.tools import ToolDefinition


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


@pytest.mark.anyio
async def test_gateway_provider_parses_structured_response(project_root: Path) -> None:
    class FakeMessage:
        content = json.dumps({"response": "done"})
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
        async def create_response(self, *, messages: list[ProviderMessage], tools: list[ToolDefinition]):
            return FakeCompletion()

    provider = GatewayProvider(FakeGatewayClient())
    agent = AgentRegistry().get("planner")
    stage = StageRegistry(project_root / "examples" / "pipeline.yaml").get("discover")
    assert agent is not None
    assert stage is not None
    decision = await provider.decide(
        agent=agent,
        stage=stage,
        messages=[ProviderMessage(role="user", content="prompt")],
        tools=[ToolDefinition(name="write_artifact", description="artifact")],
    )
    assert isinstance(decision, AgentDecision)
    assert decision.response == "done"
    assert decision.tool_calls == [
        ToolCallDecision(tool_name="write_artifact", arguments={"kind": "note", "title": "t", "content": "c"})
    ]


@pytest.mark.anyio
async def test_gateway_provider_rejects_invalid_tool_arguments(project_root: Path) -> None:
    class FakeMessage:
        content = json.dumps({"response": "done"})
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
        async def create_response(self, *, messages: list[ProviderMessage], tools: list[ToolDefinition]):
            return FakeCompletion()

    provider = GatewayProvider(FakeGatewayClient())
    agent = AgentRegistry().get("planner")
    stage = StageRegistry(project_root / "examples" / "pipeline.yaml").get("discover")
    assert agent is not None
    assert stage is not None

    with pytest.raises(ValueError, match="invalid JSON arguments"):
        await provider.decide(
            agent=agent,
            stage=stage,
            messages=[ProviderMessage(role="user", content="prompt")],
            tools=[ToolDefinition(name="write_artifact", description="artifact")],
        )


@pytest.mark.anyio
async def test_gateway_provider_parses_stage_evaluation_response(project_root: Path) -> None:
    class FakeMessage:
        content = json.dumps({"passed": True, "reasoning": "The stage goal is satisfied."})
        tool_calls = []

    class FakeChoice:
        message = FakeMessage()

    class FakeCompletion:
        choices = [FakeChoice()]

    class FakeGatewayClient:
        async def create_response(self, *, messages: list[ProviderMessage], tools: list[ToolDefinition]):
            raise AssertionError("agent response path should not be used for stage evaluation")

        async def create_stage_evaluation_response(self, *, stage, messages: list[ProviderMessage]):
            return FakeCompletion()

    provider = GatewayProvider(FakeGatewayClient())
    stage = StageRegistry(project_root / "examples" / "pipeline.yaml").get("discover")
    assert stage is not None

    decision = await provider.evaluate_stage(
        stage=stage,
        messages=[ProviderMessage(role="assistant", content="Persisted context")],
    )

    assert decision.passed is True
    assert decision.reasoning == "The stage goal is satisfied."


def test_build_provider_rejects_unsupported_backend() -> None:
    with pytest.raises(ValueError, match="unsupported provider"):
        build_provider(GatewayConfig(provider="test", model="gpt"))


def test_build_provider_settings_requires_complete_azure_configuration() -> None:
    settings = Settings(model_backend="azure_openai", model_name="", model_endpoint=None, model_api_key=None)
    with pytest.raises(ValueError, match="configuration is incomplete"):
        build_provider_settings(settings)
