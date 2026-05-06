from __future__ import annotations

from dmf2_agents.agents import AgentRegistry


def test_agent_registry_has_scoped_tools() -> None:
    registry = AgentRegistry()
    planner = registry.get("planner")
    assert planner is not None
    assert "write_artifact" in planner.allowed_tools
    assert "run_command" not in planner.allowed_tools
