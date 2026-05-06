# Implementation Plan

## Reference Structure

This implementation follows the OpenCode reference at a structural level, adapted to a stage-driven Python system.

1. Project and session surface
2. Agent registry and agent configuration
3. Session loop and routing graph
4. Tool registry and tool permissions
5. Skills loading and prompt injection
6. Memory, summaries, plans, and progress
7. Artifact persistence and versioning
8. Event emission for observability
9. Task-style subagent execution
10. Tests around orchestration boundaries

## Current Implementation Progress

The current codebase is a functional scaffold with a working provider boundary, but it is not yet a finished product.

Implemented:

- `uv` project setup with Python package metadata and dependencies in `pyproject.toml`
- PostgreSQL-backed persistence via SQLAlchemy in `src/dmf2_agents/storage.py`
- Durable repository for sessions, messages, summaries, plans, progress, artifacts, and events in `src/dmf2_agents/repository.py`
- Domain models in `src/dmf2_agents/domain.py`
- Skill discovery from `skills/**/SKILL.md` in `src/dmf2_agents/skills.py`
- Stage registry from `examples/pipeline.yaml` in `src/dmf2_agents/stages.py`
- Agent registry with scoped tools in `src/dmf2_agents/agents.py`
- Tool registry with permission checks in `src/dmf2_agents/tools.py`
- Memory, artifact, and event services in `src/dmf2_agents/memory.py`, `src/dmf2_agents/artifacts.py`, and `src/dmf2_agents/events.py`
- Prompt assembly from summary, plan, progress, artifacts, and skills in `src/dmf2_agents/prompting.py`
- LangGraph stage loop in `src/dmf2_agents/orchestrator.py`
- Provider abstraction with a deterministic stub backend and Azure OpenAI adapter in `src/dmf2_agents/providers.py`
- Bootstrap and CLI entrypoint in `src/dmf2_agents/bootstrap.py` and `src/dmf2_agents/cli.py`
- Tests covering core registry, prompting, persistence, permissions, and orchestration behavior

Implemented but intentionally simplified:

- The `AgentRunner` routes decisions through a provider abstraction with a deterministic stub backend by default and an Azure OpenAI adapter when configured, but the live path has only been validated through narrow adapter tests rather than a full end-to-end staged workflow
- `run_task_agent` returns a structured stub result rather than spawning a true child session
- Stage completion is driven by the runner directly, not by evaluating explicit completion conditions
- Summary generation is a simple rolling summary over recent messages, not model-generated compaction
- Tool discoverability exists in code, but there is not yet an external session API or event stream surface

Not yet implemented:

- True child task sessions with separate lineage, summaries, and persisted session records
- Stage completion evaluators based on artifact existence, validation checks, or task outputs
- HTTP API for session creation, monitoring, and event streaming
- Richer permission policies by stage, path, or command patterns
- Resume behavior for existing sessions and tasks
- Dedicated tables for stage runs and task lineage

## Next Steps

### 1. Implement true task sessions for subagents

Status: next

Why:

- The main architectural promise is independent agent execution with shared intermediate results and lineage
- The current `run_task_agent` stub does not create isolation, persistence, or resumability

What to implement:

- Add task session creation linked to a parent session
- Reuse the parent stage definition as the child session context rather than inventing a synthetic task stage
- Persist parent-child session lineage explicitly through `parent_session_id`
- Allow child sessions to have their own messages, summaries, progress, and artifacts
- Return a structured `TaskResult` containing task id, summary, artifact ids, and recommended next action

Definition of done:

- Parent agent can spawn a reviewer or specialist subagent as a true child session
- Child outputs are persisted and visible to the parent session
- Tests validate lineage and independent state

### 2. Add explicit stage completion evaluators

Why:

- Right now stage completion is optimistic and immediate
- The product needs stage goals and completion criteria to be first-class, inspectable, and reliable

What to implement:

- Add a stage evaluator service that reads stage definitions and checks completion conditions
- Start with artifact-based completion using the declared `output_artifacts` for each stage
- Support later extension for validation artifacts, progress flags, and task result presence
- Move stage completion decisions out of `AgentRunner`

Definition of done:

- `SessionOrchestrator` advances stages only when evaluator rules pass
- Tests cover passing and failing stage transitions

### 3. Prove the live model-backed runner end to end

Why:

- The provider boundary and Azure adapter exist, but the codebase has not yet proven a full staged workflow against a live model
- The product goal still requires confidence that model decisions map cleanly into controlled tool execution

What to implement:

- Exercise the existing provider path against a real staged session
- Tighten the runtime contract around tool calls, final response content, and completion signals
- Keep the current boundaries intact: prompt building, tool execution, permissions, and persistence should remain outside the provider client
- Preserve the stub backend as the default fast test path

Definition of done:

- A live model-backed session can complete at least one staged workflow
- Existing tests remain green and additional coverage exists around provider decisions in runner and orchestration boundaries

### 4. Improve context management and summarization

Why:

- Context management is central to this product
- The current rolling summary is enough for scaffolding but not for long-running sessions

What to implement:

- Introduce summary thresholds based on message count or token estimates
- Separate full chat history from compact working summary
- Track current plan and stage-local handoff notes independently
- Add artifact references into prompt assembly rather than only listing artifact titles

Definition of done:

- Long sessions can continue with bounded prompt size
- Summary, plan, progress, and artifacts are all explicitly distinguishable in prompts and persistence

### 5. Add a service API and event streaming surface

Why:

- The current CLI is enough for local testing but not for product usage
- Monitoring progress and state is a core requirement

What to implement:

- Add a thin HTTP API for starting sessions, inspecting sessions, listing artifacts, and reading progress
- Add event streaming, likely via SSE
- Keep transport thin and route all behavior through existing services

Definition of done:

- A client can create a session with a text message and monitor stages, progress, and events in real time

### 6. Harden tool permissions and execution controls

Why:

- The product must remain controlled and engineering-first as more autonomy is introduced

What to implement:

- Add policy checks for filesystem paths and shell commands
- Add stage-specific tool restrictions in addition to agent-specific restrictions
- Add structured logging around tool execution and failures

Definition of done:

- Disallowed tools, commands, and paths fail consistently with clear errors
- Tests cover allowed and denied paths

## Recommended Execution Order

1. True task sessions and lineage
2. Stage evaluators
3. End-to-end live model validation
4. Better summary and context compaction
5. HTTP API and event streaming
6. Permission hardening

This order preserves momentum while keeping risk low. The provider boundary is already in place, so the next priority is to make delegation and completion reliable before expanding the external surface.

## Risks And Constraints

- Task sessions can become tangled with parent session state if lineage is not modeled explicitly
- Reusing the parent stage definition for child task context is intentionally minimal, but it means task semantics stay coupled to the parent stage until a richer task model exists
- Real model integration can still blur separation of concerns if tool logic leaks into provider code
- Shell and filesystem tools become a real safety concern once live model execution is enabled
- Prompt growth will become a practical issue quickly after enabling live model reasoning
- Postgres schema is still minimal and may need migrations once stage runs and task lineage are introduced

## Testing Plan For Next Iterations

Add tests for:

- Real provider adapter behavior behind a small mocked boundary
- Parent-child task session creation and persistence
- Stage evaluator success and failure paths
- End-to-end live-model workflow behavior once a safe integration test path exists
- Summary compaction behavior on longer sessions
- Path and command permission enforcement
- API-level session lifecycle behavior
