# dmf2-agents

Controlled, engineering-first multi-agent orchestration built in Python on top of LangGraph.

## Current State

The runtime is now functional beyond the initial scaffold. It currently supports:

- workflow-driven stage orchestration from YAML
- PostgreSQL-backed durable state for sessions, messages, plans, summaries, progress, artifacts, and events
- live Azure OpenAI tool-calling through a provider boundary
- scoped built-in agents with mode-specific prompts and permissions
- artifact persistence both in PostgreSQL and under `runtime/artifacts/**`
- goal-based stage evaluation with provider-backed judgment
- child task sessions with parent-child linkage

The checked-in SQL migration workflow now runs end to end:

```bash
uv run dmf2-agents --workflow examples/migration-clean.yaml "Do it"
```

In the current implementation, that workflow reads the checked-in SQL inputs under `data/example/migration-clean/input`, produces Oracle-oriented SQL files under `oracle/`, and runs a reviewer stage that inspects the generated outputs.

The migration example is functional, but not yet hardened into the final desired contract. Output paths are still model-chosen rather than forced into a canonical checked output directory such as `data/example/migration-clean/output`.

## Reference Structure

This project borrows selectively from the OpenCode reference implementation in `./tmp`.

1. Project and session surface
2. Agent registry and agent config
3. Session prompt loop
4. LLM adapter and tool wiring
5. Tool registry and tool definitions
6. Permissions and approvals
7. Skills loading and prompt injection
8. Memory and summaries
9. Events and streaming updates
10. Artifacts and session outputs

## What This Project Does

- Orchestrates configurable stages with explicit goals
- Assigns scoped agents to stages
- Tracks plans, summaries, progress, artifacts, and events
- Allows agents to call subagents as independent tasks
- Uses PostgreSQL for durable state
- Loads reusable `SKILL.md` instruction bundles
- Carries stage context forward through persisted messages, progress, and artifacts
- Persists artifact content both in PostgreSQL and as runtime files

## Built-in Agents

- `planner`
  - plan mode
  - read-only analysis
  - can read files, run commands, write artifacts, update progress, and delegate tasks
  - cannot write project files
- `builder`
  - build mode
  - can read files, write files, run commands, write artifacts, update progress, and delegate tasks
- `reviewer`
  - review mode
  - can read files, run inspection commands, write validation artifacts, and update progress
  - cannot write project files

Prompt assembly injects explicit system reminders for each mode:

- planner gets a read-only plan-mode reminder
- builder gets a build-switch reminder
- reviewer gets a validation reminder

Historical tool outputs are also propagated into later turns as persisted context so later stages can reason over prior inspection and execution results.

## Workflow Model

Workflows are defined in YAML. Each stage includes:

- `id`
- `name`
- `goal`
- `assigned_agents`
- `max_loops`
- optional `evaluation_mode`

The orchestrator:

1. creates a durable session
2. persists the user request
3. derives an initial plan from workflow stages
4. runs each stage through the assigned agent
5. evaluates the stage goal using persisted context
6. retries or halts when the goal is not yet met

## What This Project Does Not Do

- No LSP integration
- No opaque high-level agent framework beyond LangGraph as the routing engine
- No CrewAI or AutoGen
- No HTTP API or SSE event streaming yet
- No strict read-only shell policy enforcement for planner or reviewer yet
- No PostgreSQL migration toolchain yet

## Development

Install dependencies:

```bash
uv sync
```

Run tests:

```bash
uv run pytest
```

Run the CLI:

```bash
uv run dmf2-agents "Create a staged implementation plan for a Python API"
```

Run the migration workflow:

```bash
uv run dmf2-agents --workflow examples/migration-clean.yaml "Do it"
```

## Known Gaps

- The migration workflow currently writes output files arbitrarily instead of a canonical output directory.
- Stage evaluation is grounded in persisted evidence, but the validation contract is still looser than the final product target.
- Historical tool outputs are carried forward as system context rather than as a richer structured event model.
- Database schema evolution still relies on table creation for fresh setups; existing PostgreSQL instances still need explicit migrations.
