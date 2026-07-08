"""Structured logging helpers.

Purpose:
    Provide reusable logging primitives that include timestamps, component
    names, and the current `run_id` without requiring direct logging setup in
    feature code.
Inputs:
    Logging settings and component names.
Outputs:
    A lightweight structured logger wrapper and configured handlers.
Assumptions:
    Logs should remain dependency-free and JSON-serializable in Phase 1.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import logging as py_logging
from datetime import datetime, timezone
from typing import Any

from common.config.settings import LoggingSettings, load_config
from common.tracing.context import get_current_run_id

_CONFIGURED = False


class StructuredFormatter(py_logging.Formatter):
    """Format log records as structured JSON objects."""

    def format(self, record: py_logging.LogRecord) -> str:  # noqa: D401
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "component": getattr(record, "component", record.name),
            "run_id": getattr(record, "run_id", None),
            "message": record.getMessage(),
        }
        extra_fields = getattr(record, "structured_fields", None)
        if isinstance(extra_fields, dict):
            payload.update(extra_fields)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


class RunContextFilter(py_logging.Filter):
    """Inject the current run identifier into every log record."""

    def filter(self, record: py_logging.LogRecord) -> bool:
        record.run_id = get_current_run_id()
        return True


@dataclass(slots=True)
class StructuredLogger:
    """Thin wrapper over `logging.Logger` with structured field support.

    Purpose:
        Offer a consistent logging API to application code without exposing the
        details of the underlying logging subsystem.
    Inputs:
        Component name and optional logger instance.
    Outputs:
        Convenience methods for emitting structured log events.
    Assumptions:
        Structured fields are JSON-serializable or string-coercible.
    """

    component_name: str
    _logger: py_logging.Logger

    def debug(self, message: str, **fields: Any) -> None:
        self._log(py_logging.DEBUG, message, fields)

    def info(self, message: str, **fields: Any) -> None:
        self._log(py_logging.INFO, message, fields)

    def warning(self, message: str, **fields: Any) -> None:
        self._log(py_logging.WARNING, message, fields)

    def error(self, message: str, **fields: Any) -> None:
        self._log(py_logging.ERROR, message, fields)

    def exception(self, message: str, **fields: Any) -> None:
        self._log(py_logging.ERROR, message, fields, exc_info=True)

    def _log(self, level: int, message: str, fields: dict[str, Any], exc_info: bool = False) -> None:
        self._logger.log(
            level,
            message,
            extra={
                "component": self.component_name,
                "structured_fields": fields,
            },
            exc_info=exc_info,
        )


def configure_logging(settings: LoggingSettings | None = None, force: bool = False) -> None:
    """Configure console and file logging once per process."""

    global _CONFIGURED
    if _CONFIGURED and not force:
        return

    config = settings or load_config().logging
    level = getattr(py_logging, config.level.upper(), py_logging.INFO)

    root_logger = py_logging.getLogger()
    if force:
        root_logger.handlers.clear()
    elif root_logger.handlers:
        _CONFIGURED = True
        return

    root_logger.setLevel(level)

    formatter = StructuredFormatter()
    filter_ = RunContextFilter()

    console_handler = py_logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(filter_)
    root_logger.addHandler(console_handler)

    if config.file_path:
        config.log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = py_logging.FileHandler(config.file_path, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        file_handler.addFilter(filter_)
        root_logger.addHandler(file_handler)

    root_logger.addFilter(filter_)
    _CONFIGURED = True


def get_logger(component_name: str, settings: LoggingSettings | None = None) -> StructuredLogger:
    """Return a structured logger for the named component."""

    configure_logging(settings)
    logger = py_logging.getLogger(f"nidarsha.{component_name}")
    return StructuredLogger(component_name=component_name, _logger=logger)
