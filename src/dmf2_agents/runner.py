from __future__ import annotations

from .artifacts import ArtifactService
from .domain import AgentDefinition, AgentOutcome, MessageRecord
from .memory import MemoryService
from .prompting import PromptBuilder
from .providers import ProviderClient, ProviderMessage
from .tools import ToolContext, ToolRegistry


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

    def run(self, *, session_id: str, stage, agent: AgentDefinition, user_input: str) -> AgentOutcome:
        summary = self.memory.latest_summary(session_id)
        plan = self.memory.latest_plan(session_id)
        progress = self.memory.list_progress(session_id)
        artifacts = self.artifacts.list_artifacts(session_id)
        loaded_skill_defs = []
        if agent.allowed_skills:
            loaded_skill_defs = [self.tools.skills.get(name) for name in agent.allowed_skills[:1] if self.tools.skills.get(name)]
        prompt = self.prompt_builder.build(
            agent=agent,
            stage=stage,
            summary=summary,
            plan=plan,
            progress=progress,
            artifacts=artifacts,
            skills=loaded_skill_defs,
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
        response = ""
        stage_complete = False
        for _ in range(agent.max_iterations):
            decision = self.provider.decide(agent=agent, stage=stage, messages=messages, tools=available_tools)
            self.memory.append_message(
                MessageRecord(session_id=session_id, role="assistant", agent_name=agent.name, content=decision.response)
            )
            messages.append(ProviderMessage(role="assistant", content=decision.response))
            response = decision.response
            stage_complete = decision.mark_stage_complete
            if not decision.tool_calls:
                break
            for call in decision.tool_calls:
                result = self.tools.run(agent.name, call.tool_name, ctx, **call.arguments)
                tool_actions.append({"tool": call.tool_name, "status": "completed"})
                tool_result = self._format_tool_result(call.tool_name, result)
                self.memory.append_message(
                    MessageRecord(session_id=session_id, role="tool", agent_name=agent.name, content=tool_result)
                )
                messages.append(ProviderMessage(role="tool", content=tool_result))
                if call.tool_name == "write_artifact":
                    artifacts_written.append({"id": result, "kind": str(call.arguments.get("kind", "artifact"))})
                if call.tool_name == "update_progress":
                    progress_updates.append(str(call.arguments.get("message", "")))
                if call.tool_name == "run_task_agent":
                    response = f"{response} {result.summary}".strip()
        else:
            response = f"{response} Iteration limit reached.".strip()
        return AgentOutcome(
            response=response,
            stage_complete=stage_complete,
            loaded_skills=[skill.name for skill in loaded_skill_defs],
            tool_actions=tool_actions,
            artifacts=artifacts_written,
            progress_updates=progress_updates,
        )

    def _format_tool_result(self, tool_name: str, result: object) -> str:
        if hasattr(result, "model_dump"):
            payload = result.model_dump()
        else:
            payload = result
        return f"Tool '{tool_name}' result: {payload}"
