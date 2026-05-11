from __future__ import annotations

from dmf2_agents.agents import AgentRegistry


def test_agent_registry_has_scoped_tools() -> None:
    registry = AgentRegistry()
    planner = registry.get("planner")
    reviewer = registry.get("reviewer")
    assert planner is not None
    assert reviewer is not None
    assert "write_artifact" in planner.allowed_tools
    assert "read_file" in planner.allowed_tools
    assert "run_command" in planner.allowed_tools
    assert "write_file" not in planner.allowed_tools
    assert all(not agent.stage_roles if hasattr(agent, "stage_roles") else True for agent in registry.list())
    assert "read_file" in reviewer.allowed_tools
    assert "run_command" in reviewer.allowed_tools
    assert "write_file" not in reviewer.allowed_tools
    assert "mark_stage_complete" not in planner.allowed_tools
    assert "mark_stage_complete" not in reviewer.allowed_tools
