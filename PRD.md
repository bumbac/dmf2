# Product Requirements Document

## Product Name

dmf2-agents

## Product Summary

dmf2-agents is a controlled, engineering-first multi-agent orchestration system built in Python around LangGraph. It is not a general-purpose coding assistant. Its purpose is to execute configurable sequences of stages with explicit goals, scoped agents, reusable skills, durable memory, and observable progress.

The system accepts a user text message as the only interactive input. From that input, it creates or resumes a session, builds a plan, routes work through configured stages, tracks progress, writes artifacts, and optionally delegates bounded work to subagents.

## Problem Statement

Teams need agent systems that are easier to control, inspect, and reason about than chat-first coding assistants. Existing systems often optimize for autonomy before reliability. This product instead prioritizes:

- explicit stages over hidden internal reasoning
- scoped tools over unrestricted action
- durable state over ephemeral chat context
- observability over black-box behavior

## Goals

- Allow operators to configure a sequence of stages with stage-specific goals
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

1. User submits a text request
2. System creates a session and initial plan
3. System runs configured stages in order
4. Each stage invokes an assigned agent with only its allowed tools and skills
5. Agents write artifacts and progress updates as they work
6. Stages advance only when completion conditions are satisfied
7. Subagents can be called as independent tasks when needed
8. Session ends with a clear set of artifacts, summaries, and progress history

## Functional Requirements

### Session Management

- The system must create a durable session for each request
- The system must persist messages, summaries, plans, progress, artifacts, and events
- The system should support parent-child session lineage for task delegation

### Stage Orchestration

- The system must load a configurable ordered list of stages
- Each stage must have an id, name, goal, assigned agents, and completion conditions
- The system must route across stages using LangGraph
- The system must halt or fail cleanly when a stage cannot be executed

### Agents

- Agents must be configurable and addressable by name
- Each agent must have a system prompt, mode, allowed tools, allowed skills, and iteration limits
- Agents must not be able to use tools outside their permissions
- Agents must be able to request subagent work through a task mechanism

### Tools

- Tools must be discoverable and scoped to agents
- Tools must support permission checks before execution
- Initial tool set must include file read, file write, shell command execution, artifact writing, progress updates, skill loading, task delegation, and stage completion signaling

### Example Workflow Execution

- The system must be able to run a concrete example workflow from checked-in sample input files to checked-in or generated output artifacts
- The first example workflow must use `data/example/migration-clean/input` as input and produce Oracle-compatible migration outputs
- The example workflow must not rely on live database access and must operate purely from provided files and persisted session state
- The example workflow must have a deterministic success path for local development, even when a live model is not configured
- The system must persist enough output for an operator to inspect what was read, what was produced, and whether validation passed

### Skills

- Skills must be loaded from `SKILL.md` files
- Skills must provide reusable instruction bundles that can be injected into agent context
- Skills should be selectively available per agent

### Context Management

- The system must maintain chat history, a session summary, a current plan, progress entries, and artifacts
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
- CLI entrypoint for running a session
- Child task sessions with parent-child linkage using the durable session model
- Explicit stage evaluator logic based on persisted artifacts scoped by `stage_id` and artifact kind
- Stage loop accounting and halting behavior based on `max_loops`, including retry and halt events
- Tests for the current scaffold
- The runner now supports iterative provider turns with persisted tool-result messages between decisions

Partially implemented:

- Summary generation exists but is simple and not model-backed
- Agent execution now has a provider-backed runtime boundary, with deterministic stub execution for tests and an Azure OpenAI adapter for structured output and tool-calling
- Parent-child lineage uses `parent_session_id`, but there are not yet dedicated lineage or stage-run tables
- Stage completion currently starts with artifact-based evaluation from `output_artifacts`; `completion_conditions` remain descriptive and are not yet parsed as a richer policy format
- A CLI session can be run end to end against the sample SQL migration prompt, but the default stub backend still produces generic scaffold artifacts rather than Oracle migration deliverables

Not yet implemented:

- HTTP API and event streaming
- Rich permission policies for commands and filesystem paths
- Resume and recovery flows
- Richer stage evaluator logic for validation checks, task-result presence, and parsed completion-condition policies
- A deterministic file-based example workflow that reads `data/example/migration-clean/input` and writes real Oracle migration outputs
- Prompt and stage definitions specialized enough for the SQL-to-Oracle sample to produce useful deliverables instead of generic notes
- Output file conventions and validation rules for end-to-end example runs

## Architecture Requirements

- LangGraph must be used as the orchestration and routing layer
- Business logic must remain outside LangGraph nodes wherever possible
- Tools, skills, memory, artifacts, events, and storage must remain separate services
- Shared state must be explicit and persisted
- PostgreSQL must be the primary durable store

## Acceptance Criteria For Next Milestone

- A live model-backed agent runner can complete at least one full staged workflow
- Session summaries remain bounded as session length grows
- Progress and events are queryable through a thin service interface
- The checked-in SQL migration example can be executed locally end to end and produce Oracle-compatible output artifacts that are inspectable after the run
- The same example has a deterministic local success path without requiring a live model, even if the quality is lower than the live path

Implementation note for the completed delegation milestone:

- Child task sessions should reuse the parent stage definition for context and completion semantics in the first implementation rather than introducing a new task-stage model
- Parent-child lineage should use the existing durable session model before adding dedicated lineage tables

Implementation note for the next orchestration milestone:

- The first stage evaluator should use concrete persisted signals, starting with required artifacts declared in `output_artifacts`, before introducing a richer completion-condition DSL
- Loop accounting should remain in orchestration state so the system can halt deterministically when a stage exceeds `max_loops`

Implementation note after the completed orchestration milestone:

- Stage advancement now depends on an explicit evaluator service rather than the runner's completion flag
- The current evaluator requires artifact matches on both `stage_id` and artifact `kind` for the active stage
- `completion_conditions` remain descriptive until a later milestone introduces a parsed policy format beyond artifact checks

Implementation note for the live-model milestone:

- The runner must remain responsible for tool execution, persistence, and permission enforcement
- Provider adapters may use structured output and tool-calling features, but must return normalized decisions rather than execute tools directly
- The model integration layer should be shaped like a swappable gateway client so model names, endpoints, and runtime parameters can change without changing orchestration code

Implementation note for the first real example milestone:

- The first end-to-end example should be treated as a product requirement, not just a demo prompt
- The example should have explicit input discovery, output location, and validation expectations so success does not depend on generic stage notes
- The stub backend may use deterministic logic for this example so local development can prove file-to-output behavior without external model access
- The live-model path should reuse the same stages, artifacts, and output contract as the deterministic local path

## Open Questions

- Which provider abstraction should be introduced first beyond Azure OpenAI support?
- Should stage definitions remain YAML-first or move into a richer config model?
- How strict should shell command policies be in the first live-model milestone?
- What is the smallest useful HTTP API surface for the next iteration?
- When should `completion_conditions` move from descriptive metadata to a parsed policy format beyond artifact evaluation?
- Should the first example workflow write final outputs only as persisted artifacts, or also materialize files under a checked output directory such as `data/example/migration-clean/output`?
