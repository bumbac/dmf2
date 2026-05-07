from __future__ import annotations

import json
from typing import Any, Protocol

from pydantic import BaseModel, Field, ValidationError

from .domain import AgentDefinition, StageDefinition
from .tools import ToolDefinition

try:
    from openai import AzureOpenAI
except ImportError:  # pragma: no cover
    AzureOpenAI = None


class ToolCallDecision(BaseModel):
    id: str | None = None
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class AgentDecision(BaseModel):
    response: str
    tool_calls: list[ToolCallDecision] = Field(default_factory=list)
    mark_stage_complete: bool = False


class StageEvaluationDecision(BaseModel):
    passed: bool
    reasoning: str


class ProviderMessage(BaseModel):
    role: str
    content: str
    tool_call_id: str | None = None
    tool_name: str | None = None
    tool_calls: list[ToolCallDecision] = Field(default_factory=list)


class GatewayConfig(BaseModel):
    provider: str
    model: str
    endpoint: str | None = None
    api_key: str | None = None
    api_version: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None


class ProviderClient(Protocol):
    def decide(
        self,
        *,
        agent: AgentDefinition,
        stage: StageDefinition,
        messages: list[ProviderMessage],
        tools: list[ToolDefinition],
    ) -> AgentDecision: ...


class StageEvaluationProvider(Protocol):
    def evaluate_stage(
        self,
        *,
        stage: StageDefinition,
        messages: list[ProviderMessage],
    ) -> StageEvaluationDecision: ...


class GatewayClient(Protocol):
    def create_response(self, *, messages: list[ProviderMessage], tools: list[ToolDefinition]) -> Any: ...

    def create_stage_evaluation_response(self, *, stage: StageDefinition, messages: list[ProviderMessage]) -> Any: ...


class StubProvider:
    def decide(
        self,
        *,
        agent: AgentDefinition,
        stage: StageDefinition,
        messages: list[ProviderMessage],
        tools: list[ToolDefinition],
    ) -> AgentDecision:
        available_tools = {tool.name for tool in tools}
        prompt = "\n\n".join(message.content for message in messages)
        tool_messages = [message.content for message in messages if message.role == "tool"]
        if any("failed:" in message for message in tool_messages):
            return AgentDecision(
                response=f"Agent {agent.name} encountered a tool failure and is stopping this turn.",
                tool_calls=[],
                mark_stage_complete=False,
            )
        tool_calls: list[ToolCallDecision] = []
        if "update_progress" in available_tools:
            tool_calls.append(
                ToolCallDecision(
                    tool_name="update_progress",
                    arguments={"message": f"Working stage '{stage.id}'", "status": "in_progress"},
                )
            )
        if "write_artifact" in available_tools:
            tool_calls.append(
                ToolCallDecision(
                    tool_name="write_artifact",
                    arguments={
                        "kind": f"{stage.id}_note",
                        "title": f"{stage.name} output",
                        "content": f"Agent: {agent.name}\nGoal: {stage.goal}\n\nPrompt:\n{prompt}",
                    },
                )
            )
        if "validate" in stage.id and "run_task_agent" in available_tools:
            tool_calls.append(
                ToolCallDecision(
                    tool_name="run_task_agent",
                    arguments={"subagent_name": "reviewer", "prompt": f"Review artifacts for stage {stage.id}"},
                )
            )
        return AgentDecision(
            response=f"Agent {agent.name} advanced stage {stage.id}.",
            tool_calls=tool_calls,
            mark_stage_complete=True,
        )

    def evaluate_stage(
        self,
        *,
        stage: StageDefinition,
        messages: list[ProviderMessage],
    ) -> StageEvaluationDecision:
        has_evidence = any(message.content.strip() for message in messages)
        if has_evidence:
            return StageEvaluationDecision(
                passed=True,
                reasoning=f"Stub evaluator found persisted evidence for stage goal '{stage.goal}'.",
            )
        return StageEvaluationDecision(
            passed=False,
            reasoning=f"Stub evaluator found no persisted evidence for stage goal '{stage.goal}'.",
        )


class OpenAIGatewayClient:
    def __init__(self, config: GatewayConfig):
        if AzureOpenAI is None:
            raise RuntimeError("openai package is required for Azure OpenAI support")
        self.config = config
        if config.provider != "azure_openai":
            raise ValueError(f"unsupported gateway provider: {config.provider}")
        self.client = AzureOpenAI(
            azure_endpoint=config.endpoint,
            api_key=config.api_key,
            api_version=config.api_version,
        )

    def create_response(self, *, messages: list[ProviderMessage], tools: list[ToolDefinition]) -> Any:
        tool_payload = [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "additionalProperties": True,
                    },
                },
            }
            for tool in tools
        ]
        request: dict[str, Any] = {
            "model": self.config.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a controlled stage-based agent. Use only the supplied tools when needed. "
                        "Always return a final response message, and set mark_stage_complete only when the stage work is done."
                    ),
                },
                *[self._serialize_message(message) for message in messages],
            ],
            "tools": tool_payload or None,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "agent_decision",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "response": {"type": "string"},
                            "mark_stage_complete": {"type": "boolean"},
                        },
                        "required": ["response", "mark_stage_complete"],
                        "additionalProperties": False,
                    },
                    "strict": True,
                },
            },
        }
        if self.config.temperature != 1:
            request["temperature"] = self.config.temperature
        if self.config.max_tokens is not None:
            request["max_tokens"] = self.config.max_tokens
        return self.client.chat.completions.create(
            **request,
        )

    def create_stage_evaluation_response(self, *, stage: StageDefinition, messages: list[ProviderMessage]) -> Any:
        request: dict[str, Any] = {
            "model": self.config.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a stage evaluator for a controlled workflow system. Determine whether the stated stage goal has been satisfied using only the persisted context you receive. "
                        "Artifacts may be supporting evidence but must not be required. Return strict JSON with fields 'passed' and 'reasoning'."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Evaluate this stage.\nStage id: {stage.id}\nStage name: {stage.name}\nStage goal: {stage.goal}\n"
                        "Judge whether the goal is satisfied based on the provided persisted context."
                    ),
                },
                *[self._serialize_message(message) for message in messages],
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "stage_evaluation",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "passed": {"type": "boolean"},
                            "reasoning": {"type": "string"},
                        },
                        "required": ["passed", "reasoning"],
                        "additionalProperties": False,
                    },
                    "strict": True,
                },
            },
        }
        if self.config.temperature != 1:
            request["temperature"] = self.config.temperature
        if self.config.max_tokens is not None:
            request["max_tokens"] = self.config.max_tokens
        return self.client.chat.completions.create(
            **request,
        )

    def _serialize_message(self, message: ProviderMessage) -> dict[str, Any]:
        payload: dict[str, Any] = {"role": message.role, "content": message.content}
        if message.tool_calls:
            payload["tool_calls"] = [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {"name": call.tool_name, "arguments": json.dumps(call.arguments)},
                }
                for call in message.tool_calls
            ]
        if message.tool_call_id:
            payload["tool_call_id"] = message.tool_call_id
        return payload


class GatewayProvider:
    def __init__(self, client: GatewayClient):
        self.client = client

    def decide(
        self,
        *,
        agent: AgentDefinition,
        stage: StageDefinition,
        messages: list[ProviderMessage],
        tools: list[ToolDefinition],
    ) -> AgentDecision:
        completion = self.client.create_response(messages=messages, tools=tools)
        choice = completion.choices[0].message
        content = choice.content or "{}"
        try:
            payload = json.loads(content)
        except json.JSONDecodeError as exc:  # pragma: no cover
            raise ValueError(f"provider returned invalid JSON: {content}") from exc
        tool_calls: list[ToolCallDecision] = []
        for tool_call in choice.tool_calls or []:
            args = tool_call.function.arguments or "{}"
            try:
                arguments = json.loads(args)
            except json.JSONDecodeError as exc:  # pragma: no cover
                raise ValueError(f"tool call '{tool_call.function.name}' returned invalid JSON arguments") from exc
            tool_calls.append(
                ToolCallDecision(id=getattr(tool_call, "id", None), tool_name=tool_call.function.name, arguments=arguments)
            )
        payload.setdefault("response", "Tool call requested.")
        payload.setdefault("mark_stage_complete", False)
        try:
            return AgentDecision.model_validate({**payload, "tool_calls": tool_calls})
        except ValidationError as exc:  # pragma: no cover
            raise ValueError(f"provider decision failed validation: {exc}") from exc

    def evaluate_stage(
        self,
        *,
        stage: StageDefinition,
        messages: list[ProviderMessage],
    ) -> StageEvaluationDecision:
        completion = self.client.create_stage_evaluation_response(stage=stage, messages=messages)
        choice = completion.choices[0].message
        content = choice.content or "{}"
        try:
            payload = json.loads(content)
        except json.JSONDecodeError as exc:  # pragma: no cover
            raise ValueError(f"provider returned invalid JSON: {content}") from exc
        try:
            return StageEvaluationDecision.model_validate(payload)
        except ValidationError as exc:  # pragma: no cover
            raise ValueError(f"provider stage evaluation failed validation: {exc}") from exc


def build_provider(config: GatewayConfig) -> ProviderClient:
    if config.provider == "stub":
        return StubProvider()
    return GatewayProvider(OpenAIGatewayClient(config))
