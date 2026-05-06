from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field


class Settings(BaseModel):
    project_root: Path = Field(default_factory=lambda: Path.cwd())
    database_url: str = Field(default="")
    model_backend: str = Field(default="stub")
    model_name: str = Field(default="stub-model")
    model_endpoint: str | None = Field(default=None)
    model_api_key: str | None = Field(default=None)
    model_api_version: str | None = Field(default=None)
    model_temperature: float = Field(default=0.1)
    model_max_tokens: int | None = Field(default=None)
    azure_openai_endpoint: str | None = Field(default=None)
    azure_openai_api_key: str | None = Field(default=None)
    azure_openai_api_version: str = Field(default="2024-08-01-preview")
    azure_openai_deployment: str | None = Field(default=None)
    skills_dir: Path = Field(default_factory=lambda: Path.cwd() / "skills")
    default_stage_file: Path = Field(default_factory=lambda: Path.cwd() / "examples" / "pipeline.yaml")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    root = Path.cwd()
    database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        host = os.getenv("POSTGRES_HOST", "localhost")
        port = os.getenv("POSTGRES_PORT", "5432")
        user = os.getenv("POSTGRES_USER", "postgres")
        password = os.getenv("POSTGRES_PASSWORD", "")
        database = os.getenv("AGENTS_POSTGRES_DB", "dmf2_agents")
        auth = user if not password else f"{user}:{password}"
        database_url = f"postgresql+psycopg://{auth}@{host}:{port}/{database}"
    backend = "stub"
    if os.getenv("AZURE_OPENAI_API_KEY") and os.getenv("AZURE_OPENAI_ENDPOINT"):
        backend = "azure_openai"
    return Settings(
        project_root=root,
        database_url=database_url,
        model_backend=backend,
        model_name=os.getenv("AZURE_OPENAI_DEPLOYMENT", "stub-model"),
        model_endpoint=os.getenv("MODEL_ENDPOINT") or os.getenv("AZURE_OPENAI_ENDPOINT"),
        model_api_key=os.getenv("MODEL_API_KEY") or os.getenv("AZURE_OPENAI_API_KEY"),
        model_api_version=os.getenv("MODEL_API_VERSION") or os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview"),
        model_temperature=float(os.getenv("MODEL_TEMPERATURE", "0.1")),
        model_max_tokens=int(os.getenv("MODEL_MAX_TOKENS")) if os.getenv("MODEL_MAX_TOKENS") else None,
        azure_openai_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        azure_openai_api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        azure_openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview"),
        azure_openai_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
        skills_dir=root / "skills",
        default_stage_file=root / "examples" / "pipeline.yaml",
    )


def build_provider_settings(settings: Settings) -> dict[str, str]:
    return {
        "provider": settings.model_backend,
        "model": settings.azure_openai_deployment or settings.model_name,
        "endpoint": settings.model_endpoint or settings.azure_openai_endpoint or "",
        "api_key": settings.model_api_key or settings.azure_openai_api_key or "",
        "api_version": settings.model_api_version or settings.azure_openai_api_version,
        "temperature": settings.model_temperature,
        "max_tokens": settings.model_max_tokens,
    }
