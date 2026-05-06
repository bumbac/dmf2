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

The current codebase is a functional scaffold with a working provider boundary, and it now includes real child task sessions, but it is not yet a finished product.

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
- Child task session creation and parent-child linkage in `src/dmf2_agents/tasks.py`
- Bootstrap and CLI entrypoint in `src/dmf2_agents/bootstrap.py` and `src/dmf2_agents/cli.py`
- Tests covering core registry, prompting, persistence, permissions, and orchestration behavior

Implemented but intentionally simplified:

- The `AgentRunner` routes decisions through a provider abstraction with a deterministic stub backend by default and an Azure OpenAI adapter when configured, but the live path has only been validated through narrow adapter tests rather than a full end-to-end staged workflow
- `run_task_agent` now spawns a true child session and returns a structured task result, but task semantics still reuse the parent stage context and there are not yet dedicated lineage tables
- Stage completion is still driven by the runner directly, not by evaluating explicit completion conditions or required artifacts
- Summary generation is a simple rolling summary over recent messages, not model-generated compaction
- Tool discoverability exists in code, but there is not yet an external session API or event stream surface
- Stage definitions include `completion_conditions`, `output_artifacts`, and `max_loops`, but orchestration does not yet evaluate or enforce them

Not yet implemented:

- Stage completion evaluators based on artifact existence, validation checks, or task outputs
- Stage loop accounting and clean halting when a stage exceeds `max_loops`
- HTTP API for session creation, monitoring, and event streaming
- Richer permission policies by stage, path, or command patterns
- Resume behavior for existing sessions and tasks
- Dedicated tables for stage runs and task lineage

## Next Steps

### 1. Add explicit stage completion evaluators

Status: next

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

### 2. Enforce stage loop limits and halting behavior

Why:

- The current orchestration loop can continue indefinitely when a stage never satisfies completion conditions
- `StageDefinition.max_loops` already exists in the model and should become active behavior

What to implement:

- Track stage attempt counts in orchestration state
- Halt or fail the session cleanly when a stage exceeds `max_loops`
- Emit explicit events when a stage is retried and when it halts because loop limits are reached
- Keep loop enforcement in orchestration rather than provider logic

Definition of done:

- A non-completing stage stops after its configured number of attempts
- The session is marked failed with clear stage-level events and persisted state
- Tests cover retry and halt behavior

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

1. Stage evaluators
2. Stage loop enforcement and halting
3. End-to-end live model validation
4. Better summary and context compaction
5. HTTP API and event streaming
6. Permission hardening

This order preserves momentum while keeping risk low. Task delegation is now real enough for the current milestone, so the next priority is to make stage completion and failure semantics reliable before expanding the external surface.

## Risks And Constraints

- Reusing the parent stage definition for child task context is intentionally minimal, but it means task semantics stay coupled to the parent stage until a richer task model exists
- Stage evaluators can become too implicit if `completion_conditions` stay free-form without a clear initial contract
- Loop enforcement must avoid masking useful retries while still preventing infinite stage churn
- Real model integration can still blur separation of concerns if tool logic leaks into provider code
- Shell and filesystem tools become a real safety concern once live model execution is enabled
- Prompt growth will become a practical issue quickly after enabling live model reasoning
- Postgres schema is still minimal and may need migrations once stage runs and task lineage are introduced

## Testing Plan For Next Iterations

Add tests for:

- Real provider adapter behavior behind a small mocked boundary
- Stage evaluator success and failure paths
- Stage retry and halt behavior based on `max_loops`
- End-to-end live-model workflow behavior once a safe integration test path exists
- Summary compaction behavior on longer sessions
- Path and command permission enforcement
- API-level session lifecycle behavior
