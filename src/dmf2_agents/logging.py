from __future__ import annotations

import sys
from contextlib import contextmanager
from contextvars import ContextVar, Token
from pathlib import Path
from typing import Any

from loguru import logger


_CONTEXT_VARS: dict[str, ContextVar[str | None]] = {
    "session_id": ContextVar("session_id", default=None),
    "parent_session_id": ContextVar("parent_session_id", default=None),
    "agent_name": ContextVar("agent_name", default=None),
    "stage_id": ContextVar("stage_id", default=None),
}


def _patch_record(record: dict[str, Any]) -> None:
    extra = record.setdefault("extra", {})
    for key, var in _CONTEXT_VARS.items():
        extra.setdefault(key, var.get())


app_logger = logger.patch(_patch_record)


def configure_logging(*, level: str = "INFO", log_file: Path | None = None) -> None:
    logger.remove()
    logger.configure(patcher=_patch_record)
    logger.add(
        sys.stdout,
        level=level.upper(),
        serialize=False,
        colorize=True,
        backtrace=False,
        diagnose=False,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "session={extra[session_id]} parent={extra[parent_session_id]} "
            "agent={extra[agent_name]} stage={extra[stage_id]} | "
            "{message} <dim>{extra}</dim>"
        ),
    )
    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        logger.add(log_file, level=level.upper(), serialize=True, backtrace=False, diagnose=False)


@contextmanager
def log_context(**values: str | None):
    tokens: list[tuple[ContextVar[str | None], Token[str | None]]] = []
    try:
        for key, value in values.items():
            var = _CONTEXT_VARS.get(key)
            if var is None:
                continue
            tokens.append((var, var.set(value)))
        yield
    finally:
        for var, token in reversed(tokens):
            var.reset(token)
