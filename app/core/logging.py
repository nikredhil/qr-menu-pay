"""Minimal structured-ish logging built on the stdlib.

Keeps the app dependency-light. ``get_logger(__name__).info("event", key=val)``
emits ``event key=val`` lines so logs stay greppable without a logging library.
"""
from __future__ import annotations

import logging


def configure_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


class _KwLogger:
    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger

    def _fmt(self, event: str, kwargs: dict) -> str:
        if not kwargs:
            return event
        extra = " ".join(f"{k}={v}" for k, v in kwargs.items())
        return f"{event} {extra}"

    def info(self, event: str, **kwargs) -> None:
        self._logger.info(self._fmt(event, kwargs))

    def warning(self, event: str, **kwargs) -> None:
        self._logger.warning(self._fmt(event, kwargs))

    def error(self, event: str, **kwargs) -> None:
        self._logger.error(self._fmt(event, kwargs))


def get_logger(name: str) -> _KwLogger:
    return _KwLogger(logging.getLogger(name))
