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
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class AgentDecision(BaseModel):
    response: str
    tool_calls: list[ToolCallDecision] = Field(default_factory=list)
    mark_stage_complete: bool = False


class ProviderClient(Protocol):
    def decide(
        self,
        *,
        agent: AgentDefinition,
        stage: StageDefinition,
        prompt: str,
        tools: list[ToolDefinition],
    ) -> AgentDecision: ...


class StubProvider:
    def decide(
        self,
        *,
        agent: AgentDefinition,
        stage: StageDefinition,
        prompt: str,
        tools: list[ToolDefinition],
    ) -> AgentDecision:
        available_tools = {tool.name for tool in tools}
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


class AzureOpenAIProvider:
    def __init__(self, *, endpoint: str, api_key: str, api_version: str, deployment: str):
        if AzureOpenAI is None:
            raise RuntimeError("openai package is required for Azure OpenAI support")
        self.deployment = deployment
        self.client = AzureOpenAI(azure_endpoint=endpoint, api_key=api_key, api_version=api_version)

    def decide(
        self,
        *,
        agent: AgentDefinition,
        stage: StageDefinition,
        prompt: str,
        tools: list[ToolDefinition],
    ) -> AgentDecision:
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
        completion = self.client.chat.completions.create(
            model=self.deployment,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a controlled stage-based agent. Use only the supplied tools when needed. "
                        "Always return a final response message, and set mark_stage_complete only when the stage work is done."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            tools=tool_payload or None,
            response_format={
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
        )
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
            tool_calls.append(ToolCallDecision(tool_name=tool_call.function.name, arguments=arguments))
        try:
            return AgentDecision.model_validate({**payload, "tool_calls": tool_calls})
        except ValidationError as exc:  # pragma: no cover
            raise ValueError(f"provider decision failed validation: {exc}") from exc
