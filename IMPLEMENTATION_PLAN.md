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

Reality check after running the checked-in SQL migration example:

- The end-to-end CLI session completes successfully against `data/example/migration-clean/input`
- The current default backend is still the deterministic stub path unless live model settings are present
- The sample run proves stage orchestration, persistence, and iterative tool-result feedback, but it does not yet produce real Oracle migration deliverables
- The current stub backend repeatedly writes generic stage artifacts until the per-agent iteration limit, so the example is not yet a true file-to-output workflow

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
- Iterative provider turns in `src/dmf2_agents/runner.py`, with persisted assistant and tool-result messages between decisions
- Child task session creation and parent-child linkage in `src/dmf2_agents/tasks.py`
- Bootstrap and CLI entrypoint in `src/dmf2_agents/bootstrap.py` and `src/dmf2_agents/cli.py`
- Artifact-based stage completion that requires matching `stage_id` and artifact kind for the active stage
- Stage loop accounting and clean halting when a stage exceeds `max_loops`
- Tests covering core registry, prompting, persistence, permissions, and orchestration behavior

Implemented but intentionally simplified:

- The `AgentRunner` now supports iterative provider turns and feeds tool results back into the provider, but the live path has not yet been validated through a real domain-specific staged workflow that produces deliverable files
- `run_task_agent` now spawns a true child session and returns a structured task result, but task semantics still reuse the parent stage context and there are not yet dedicated lineage tables
- Summary generation is a simple rolling summary over recent messages, not model-generated compaction
- Tool discoverability exists in code, but there is not yet an external session API or event stream surface
- Stage completion currently supports artifact-based evaluation only; richer validation checks, task-result signals, and parsed completion-condition policies are not yet implemented
- The provider contract still includes `mark_stage_complete`, but orchestration no longer uses it to advance stages
- The checked-in SQL migration example can be invoked through the CLI, but it still yields generic note artifacts instead of Oracle migration outputs

Not yet implemented:

- Richer stage completion evaluators based on validation checks, task outputs, or parsed `completion_conditions`
- HTTP API for session creation, monitoring, and event streaming
- Richer permission policies by stage, path, or command patterns
- Resume behavior for existing sessions and tasks
- Dedicated tables for stage runs and task lineage
- A deterministic example workflow path that reads `data/example/migration-clean/input` and writes real Oracle migration output
- Sample-specific prompts, stages, and validation artifacts for the SQL-to-Oracle example
- Output file conventions for generated example results

## Next Steps

### 1. Make the checked-in SQL migration example run end to end

Status: next

Why:

- A local end-to-end example is now a concrete product need, not just a nice-to-have demo
- The current sample run completes structurally but does not produce usable migration output
- A deterministic example path will make it much easier to validate the live-model path afterward

What to implement:

- Add explicit workflow conventions for the example input at `data/example/migration-clean/input`
- Make the execution path read the example SQL files and produce Oracle-compatible output artifacts, and likely output files, instead of generic stage notes
- Add a deterministic local success path for the sample when the backend is `stub`
- Add validation that checks for expected deliverables, not just artifact existence
- Ensure the final outputs are easy to inspect after the run

Definition of done:

- Running the CLI against the SQL migration sample produces Oracle-oriented outputs derived from the checked-in input files
- The sample run succeeds locally without requiring a live model
- Tests cover the deterministic example path and its output contract

### 2. Prove the live model-backed runner end to end

Status: after example workflow

Why:

- The provider boundary and Azure adapter exist, but the codebase has not yet proven a full staged workflow against a live model
- The product goal still requires confidence that model decisions map cleanly into controlled tool execution
- The local deterministic example path should define the same output contract the live model will need to satisfy

What to implement:

- Exercise the existing provider path against a real staged session
- Tighten the runtime contract around tool calls, final response content, and completion signals
- Keep the current boundaries intact: prompt building, tool execution, permissions, and persistence should remain outside the provider client
- Preserve the stub backend as the default fast test path

Definition of done:

- A live model-backed session can complete at least one staged workflow
- Existing tests remain green and additional coverage exists around provider decisions in runner and orchestration boundaries

### 3. Improve context management and summarization

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

### 4. Add a service API and event streaming surface

Why:

- The current CLI is enough for local testing but not for product usage
- Monitoring progress and state is a core requirement

What to implement:

- Add a thin HTTP API for starting sessions, inspecting sessions, listing artifacts, and reading progress
- Add event streaming, likely via SSE
- Keep transport thin and route all behavior through existing services

Definition of done:

- A client can create a session with a text message and monitor stages, progress, and events in real time

### 5. Harden tool permissions and execution controls

Why:

- The product must remain controlled and engineering-first as more autonomy is introduced

What to implement:

- Add policy checks for filesystem paths and shell commands
- Add stage-specific tool restrictions in addition to agent-specific restrictions
- Add structured logging around tool execution and failures

Definition of done:

- Disallowed tools, commands, and paths fail consistently with clear errors
- Tests cover allowed and denied paths

### 6. Extend stage evaluators beyond artifact existence

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

### 7. Add resume behavior and richer persistence for orchestration lineage

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
2. Deterministic checked-in example workflow
3. Better summary and context compaction
4. HTTP API and event streaming
5. Permission hardening
6. Richer stage evaluators
7. Resume behavior and lineage persistence

This order preserves momentum while keeping risk low. The checked-in example should become a real file-to-output workflow first, because it creates a concrete contract for both the deterministic stub path and the live-model path before expanding the external surface.

## Risks And Constraints

- Reusing the parent stage definition for child task context is intentionally minimal, but it means task semantics stay coupled to the parent stage until a richer task model exists
- Real model integration can still blur separation of concerns if tool logic leaks into provider code
- Shell and filesystem tools become a real safety concern once live model execution is enabled
- Prompt growth will become a practical issue quickly after enabling live model reasoning
- Artifact-based stage completion is intentionally narrow and may not cover all workflow semantics without expanding evaluator inputs
- Postgres schema is still minimal and may need migrations once stage runs and task lineage are introduced
- A generic scaffold pipeline can appear healthy while still failing the product need for a concrete end-to-end example
- If the stub path stays too generic, local development will continue to validate orchestration rather than real deliverable generation

## Testing Plan For Next Iterations

Add tests for:

- Deterministic example workflow behavior for `data/example/migration-clean/input`
- Expected Oracle-oriented output artifacts or files from the example run
- Real provider adapter behavior behind a small mocked boundary
- End-to-end live-model workflow behavior once a safe integration test path exists
- Summary compaction behavior on longer sessions
- Path and command permission enforcement
- Richer evaluator behavior once validation and task-result signals are introduced
- Resume and lineage behavior once dedicated persistence is added
- API-level session lifecycle behavior
