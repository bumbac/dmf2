from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, StateGraph

from .agents import AgentRegistry
from .artifacts import ArtifactService
from .domain import EventRecord, MessageRecord, SessionRecord
from .evaluators import StageEvaluator
from .events import EventBus
from .memory import MemoryService
from .repository import Repository
from .runner import AgentRunner
from .stages import StageRegistry


class GraphState(TypedDict):
    session_id: str
    user_input: str
    current_stage_id: str | None
    stage_queue: list[str]
    stage_attempts: dict[str, int]
    goal_reached: bool
    halted: bool


class SessionOrchestrator:
    def __init__(
        self,
        repository: Repository,
        memory: MemoryService,
        artifacts: ArtifactService,
        events: EventBus,
        stages: StageRegistry,
        agents: AgentRegistry,
        runner: AgentRunner,
        evaluator: StageEvaluator,
    ):
        self.repository = repository
        self.memory = memory
        self.artifacts = artifacts
        self.events = events
        self.stages = stages
        self.agents = agents
        self.runner = runner
        self.evaluator = evaluator
        self.graph = self._build_graph()

    def _build_plan(self, user_input: str) -> str:
        stages = "\n".join(
            f"- {index}. {stage.name}: {stage.goal}"
            for index, stage in enumerate(self.stages.list(), start=1)
        )
        return f"Request:\n{user_input}\n\nWorkflow Plan:\n{stages}"

    def _build_graph(self):
        graph = StateGraph(GraphState)
        graph.add_node("choose_stage", self._choose_stage)
        graph.add_node("run_stage", self._run_stage)
        graph.add_node("evaluate", self._evaluate)
        graph.set_entry_point("choose_stage")
        graph.add_edge("choose_stage", "run_stage")
        graph.add_edge("run_stage", "evaluate")
        graph.add_conditional_edges(
            "evaluate",
            self._route,
            {
                "next": "choose_stage",
                "end": END,
            },
        )
        return graph.compile()

    def run(self, user_input: str) -> str:
        session = self.repository.create_session(SessionRecord(title=user_input[:80] or "session"))
        self.memory.append_message(MessageRecord(session_id=session.id, role="user", content=user_input))
        self.memory.set_plan(session.id, self._build_plan(user_input))
        self.events.publish(EventRecord(session_id=session.id, event_type="session.started", payload={"title": session.title}))
        initial_state: GraphState = {
            "session_id": session.id,
            "user_input": user_input,
            "current_stage_id": None,
            "stage_queue": [item.id for item in self.stages.list()],
            "stage_attempts": {},
            "goal_reached": False,
            "halted": False,
        }
        final_state = self.graph.invoke(initial_state)
        self.memory.update_summary(session.id)
        self.repository.update_session_status(session.id, "completed" if final_state["goal_reached"] else "failed")
        self.events.publish(EventRecord(session_id=session.id, event_type="session.finished", payload=final_state))
        return session.id

    def _choose_stage(self, state: GraphState) -> GraphState:
        if not state["stage_queue"]:
            state["goal_reached"] = True
            return state
        stage_id = state["stage_queue"][0]
        state["current_stage_id"] = stage_id
        self.events.publish(EventRecord(session_id=state["session_id"], event_type="stage.entered", payload={"stage_id": stage_id}))
        return state

    def _run_stage(self, state: GraphState) -> GraphState:
        stage = self.stages.get(state["current_stage_id"] or "")
        if stage is None:
            state["halted"] = True
            return state
        agent_name = stage.assigned_agents[0]
        agent = self.agents.get(agent_name)
        if agent is None:
            state["halted"] = True
            return state
        attempts = dict(state["stage_attempts"])
        attempts[stage.id] = attempts.get(stage.id, 0) + 1
        state["stage_attempts"] = attempts
        outcome = self.runner.run(session_id=state["session_id"], stage=stage, agent=agent, user_input=state["user_input"])
        self.events.publish(
            EventRecord(
                session_id=state["session_id"],
                event_type="stage.progressed",
                payload={"stage_id": stage.id, "agent": agent.name, "response": outcome.response},
            )
        )
        return state

    def _evaluate(self, state: GraphState) -> GraphState:
        if state["halted"]:
            return state
        stage = self.stages.get(state["current_stage_id"] or "")
        if stage is None:
            state["halted"] = True
            return state
        evaluation = self.evaluator.evaluate(session_id=state["session_id"], stage=stage)
        if evaluation.passed:
            state["stage_queue"] = state["stage_queue"][1:]
            self.events.publish(
                EventRecord(session_id=state["session_id"], event_type="stage.completed", payload={"stage_id": stage.id})
            )
        else:
            attempt = state["stage_attempts"].get(stage.id, 0)
            payload = {
                "stage_id": stage.id,
                "attempt": attempt,
                "max_loops": stage.max_loops,
                "evaluation_reason": evaluation.reasoning,
                "evaluation_source": evaluation.source,
            }
            if attempt >= stage.max_loops:
                state["halted"] = True
                self.events.publish(
                    EventRecord(session_id=state["session_id"], event_type="stage.halted", payload=payload)
                )
            else:
                self.events.publish(
                    EventRecord(session_id=state["session_id"], event_type="stage.retry_scheduled", payload=payload)
                )
        if not state["stage_queue"]:
            state["goal_reached"] = True
        return state

    def _route(self, state: GraphState) -> str:
        if state["goal_reached"] or state["halted"]:
            return "end"
        return "next"
