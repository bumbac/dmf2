from __future__ import annotations

import os
from pathlib import Path

import pytest

from dmf2_agents.config import get_settings


@pytest.fixture(autouse=True)
def reset_settings_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENTS_POSTGRES_DB", os.getenv("AGENTS_POSTGRES_DB", "dmf2_agents"))
    get_settings.cache_clear()


@pytest.fixture
def project_root() -> Path:
    return Path.cwd()
