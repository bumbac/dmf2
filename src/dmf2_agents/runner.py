from __future__ import annotations

import json

from .artifacts import ArtifactService
from .domain import AgentDefinition, AgentOutcome, MessageRecord
from .logging import app_logger, log_context
from .memory import MemoryService
from .prompting import PromptBuilder
from .providers import ProviderClient, ProviderMessage
from .tools import ToolContext, ToolRegistry


SKILLS_LOADED_N_LIMIT = -1

class AgentRunner:
    def __init__(
        self,
        memory: MemoryService,
        artifacts: ArtifactService,
        tools: ToolRegistry,
        prompt_builder: PromptBuilder,
        provider: ProviderClient,
    ):
        self.memory = memory
        self.artifacts = artifacts
        self.tools = tools
        self.prompt_builder = prompt_builder
        self.provider = provider

    async def run(self, *, session_id: str, stage, agent: AgentDefinition, user_input: str) -> AgentOutcome:
        with log_context(session_id=session_id, stage_id=stage.id, agent_name=agent.name):
            summary = await self.memory.latest_summary(session_id)
            plan = await self.memory.latest_plan(session_id)
            progress = await self.memory.list_progress(session_id)
            artifacts = await self.artifacts.list_artifacts(session_id)
            messages_history = await self.memory.recent_messages(session_id, limit=24)
            loaded_skill_defs = []
            if agent.allowed_skills:
                loaded_skill_defs = [self.tools.skills.get(name) for name in agent.allowed_skills[:SKILLS_LOADED_N_LIMIT] if self.tools.skills.get(name)]
            prompt = self.prompt_builder.build(
                agent=agent,
                stage=stage,
                summary=summary,
                plan=plan,
                progress=progress,
                artifacts=artifacts,
                skills=loaded_skill_defs,
                messages=messages_history,
            )
            available_tools = self.tools.discover_for_agent(agent.name)
            tool_context = "\n".join(f"- {tool.name}: {tool.description}" for tool in available_tools) or "None"
            ctx = ToolContext(session_id=session_id, stage_id=stage.id, agent_name=agent.name, stage=stage)
            artifacts_written: list[dict[str, str]] = []
            progress_updates: list[str] = []
            tool_actions: list[dict[str, str]] = []
            messages = [
                ProviderMessage(role="user", content=f"{prompt}\n\nAvailable tools:\n{tool_context}\n\nUser input:\n{user_input}")
            ]
            for record in messages_history:
                if record.role not in {"system", "user", "assistant", "tool"}:
                    continue
                if record.role == "tool":
                    messages.append(ProviderMessage(role="system", content=f"Historical tool output: {record.content}"))
                    continue
                messages.append(ProviderMessage(role=record.role, content=record.content))
            app_logger.bind(
                max_iterations=agent.max_iterations,
                available_tools=[tool.name for tool in available_tools],
                history_messages=len(messages_history),
                loaded_skills=[skill.name for skill in loaded_skill_defs],
            ).info("agent_run_started")
            response = ""
            for iteration in range(agent.max_iterations):
                app_logger.bind(iteration=iteration + 1).info("agent_iteration_started")
                decision = await self.provider.decide(agent=agent, stage=stage, messages=messages, tools=available_tools)
                app_logger.bind(
                    iteration=iteration + 1,
                    response_length=len(decision.response),
                    tool_call_count=len(decision.tool_calls),
                ).info("provider_decision_received")
                await self.memory.append_message(
                    MessageRecord(session_id=session_id, role="assistant", agent_name=agent.name, content=decision.response)
                )
                messages.append(ProviderMessage(role="assistant", content=decision.response, tool_calls=decision.tool_calls))
                response = decision.response
                if not decision.tool_calls:
                    break
                for call in decision.tool_calls:
                    try:
                        app_logger.bind(tool_name=call.tool_name, arguments=call.arguments).info("tool_call_started")
                        result = await self.tools.run(agent.name, call.tool_name, ctx, **call.arguments)
                    except PermissionError:
                        app_logger.bind(tool_name=call.tool_name).warning("tool_call_denied")
                        raise
                    except Exception as exc:
                        tool_actions.append({"tool": call.tool_name, "status": "failed"})
                        app_logger.bind(tool_name=call.tool_name, error_type=type(exc).__name__, error=str(exc)).exception(
                            "tool_call_failed"
                        )
                        tool_result = self._format_tool_error(call.tool_name, call.arguments, exc)
                    else:
                        tool_actions.append({"tool": call.tool_name, "status": "completed"})
                        app_logger.bind(tool_name=call.tool_name).info("tool_call_completed")
                        tool_result = self._format_tool_result(stage.id, call.tool_name, result)
                    await self.memory.append_message(
                        MessageRecord(session_id=session_id, role="tool", agent_name=agent.name, content=tool_result)
                    )
                    messages.append(ProviderMessage(role="tool", content=tool_result, tool_call_id=call.id, tool_name=call.tool_name))
                    if "failed" in tool_result:
                        continue
                    if call.tool_name == "write_artifact":
                        artifacts_written.append({"id": result, "kind": str(call.arguments.get("kind", "artifact"))})
                    if call.tool_name == "update_progress":
                        progress_updates.append(str(call.arguments.get("message", "")))
                    if call.tool_name == "run_task_agent":
                        response = f"{response} {result.summary}".strip()
            else:
                response = f"{response} Iteration limit reached.".strip()
                app_logger.warning("agent_iteration_limit_reached")
            app_logger.bind(
                response_length=len(response),
                tool_actions=tool_actions,
                artifacts=artifacts_written,
                progress_update_count=len(progress_updates),
            ).info("agent_run_finished")
            return AgentOutcome(
                response=response,
                loaded_skills=[skill.name for skill in loaded_skill_defs],
                tool_actions=tool_actions,
                artifacts=artifacts_written,
                progress_updates=progress_updates,
            )

    def _format_tool_result(self, stage_id: str, tool_name: str, result: object) -> str:
        if hasattr(result, "model_dump"):
            payload = result.model_dump()
        else:
            payload = result
        return f"Stage '{stage_id}' tool '{tool_name}' result: {payload}"

    def _format_tool_error(self, tool_name: str, arguments: dict[str, object], exc: Exception) -> str:
        return (
            f"Tool '{tool_name}' failed: {exc}. "
            f"Arguments received: {json.dumps(arguments, default=str, sort_keys=True)}"
        )
