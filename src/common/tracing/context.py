"""Lightweight run-scoped tracing utilities.

Purpose:
    Associate a unique `run_id` with all work executed during a discovery run.
Inputs:
    Optional explicit run identifier.
Outputs:
    A reusable context manager and helper functions for run context management.
Assumptions:
    A single run identifier is sufficient for Phase 1 tracing needs.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterator
from uuid import uuid4

_CURRENT_RUN_ID: ContextVar[str | None] = ContextVar("current_run_id", default=None)


def create_run_id() -> str:
    """Create a new opaque run identifier."""

    return uuid4().hex


def get_current_run_id() -> str | None:
    """Return the active run identifier, if one is set."""

    return _CURRENT_RUN_ID.get()


def set_current_run_id(run_id: str | None) -> None:
    """Set the active run identifier for the current context."""

    _CURRENT_RUN_ID.set(run_id)


@dataclass(slots=True)
class RunContext:
    """Runtime tracing state for a pipeline execution.

    Purpose:
        Represent a discovery run and make its identifier easy to propagate.
    Inputs:
        A run identifier and optional start time.
    Outputs:
        A compact value object that can be attached to logs or records.
    Assumptions:
        The run identifier is immutable for the life of the context.
    """

    run_id: str
    started_at: datetime


@contextmanager
def trace_run(run_id: str | None = None) -> Iterator[RunContext]:
    """Activate a run-scoped tracing context."""

    active_run_id = run_id or create_run_id()
    token = _CURRENT_RUN_ID.set(active_run_id)
    context = RunContext(run_id=active_run_id, started_at=datetime.now(timezone.utc))
    try:
        yield context
    finally:
        _CURRENT_RUN_ID.reset(token)

