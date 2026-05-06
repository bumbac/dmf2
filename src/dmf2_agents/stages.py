from __future__ import annotations

from pathlib import Path

import yaml

from .domain import StageDefinition


class StageRegistry:
    def __init__(self, stage_file: Path):
        payload = yaml.safe_load(stage_file.read_text())
        self._stages = [StageDefinition.model_validate(item) for item in payload["stages"]]

    def list(self) -> list[StageDefinition]:
        return list(self._stages)

    def get(self, stage_id: str) -> StageDefinition | None:
        for stage in self._stages:
            if stage.id == stage_id:
                return stage
        return None
