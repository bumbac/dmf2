from __future__ import annotations

import json
from typing import Any, Protocol

from pydantic import BaseModel, Field, ValidationError

from .domain import AgentDefinition, StageDefinition
from .tools import ToolDefinition

try:
    from langchain_openai import AzureChatOpenAI
except ImportError:  # pragma: no cover
    AzureChatOpenAI = None


class ToolCallDecision(BaseModel):
    id: str | None = None
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class AgentDecision(BaseModel):
    response: str
    tool_calls: list[ToolCallDecision] = Field(default_factory=list)


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


class OpenAIGatewayClient:
    def __init__(self, config: GatewayConfig):
        if AzureChatOpenAI is None:
            raise RuntimeError("langchain-openai package is required for Azure OpenAI support")
        self.config = config
        if config.provider != "azure_openai":
            raise ValueError(f"unsupported gateway provider: {config.provider}")
        self.client = AzureChatOpenAI(
            azure_endpoint=config.endpoint,
            api_key=config.api_key,
            api_version=config.api_version,
            azure_deployment=config.model,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )

    def create_response(self, *, messages: list[ProviderMessage], tools: list[ToolDefinition]) -> Any:
        client = self.client.bind_tools([self._tool_payload(tool) for tool in tools], tool_choice="auto")
        return client.invoke(
            [
                {
                    "role": "system",
                    "content": (
                        "You are a controlled stage-based agent. Use only the supplied tools when needed. "
                        "Always return a final response message as strict JSON with the field 'response'."
                    ),
                },
                *[self._serialize_message(message) for message in messages],
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "agent_decision",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "response": {"type": "string"},
                            },
                            "required": ["response"],
                            "additionalProperties": False,
                        },
                    "strict": True,
                },
            },
        )

    def create_stage_evaluation_response(self, *, stage: StageDefinition, messages: list[ProviderMessage]) -> Any:
        return self.client.invoke(
            [
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
            response_format={
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

    def _tool_payload(self, tool: ToolDefinition) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": self._tool_parameters(tool.name),
                "strict": True,
            },
        }

    def _tool_parameters(self, tool_name: str) -> dict[str, Any]:
        if tool_name == "read_file":
            return {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "Project-relative path to a text file to read."}},
                "required": ["path"],
                "additionalProperties": False,
            }
        if tool_name == "write_file":
            return {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Project-relative output path to write."},
                    "content": {"type": "string", "description": "Full file content to write."},
                },
                "required": ["path", "content"],
                "additionalProperties": False,
            }
        if tool_name == "run_command":
            return {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Command and arguments as a string array.",
                    }
                },
                "required": ["command"],
                "additionalProperties": False,
            }
        if tool_name == "write_artifact":
            return {
                "type": "object",
                "properties": {
                    "kind": {"type": "string"},
                    "title": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["kind", "title", "content"],
                "additionalProperties": False,
            }
        if tool_name == "update_progress":
            return {
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "status": {"type": "string"},
                },
                "required": ["message", "status"],
                "additionalProperties": False,
            }
        if tool_name == "load_skill":
            return {
                "type": "object",
                "properties": {"skill_name": {"type": "string"}},
                "required": ["skill_name"],
                "additionalProperties": False,
            }
        if tool_name == "run_task_agent":
            return {
                "type": "object",
                "properties": {
                    "subagent_name": {"type": "string"},
                    "prompt": {"type": "string"},
                },
                "required": ["subagent_name", "prompt"],
                "additionalProperties": False,
            }
        return {"type": "object", "properties": {}, "additionalProperties": True}


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
        payload = self._extract_payload(completion, context="decision")
        tool_calls: list[ToolCallDecision] = []
        for tool_call in self._extract_tool_calls(completion):
            tool_calls.append(tool_call)
        payload.setdefault("response", "Tool call requested.")
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
        payload = self._extract_payload(completion, context="stage evaluation")
        try:
            return StageEvaluationDecision.model_validate(payload)
        except ValidationError as exc:  # pragma: no cover
            raise ValueError(f"provider stage evaluation failed validation: {exc}") from exc

    def _extract_payload(self, completion: Any, *, context: str) -> dict[str, Any]:
        if isinstance(completion, dict):
            return dict(completion)
        if hasattr(completion, "choices"):
            choice = completion.choices[0].message
            return self._parse_json_content(choice.content, context=context)
        content = getattr(completion, "content", None)
        if isinstance(content, str):
            return self._parse_json_content(content, context=context)
        raise ValueError(f"provider returned unexpected {context} payload: {completion!r}")

    def _parse_json_content(self, content: str | None, *, context: str) -> dict[str, Any]:
        raw = (content or "{}").strip()
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            decoder = json.JSONDecoder()
            index = 0
            payload = None
            while index < len(raw):
                while index < len(raw) and raw[index].isspace():
                    index += 1
                if index >= len(raw):
                    break
                try:
                    candidate, end = decoder.raw_decode(raw, index)
                except json.JSONDecodeError as exc:  # pragma: no cover
                    raise ValueError(f"provider returned invalid JSON: {content}") from exc
                if isinstance(candidate, dict):
                    payload = candidate
                index = end
            if payload is None:
                raise ValueError(f"provider returned invalid {context} payload: {content}")
        if not isinstance(payload, dict):
            raise ValueError(f"provider returned unexpected {context} payload: {payload!r}")
        return payload

    def _extract_tool_calls(self, completion: Any) -> list[ToolCallDecision]:
        if hasattr(completion, "choices"):
            source_calls = completion.choices[0].message.tool_calls or []
            parsed_calls = []
            for tool_call in source_calls:
                args = tool_call.function.arguments or "{}"
                try:
                    arguments = json.loads(args)
                except json.JSONDecodeError as exc:  # pragma: no cover
                    raise ValueError(f"tool call '{tool_call.function.name}' returned invalid JSON arguments") from exc
                parsed_calls.append(
                    ToolCallDecision(id=getattr(tool_call, "id", None), tool_name=tool_call.function.name, arguments=arguments)
                )
            return parsed_calls
        source_calls = getattr(completion, "tool_calls", None) or []
        parsed_calls = []
        for tool_call in source_calls:
            name = tool_call.get("name") or tool_call.get("function", {}).get("name")
            arguments = tool_call.get("args")
            if arguments is None:
                raw_arguments = tool_call.get("function", {}).get("arguments", "{}")
                try:
                    arguments = json.loads(raw_arguments)
                except json.JSONDecodeError as exc:  # pragma: no cover
                    raise ValueError(f"tool call '{name}' returned invalid JSON arguments") from exc
            parsed_calls.append(
                ToolCallDecision(id=tool_call.get("id"), tool_name=name, arguments=arguments)
            )
        return parsed_calls


def build_provider(config: GatewayConfig) -> ProviderClient:
    if config.provider != "azure_openai":
        raise ValueError(f"unsupported provider: {config.provider}")
    return GatewayProvider(OpenAIGatewayClient(config))
