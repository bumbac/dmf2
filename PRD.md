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
- Tests for the current scaffold

Partially implemented:

- Task delegation exists only as a structured stub result
- Summary generation exists but is simple and not model-backed
- Stage completion exists but does not yet evaluate explicit completion conditions
- Agent execution now has a provider-backed runtime boundary, with deterministic stub execution for tests and an Azure OpenAI adapter for live structured output and tool-calling

Not yet implemented:

- Real model provider integration
- True child task sessions and lineage tables
- HTTP API and event streaming
- Rich permission policies for commands and filesystem paths
- Resume and recovery flows

## Architecture Requirements

- LangGraph must be used as the orchestration and routing layer
- Business logic must remain outside LangGraph nodes wherever possible
- Tools, skills, memory, artifacts, events, and storage must remain separate services
- Shared state must be explicit and persisted
- PostgreSQL must be the primary durable store

## Acceptance Criteria For Next Milestone

- A live model-backed agent runner can complete at least one full staged workflow
- A parent session can spawn a real child task session and consume its result
- Stage advancement depends on explicit evaluator logic rather than a hardcoded runner decision
- Session summaries remain bounded as session length grows
- Progress and events are queryable through a thin service interface

Implementation note for the live-model milestone:

- The runner must remain responsible for tool execution, persistence, and permission enforcement
- Provider adapters may use structured output and tool-calling features, but must return normalized decisions rather than execute tools directly

## Open Questions

- Which provider abstraction should be introduced first beyond Azure OpenAI support?
- Should stage definitions remain YAML-first or move into a richer config model?
- How strict should shell command policies be in the first live-model milestone?
- What is the smallest useful HTTP API surface for the next iteration?
