from __future__ import annotations

from pathlib import Path

from dmf2_agents.bootstrap import build_app


def test_session_orchestrator_runs_all_stages(project_root: Path) -> None:
    app = build_app(project_root=project_root)
    session_id = app.run("Produce a staged implementation outline")
    assert session_id
    messages = app.repository.list_messages(session_id)
    assert any(item.role == "assistant" for item in messages)
    events = app.repository.list_events(session_id)
    event_types = [item.event_type for item in events]
    assert "session.started" in event_types
    assert "stage.completed" in event_types
    assert "session.finished" in event_types
