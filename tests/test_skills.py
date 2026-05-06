from __future__ import annotations

from pathlib import Path

from dmf2_agents.skills import SkillRegistry


def test_skill_registry_loads_skills(project_root: Path) -> None:
    registry = SkillRegistry(project_root / "skills")
    names = {item.name for item in registry.list()}
    assert {"planning", "artifact-writing", "code-review"}.issubset(names)
