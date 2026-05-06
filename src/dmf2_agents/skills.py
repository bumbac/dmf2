from __future__ import annotations

from pathlib import Path

from .domain import SkillDefinition


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text
    _, rest = text.split("---\n", 1)
    head, body = rest.split("---\n", 1)
    metadata: dict[str, str] = {}
    for line in head.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip()
    return metadata, body.strip()


class SkillRegistry:
    def __init__(self, root: Path):
        self.root = root
        self._skills = self._load()

    def _load(self) -> dict[str, SkillDefinition]:
        result: dict[str, SkillDefinition] = {}
        for path in sorted(self.root.glob("**/SKILL.md")):
            metadata, body = _parse_frontmatter(path.read_text())
            name = metadata.get("name", path.parent.name)
            result[name] = SkillDefinition(
                name=name,
                description=metadata.get("description", ""),
                content=body,
                path=str(path),
            )
        return result

    def list(self) -> list[SkillDefinition]:
        return list(self._skills.values())

    def get(self, name: str) -> SkillDefinition | None:
        return self._skills.get(name)
