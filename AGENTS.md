# AGENTS.md

## Project Context

Multi-agent orchestration system built in Python on top of LangGraph run in stages centered around tools, skills and loops. The tool results, chat history, and artifacts (plan, todo list, progress) needs to be shared across agents and stages.

## Code Style Preferences

- Use `uv`, Python 3.12, poetry, ruff, and black.
- Add tests for implementation changes.
- Use Postgres for the database.
- Read `PRD.md`, `IMPLEMENTATION_PLAN.md`, and `README.md` before making substantial changes.
- Update `PRD.md`, `IMPLEMENTATION_PLAN.md`, and `README.md` after implementation when behavior, config, or architecture changes.

## Commands

- `uv sync`
- `uv run pytest`
- `uv run dmf2-agents ...`
