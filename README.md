# dmf2-agents

Controlled, engineering-first multi-agent orchestration built in Python on top of LangGraph.

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

## What This Project Does Not Do

- No LSP integration
- No opaque high-level agent framework beyond LangGraph as the routing engine
- No CrewAI or AutoGen

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
