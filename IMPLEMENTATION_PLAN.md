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

## Runtime Problem Definition

The runtime now uses the workflow configuration file as the primary source of stage ordering and initial plan structure. The intended model is:

- the workflow configuration file defines the ordered stages and their goals
- the user prompt provides request-specific context for a run of that workflow

The runtime should continue to derive both stage routing and the initial session plan from the workflow configuration, with the user prompt supplying request-specific context for a run of that workflow.

The current codebase is a functional scaffold with a working provider boundary, and it now includes real child task sessions, but it is not yet a finished product.

Reality check after running the checked-in SQL migration example:

- The end-to-end CLI session completes successfully against `data/example/migration-clean/input`
- The live Azure path has now been exercised end to end through the provider boundary using `langchain-openai`
- The sample run proves stage orchestration, persistence, iterative tool-result feedback, and live-model tool-calling, but it still does not consistently produce real Oracle migration deliverables
- The example is still not yet a reliable file-to-output workflow with a concrete deliverable contract

Implemented:

- `uv` project setup with Python package metadata and dependencies in `pyproject.toml`
- PostgreSQL-backed persistence via SQLAlchemy in `src/dmf2_agents/storage.py`
- Durable repository for sessions, messages, summaries, plans, progress, artifacts, and events in `src/dmf2_agents/repository.py`
- Domain models in `src/dmf2_agents/domain.py`
- Skill discovery from `skills/**/SKILL.md` in `src/dmf2_agents/skills.py`
- Stage registry from a YAML workflow file in `src/dmf2_agents/stages.py`
- Agent registry with scoped tools in `src/dmf2_agents/agents.py`
- Tool registry with permission checks in `src/dmf2_agents/tools.py`
- Memory, artifact, and event services in `src/dmf2_agents/memory.py`, `src/dmf2_agents/artifacts.py`, and `src/dmf2_agents/events.py`
- Prompt assembly from summary, plan, progress, artifacts, and skills in `src/dmf2_agents/prompting.py`, including structured artifact references and load hints
- LangGraph stage loop in `src/dmf2_agents/orchestrator.py`
- Stage evaluator service in `src/dmf2_agents/evaluators.py`
- Provider abstraction with a LangChain-based Azure OpenAI adapter in `src/dmf2_agents/providers.py`
- Iterative provider turns in `src/dmf2_agents/runner.py`, with persisted assistant and tool-result messages between decisions
- Child task session creation and parent-child linkage in `src/dmf2_agents/tasks.py`
- Bootstrap and CLI entrypoint in `src/dmf2_agents/bootstrap.py` and `src/dmf2_agents/cli.py`
- Stage evaluator service integrated into orchestration
- Stage loop accounting and clean halting when a stage exceeds `max_loops`
- Runtime workflow selection through CLI/bootstrap and workflow-derived initial session plans
- Goal-shaped stage evaluation results with provider-backed evaluation support and per-stage evaluation mode overrides
- Planner read-only analysis permissions for file reads and shell commands
- Live Azure tool-calling compatibility fixes for multi-turn tool replay and strict tool schemas
- Workflow-defined agent assignment with arbitrary stage names and no stage-role coupling in agent definitions
- Artifact persistence to PostgreSQL plus file-backed copies under `runtime/artifacts/**`, with persisted `file_path` references and `storage_kind`
- Explicit fake-provider-based tests instead of a checked-in stub runtime backend
- Tests covering core registry, prompting, persistence, permissions, and orchestration behavior

Implemented but intentionally simplified:

- The `AgentRunner` now supports iterative provider turns and feeds tool results back into the provider, and the live Azure path has been validated through staged sessions, but the checked-in migration workflow still does not reliably produce deliverable files
- `run_task_agent` now spawns a true child session and returns a structured task result, but task semantics still reuse the parent stage context and there are not yet dedicated lineage tables
- Summary generation is a simple rolling summary over recent messages, not model-generated compaction
- Tool discoverability exists in code, but there is not yet an external session API or event stream surface
- Stage evaluation is now routed through an evaluator service and can use provider-based judgment, but the evaluator evidence and prompt are still too permissive for the migration workflow
- Artifact prompts now expose title, content, file reference, and a load hint, but artifact authoring conventions such as chunk labeling are still guided by prompt instructions rather than enforced by tool schema
- The checked-in SQL migration example can be invoked through the CLI and the agents do inspect the checked-in input files, but the workflow still tends to stall before writing Oracle migration outputs and grounded validation evidence

Not yet implemented:

- HTTP API for session creation, monitoring, and event streaming
- Richer permission policies by stage, path, or command patterns
- Resume behavior for existing sessions and tasks
- Dedicated tables for stage runs and task lineage
- A reliable example workflow path that reads `data/example/migration-clean/input` and writes real Oracle migration output files
- Validator guidance and evaluator evidence strong enough for the SQL-to-Oracle example to produce inspectable outputs and let the validator determine goal completion from grounded inspection rather than rigid file checks
- Evaluator evidence and prompts strong enough to reject stages that only inspect files shallowly without producing or validating meaningful deliverables
- Output file conventions for generated example results
- A dedicated artifact-loading tool or richer artifact retrieval API beyond persisted file references in prompt context
- A real schema migration path for existing PostgreSQL databases instead of relying on `create_all()` for fresh databases only

## Next Steps

### 1. Make workflow configuration the source of runtime structure

Status: completed

Why:

- The current runtime still starts from a raw user prompt plus a hardcoded pipeline path
- The product needs the workflow definition to be the source of stage ordering, stage goals, and initial plan structure
- This makes runs more controllable, inspectable, and reusable across sessions

What to implement:

- Load the workflow file from runtime configuration instead of a hardcoded bootstrap path
- Use the workflow definition to determine the ordered pipeline
- Generate the initial session plan from the configured stages and goals
- Remove the requirement to declare output artifacts in the workflow config

Definition of done:

- A session can be started against a selected workflow file
- The runtime stage queue comes from that workflow file
- The initial persisted plan is derived from configured stages and goals
- Workflow configs do not need `output_artifacts` to function

### 2. Replace artifact-based completion with goal-based evaluation

Status: mostly completed

Why:

- Artifact existence is not a reliable proxy for stage completion
- The product requirement is that stages advance when their goals are actually met
- The evaluator should use persisted context rather than depend on a narrow artifact contract

What to implement:

- Replace artifact-existence evaluation with LLM-based evaluation against the stage goal
- Provide the evaluator with persisted chat history, progress, and relevant outputs
- Keep evaluator logic behind the provider boundary
- Return structured evaluation results with pass or fail and reasoning

Definition of done:

- Stage completion is based on whether the evaluator judges the stage goal satisfied
- Artifacts are optional supporting evidence, not a required completion contract
- Tests cover success and failure cases for goal-based evaluation
- Remaining gap: evaluator prompts and evidence still need tightening for workflows that require concrete deliverables, while keeping completion goal-based rather than tied to rigid file existence or artifact shape checks

### 3. Expand planner to support read-only analysis

Status: completed

Why:

- The planner needs to inspect files and run read-only shell commands to form useful stage understanding
- This increases planning quality without granting write access

What to implement:

- Add file-read and shell-command permissions to the planner agent
- Keep file-write and code-modification capabilities disabled for the planner
- Add tests that verify planner can inspect but not modify

Definition of done:

- Planner can read files and run shell commands
- Planner cannot write files or otherwise modify code
- Permission tests cover both allowed and denied operations

### 4. Make the checked-in SQL migration example run end to end

Status: next

Why:

- A local end-to-end example is now a concrete product need, not just a nice-to-have demo
- The current sample run completes structurally but does not produce usable migration output
- The example needs grounded, inspectable validation, but success should still depend on whether the validator judges the stage goal met rather than on rigid file checklists

What to implement:

- Add explicit workflow conventions for the example input at `data/example/migration-clean/input`
- Make the execution path read the example SQL files and produce Oracle-compatible output artifacts and output files instead of generic stage notes
- Strengthen prompt and validation guidance so the validator inspects produced outputs, persisted artifacts, progress, and request context before deciding whether the validation goal is met
- Ensure the final outputs are easy to inspect after the run

Definition of done:

- Running the CLI against the SQL migration sample produces Oracle-oriented outputs derived from the checked-in input files
- Validation remains goal-based and is grounded in inspectable evidence gathered by the validator from produced files and persisted context
- Tests cover the example path and the validator's grounded inspection behavior

### 5. Prove the live model-backed runner end to end

Status: partially completed

Why:

- The provider boundary and Azure adapter exist, but the codebase has not yet proven a full staged workflow against a live model
- The product goal still requires confidence that model decisions map cleanly into controlled tool execution
- The checked-in example path should define the same inspectable output surface and grounded validation behavior the live model will need to satisfy

What to implement:

- Exercise the existing provider path against a real staged session
- Tighten the runtime contract around tool calls, final response content, and completion signals
- Keep the current boundaries intact: prompt building, tool execution, permissions, and persistence should remain outside the provider client

Definition of done:

- A live model-backed session can complete at least one staged workflow
- Existing tests remain green and additional coverage exists around provider decisions in runner and orchestration boundaries
- Remaining gap: the live migration workflow still needs to produce real inspectable deliverables and grounded validation evidence rather than merely complete structurally

### 5a. Add database schema migrations for durable environments

Status: next

Why:

- The current bootstrap path calls `Base.metadata.create_all(...)`, which only creates missing tables for fresh databases
- Existing PostgreSQL databases are not upgraded when ORM models change, which already caused runtime failures for new artifact columns such as `storage_kind` and `file_path`
- Durable environments need an explicit, versioned schema migration path before more persistence changes land

What to implement:

- Introduce a real migration toolchain for the PostgreSQL schema, such as Alembic
- Create a baseline migration for the current schema and a follow-up migration for the newer artifact storage columns
- Document how operators apply migrations locally and in deployed environments
- Stop relying on `create_all()` as the only schema-update mechanism for long-lived databases

Definition of done:

- An existing PostgreSQL database can be upgraded to the current schema without manual SQL edits
- The runtime can start successfully against a migrated database that includes artifact file persistence columns
- The repository includes versioned migration files and operator-facing usage instructions

### 6. Add a service API and event streaming surface

Why:

- The current CLI is enough for local testing but not for product usage
- Monitoring progress and state is a core requirement

What to implement:

- Add a thin HTTP API for starting sessions, inspecting sessions, listing artifacts, and reading progress
- Add event streaming, likely via SSE
- Keep transport thin and route all behavior through existing services

Definition of done:

- A client can create a session with a text message and monitor stages, progress, and events in real time

### 7. Harden tool permissions and execution controls

Why:

- The product must remain controlled and engineering-first as more autonomy is introduced

What to implement:

- Add policy checks for filesystem paths and shell commands
- Add stage-specific tool restrictions in addition to agent-specific restrictions
- Add structured logging around tool execution and failures

Definition of done:

- Disallowed tools, commands, and paths fail consistently with clear errors
- Tests cover allowed and denied paths

### 8. Improve context management and summarization

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

### 9. Add resume behavior and richer persistence for orchestration lineage

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

1. Workflow-driven runtime structure
2. Goal-based stage evaluation
3. Planner read-only analysis permissions
4. Checked-in example workflow with grounded validation
5. End-to-end live model validation against that contract
6. Database schema migrations for durable environments
7. HTTP API and event streaming
8. Permission hardening
9. Better summary and context compaction
10. Resume behavior and lineage persistence

This order still preserves momentum while keeping risk low. The runtime is now workflow-config-driven and goal-evaluated, so the next risk-reducing step is to make the checked-in example produce inspectable outputs with grounded validation before relying on the live path for product confidence.

## Risks And Constraints

- Reusing the parent stage definition for child task context is intentionally minimal, but it means task semantics stay coupled to the parent stage until a richer task model exists
- Real model integration can still blur separation of concerns if tool logic leaks into provider code
- Shell and filesystem tools become a real safety concern once live model execution is enabled
- Prompt growth will become a practical issue quickly after enabling live model reasoning
- Goal-based LLM evaluation can become too permissive or too strict if the evaluator prompt and evidence set are weak
- Without stage-scoped message metadata, evaluator context may include more session history than ideal
- Allowing planner read access to shell commands requires clear read-only expectations and future command-policy hardening
- A workflow config that defines stages and goals well is now more important because it becomes part of the runtime contract rather than passive metadata
- Postgres schema updates are not versioned today; `create_all()` is sufficient for fresh databases but not for upgrading durable environments
- A generic scaffold pipeline can appear healthy while still failing the product need for a concrete end-to-end example
- Validation quality depends on the validator actually inspecting the produced outputs and persisted evidence with its available tools; weak guidance can still lead to shallow approval

## Testing Plan For Next Iterations

Add tests for:

- Example workflow behavior for `data/example/migration-clean/input`
- Expected Oracle-oriented output artifacts or files from the example run
- Real provider adapter behavior behind a small mocked boundary
- End-to-end live-model workflow behavior once a safe integration test path exists
- Summary compaction behavior on longer sessions
- Path and command permission enforcement
- Goal-based evaluator behavior using persisted context and validator-grounded inspection of produced outputs
- Workflow-selected pipeline loading and plan derivation
- Planner permission behavior for read-only inspection
- Resume and lineage behavior once dedicated persistence is added
- API-level session lifecycle behavior
