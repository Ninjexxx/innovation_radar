"""Basic standard-library logging configuration."""

from __future__ import annotations

import logging
import time


LOGGER_NAME = "innovation_radar"
HANDLER_NAME = "innovation_radar.stderr"
LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def configure_logging(level: str) -> logging.Logger:
    """Configure one idempotent stderr handler for the package logger."""

    normalized_level = level.strip().upper()
    level_number = logging.getLevelNamesMapping().get(normalized_level)
    if not isinstance(level_number, int):
        raise ValueError(f"invalid log level: {level!r}")

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level_number)
    logger.propagate = False

    handler = next(
        (candidate for candidate in logger.handlers if candidate.name == HANDLER_NAME),
        None,
    )
    if handler is None:
        handler = logging.StreamHandler()
        handler.set_name(HANDLER_NAME)
        logger.addHandler(handler)

    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
    formatter.converter = time.gmtime
    handler.setFormatter(formatter)
    handler.setLevel(level_number)

    return logger
