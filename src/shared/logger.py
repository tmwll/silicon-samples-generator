from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from colorlog import ColoredFormatter


def setup_logging(
    app_name="Silicon-Samples-Generator", level=logging.INFO, console=True, logfile=True
) -> logging.Logger:

    filepath = f"logs/{app_name}.log"
    backup_count: int = (5,)

    logger = logging.getLogger(app_name)

    # idempotent: keine doppelten Handler, wenn setup_logging() aus Versehen mehrfach läuft
    if getattr(logger, "_configured", False):
        return logger

    logger.setLevel(level)
    logger.propagate = False

    if console:
        ch = logging.StreamHandler()
        ch.setLevel(level)
        ch.setFormatter(
            ColoredFormatter(
                "%(log_color)s%(levelname)-8s%(reset)s | %(asctime)s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
                log_colors={
                    "DEBUG": "cyan",
                    "INFO": "green",
                    "WARNING": "yellow",
                    "ERROR": "red",
                    "CRITICAL": "bold_red",
                },
                reset=True,
            )
        )
        logger.addHandler(ch)

    if logfile:
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        fh = RotatingFileHandler(
            path,
            backupCount=backup_count,
            encoding="utf-8",
        )
        fh.setLevel(level)
        fh.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(name)s | %(filename)s:%(lineno)d | %(message)s"
            )
        )
        logger.addHandler(fh)

    logger._configured = True
    return logger


def get_logger(
    name: str | None = None, app_name="Silicon-Samples-Generator"
) -> logging.Logger:
    return logging.getLogger(app_name if not name else f"{app_name}.{name}")
