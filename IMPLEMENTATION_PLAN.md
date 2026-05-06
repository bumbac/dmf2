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
- Stage evaluator service in `src/dmf2_agents/evaluators.py`
- Provider abstraction with a deterministic stub backend and Azure OpenAI adapter in `src/dmf2_agents/providers.py`
- Child task session creation and parent-child linkage in `src/dmf2_agents/tasks.py`
- Bootstrap and CLI entrypoint in `src/dmf2_agents/bootstrap.py` and `src/dmf2_agents/cli.py`
- Artifact-based stage completion that requires matching `stage_id` and artifact kind for the active stage
- Stage loop accounting and clean halting when a stage exceeds `max_loops`
- Tests covering core registry, prompting, persistence, permissions, and orchestration behavior

Implemented but intentionally simplified:

- The `AgentRunner` routes decisions through a provider abstraction with a deterministic stub backend by default and an Azure OpenAI adapter when configured, but the live path has only been validated through narrow adapter tests rather than a full end-to-end staged workflow
- `run_task_agent` now spawns a true child session and returns a structured task result, but task semantics still reuse the parent stage context and there are not yet dedicated lineage tables
- Summary generation is a simple rolling summary over recent messages, not model-generated compaction
- Tool discoverability exists in code, but there is not yet an external session API or event stream surface
- Stage completion currently supports artifact-based evaluation only; richer validation checks, task-result signals, and parsed completion-condition policies are not yet implemented
- The provider contract still includes `mark_stage_complete`, but orchestration no longer uses it to advance stages

Not yet implemented:

- Richer stage completion evaluators based on validation checks, task outputs, or parsed `completion_conditions`
- HTTP API for session creation, monitoring, and event streaming
- Richer permission policies by stage, path, or command patterns
- Resume behavior for existing sessions and tasks
- Dedicated tables for stage runs and task lineage

## Next Steps

### 1. Prove the live model-backed runner end to end

Status: next

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

### 2. Improve context management and summarization

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

### 3. Add a service API and event streaming surface

Why:

- The current CLI is enough for local testing but not for product usage
- Monitoring progress and state is a core requirement

What to implement:

- Add a thin HTTP API for starting sessions, inspecting sessions, listing artifacts, and reading progress
- Add event streaming, likely via SSE
- Keep transport thin and route all behavior through existing services

Definition of done:

- A client can create a session with a text message and monitor stages, progress, and events in real time

### 4. Harden tool permissions and execution controls

Why:

- The product must remain controlled and engineering-first as more autonomy is introduced

What to implement:

- Add policy checks for filesystem paths and shell commands
- Add stage-specific tool restrictions in addition to agent-specific restrictions
- Add structured logging around tool execution and failures

Definition of done:

- Disallowed tools, commands, and paths fail consistently with clear errors
- Tests cover allowed and denied paths

### 5. Extend stage evaluators beyond artifact existence

Why:

- Artifact presence is the right first persisted signal, but it is not sufficient for all stages
- Some workflows will need validation results, task outputs, or explicit parsed policies to determine completion

What to implement:

- Extend the evaluator to support validation artifacts and task-result presence
- Decide whether `completion_conditions` should become a small parsed policy format
- Keep the current artifact-based path as the simplest default behavior

Definition of done:

- Stages can require more than artifact existence without leaking completion logic back into the runner
- Tests cover multi-signal completion and failure paths

### 6. Add resume behavior and richer persistence for orchestration lineage

Why:

- The session model is durable, but the system still starts fresh for each top-level run
- Longer-running workflows will need better recovery and inspectable stage/task lineage

What to implement:

- Add resume behavior for existing sessions and tasks
- Introduce dedicated persistence for stage runs and task lineage when the current session model becomes too coarse
- Keep recovery semantics explicit and observable in events

Definition of done:

- Existing sessions can resume deterministically
- Stage and task lineage are queryable without inferring everything from generic session rows

## Recommended Execution Order

1. End-to-end live model validation
2. Better summary and context compaction
3. HTTP API and event streaming
4. Permission hardening
5. Richer stage evaluators
6. Resume behavior and lineage persistence

This order preserves momentum while keeping risk low. Stage completion and failure semantics are now reliable enough for the current milestone, so the next priority is to validate the live-model path and improve context handling before expanding the external surface.

## Risks And Constraints

- Reusing the parent stage definition for child task context is intentionally minimal, but it means task semantics stay coupled to the parent stage until a richer task model exists
- Real model integration can still blur separation of concerns if tool logic leaks into provider code
- Shell and filesystem tools become a real safety concern once live model execution is enabled
- Prompt growth will become a practical issue quickly after enabling live model reasoning
- Artifact-based stage completion is intentionally narrow and may not cover all workflow semantics without expanding evaluator inputs
- Postgres schema is still minimal and may need migrations once stage runs and task lineage are introduced

## Testing Plan For Next Iterations

Add tests for:

- Real provider adapter behavior behind a small mocked boundary
- End-to-end live-model workflow behavior once a safe integration test path exists
- Summary compaction behavior on longer sessions
- Path and command permission enforcement
- Richer evaluator behavior once validation and task-result signals are introduced
- Resume and lineage behavior once dedicated persistence is added
- API-level session lifecycle behavior
