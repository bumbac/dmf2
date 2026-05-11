# Product Requirements Document

## Product Name

dmf2-agents

## Product Summary

dmf2-agents is a controlled, engineering-first multi-agent orchestration system built in Python around LangGraph. It is not a general-purpose coding assistant. Its purpose is to execute configurable workflow definitions composed of explicit stages with stage-specific goals, scoped agents, reusable skills, durable memory, and observable progress.

The system accepts:

- a workflow configuration file that defines the ordered stages and their goals
- a user text message that provides request-specific context for the run

From that input, it creates or resumes a session, derives the initial plan from the configured workflow, routes work through the configured stages, tracks progress, writes optional artifacts, and optionally delegates bounded work to subagents.

## Problem Statement

Teams need agent systems that are easier to control, inspect, and reason about than chat-first coding assistants. Existing systems often optimize for autonomy before reliability. This product instead prioritizes:

- explicit stages over hidden internal reasoning
- scoped tools over unrestricted action
- durable state over ephemeral chat context
- observability over black-box behavior

## Goals

- Allow operators to configure a workflow file with ordered stages and stage-specific goals
- Assign specific agents to stages with explicit tool permissions
- Maintain usable context over long-running sessions through summaries, plans, progress, and artifacts
- Support subagent task execution with independent state and shared outcomes
- Persist all important state in PostgreSQL
- Expose progress and outputs in a way suitable for future API and UI clients
- Support at least one concrete end-to-end example workflow that transforms real input files into a real deliverable output

## Non-Goals

- Not a replacement for OpenCode or a full coding assistant shell
- No LSP integration
- No CrewAI, AutoGen, or similar opaque multi-agent framework
- No hidden agent autonomy without persisted state transitions and explicit routing

## Primary Users

- Engineers building workflow-driven agent systems
- Teams who need traceable stage-based automation
- Developers who want durable artifacts, summaries, and progress logs rather than pure chat transcripts

## Core User Experience

1. Operator selects a workflow configuration file
2. User submits a text request
3. System creates a session and derives the initial plan from the configured workflow
4. System runs configured stages in order
5. Each stage invokes an assigned agent with only its allowed tools and skills
6. Agents write progress updates and optional artifacts as they work
7. Stages advance only when the evaluator determines the stage goal has been met
8. Subagents can be called as independent tasks when needed
9. Session ends with a clear set of summaries, progress history, optional artifacts, and stage outcomes

## Functional Requirements

### Session Management

- The system must create a durable session for each request
- The system must persist messages, summaries, plans, progress, artifacts, and events
- The system should support parent-child session lineage for task delegation

### Stage Orchestration

- The system must load a configurable ordered workflow definition from a configuration file
- Each stage must have an id, name, goal, and assigned agents
- The workflow configuration must be the primary source for stage ordering and initial plan structure
- Each stage may include descriptive completion guidance, but stage completion must be determined by evaluator logic against the stage goal
- Stage completion must be evaluated based on whether the stage goal has been met
- The evaluator must use persisted context including chat history, progress, and relevant outputs
- The evaluator should use an LLM-based judgment step behind a bounded provider interface
- Stage completion must not depend solely on artifact existence
- Required output artifact declarations must not be necessary for stage completion
- The system must route across stages using LangGraph
- The system must halt or fail cleanly when a stage cannot be executed

### Agents

- Agents must be configurable and addressable by name
- Each agent must have a system prompt, mode, allowed tools, allowed skills, and iteration limits
- The planner agent must be allowed to inspect files and run shell commands for read-only analysis
- The planner agent must not be allowed to write files or otherwise modify code
- Agents must not be able to use tools outside their permissions
- Agents must be able to request subagent work through a task mechanism

### Tools

- Tools must be discoverable and scoped to agents
- Tools must support permission checks before execution
- Initial tool set must include file read, file write, shell command execution, artifact writing, progress updates, skill loading, and task delegation

### Example Workflow Execution

- The system must be able to run a concrete example workflow from checked-in sample input files to checked-in or generated output artifacts
- The first example workflow must use `data/example/migration-clean/input` as input and produce Oracle-compatible migration outputs
- The example workflow must not rely on live database access and must operate purely from provided files and persisted session state
- The system must persist enough output for an operator to inspect what was read, what was produced, and whether validation passed

### Skills

- Skills must be loaded from `SKILL.md` files
- Skills must provide reusable instruction bundles that can be injected into agent context
- Skills should be selectively available per agent

### Context Management

- The system must maintain chat history, a session summary, a current plan, progress entries, and artifacts
- The initial session plan must be derived from the configured workflow definition rather than a fixed generic template
- Prompt assembly must distinguish those context types clearly
- The system should compact or summarize long-running history rather than relying on full transcripts only

### Artifacts

- Artifacts must be first-class outputs with type, title, content, author, stage, and version
- Artifact versioning must be supported
- Artifacts must be accessible to later stages and subagents

### Events And Observability

- The system must emit events for session lifecycle, stage transitions, progress updates, and completion
- Event history must be persisted
- The system should later expose a streaming event interface for clients

## Current Implementation Status

Implemented now:

- Python project bootstrapped with `uv`
- PostgreSQL-backed storage layer and repository
- LangGraph-based stage loop
- Agent registry, stage registry, skill registry, and tool registry
- Prompt builder that includes summary, plan, progress, artifacts, and skills
- Artifact, progress, and event persistence
- CLI entrypoint for running a session with runtime workflow selection
- Child task sessions with parent-child linkage using the durable session model
- Explicit stage evaluator service wired into orchestration
- Stage loop accounting and halting behavior based on `max_loops`, including retry and halt events
- Tests for the current scaffold
- The runner now supports iterative provider turns with persisted tool-result messages between decisions
- Initial session plan generation derived from the configured workflow stages and goals
- Goal-based stage evaluation with structured pass/fail reasoning and per-stage evaluation mode overrides
- Planner read-only analysis permissions for file reads and shell commands
- LangChain-based Azure OpenAI adapter for structured output and tool-calling
- Live Azure tool-calling compatibility for strict schemas and multi-turn tool replay

Partially implemented:

- Summary generation exists but is simple and not model-backed
- Agent execution now has a provider-backed runtime boundary, with tests using explicit provider doubles and a LangChain Azure OpenAI adapter for structured output and tool-calling
- Parent-child lineage uses `parent_session_id`, but there are not yet dedicated lineage or stage-run tables
- Stage completion now uses an explicit evaluator and can be provider-backed, but evaluator evidence is still too permissive for workflows that require concrete deliverables
- A CLI session can be run end to end against the sample SQL migration prompt, and agents inspect the checked-in SQL inputs, but the sample still does not reliably produce Oracle migration deliverables or a validation report

Not yet implemented:

- HTTP API and event streaming
- Rich permission policies for commands and filesystem paths
- Resume and recovery flows
- A reliable file-based example workflow that reads `data/example/migration-clean/input` and writes real Oracle migration outputs
- A strict output contract, output file conventions, and validation rules for end-to-end example runs
- Prompt and evaluator constraints strong enough for the SQL-to-Oracle sample to produce and validate useful deliverables instead of generic notes

## Architecture Requirements

- LangGraph must be used as the orchestration and routing layer
- Business logic must remain outside LangGraph nodes wherever possible
- Tools, skills, memory, artifacts, events, and storage must remain separate services
- Shared state must be explicit and persisted
- PostgreSQL must be the primary durable store

## Acceptance Criteria For Next Milestone

- A live model-backed agent runner can complete at least one full staged workflow against a concrete deliverable contract
- Session summaries remain bounded as session length grows
- Progress and events are queryable through a thin service interface
- The checked-in SQL migration example can be executed locally end to end and produce Oracle-compatible output artifacts that are inspectable after the run

Implementation note for the completed delegation milestone:

- Child task sessions should reuse the parent stage definition for context and completion semantics in the first implementation rather than introducing a new task-stage model
- Parent-child lineage should use the existing durable session model before adding dedicated lineage tables

Implementation note for the next orchestration milestone:

- The workflow configuration file should define stages and goals and should be the source of stage ordering and initial plan structure
- The evaluator should determine stage completion by assessing whether the stage goal has been met using persisted session context
- Artifact existence may remain a useful signal, but it must not be the deciding completion mechanism
- The evaluator should sit behind the existing provider boundary so orchestration remains separate from model-specific code
- Loop accounting should remain in orchestration state so the system can halt deterministically when a stage exceeds `max_loops`

Implementation note after the completed orchestration milestone:

- Stage advancement now depends on an explicit evaluator service rather than the runner's completion flag
- The current evaluator can perform provider-backed judgment against the stage goal, but its evidence and prompt contract still need tightening for concrete file-output workflows
- Workflow selection and initial plan derivation are now driven by the configured workflow file
- Workflow stages now own agent assignment, and stage names are descriptive labels rather than behavior-carrying identifiers

Implementation note for the live-model milestone:

- The runner must remain responsible for tool execution, persistence, and permission enforcement
- Provider adapters may use structured output and tool-calling features, but must return normalized decisions rather than execute tools directly
- The model integration layer should be shaped like a swappable gateway client so model names, endpoints, and runtime parameters can change without changing orchestration code
- The current live-model implementation uses `langchain-openai` with Azure OpenAI and must preserve normalized decisions and tool-call replay semantics at the provider boundary

Implementation note for the first real example milestone:

- The first end-to-end example should be treated as a product requirement, not just a demo prompt
- The example should have explicit input discovery, output location, and validation expectations so success does not depend on generic stage notes
- The live-model path should reuse the same stages, artifacts, and output contract as the general runtime path

## Open Questions

- Which provider abstraction should be introduced first beyond Azure OpenAI support?
- What is the smallest reliable prompt contract for LLM-based stage evaluation against a stage goal?
- Should stage evaluation use the same provider configuration as agent execution or a dedicated evaluator model or profile?
- Should workflow configuration remain YAML-first or move into a richer config model later?
- How strict should shell command policies be in the first live-model milestone?
- What is the smallest useful HTTP API surface for the next iteration?
- Should the first example workflow write final outputs only as persisted artifacts, or also materialize files under a checked output directory such as `data/example/migration-clean/output`?
