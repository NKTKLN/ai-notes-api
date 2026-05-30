"""Application logging configuration module.

This module provides the setup_logger function for configuring log output
to the console and, optionally, to a file.
"""

import sys

from loguru import logger

from .config import settings


def setup_logger() -> None:
    """Initialize the application logging configuration.

    Configures the Loguru logger using application settings, including the log
    level, output format, and optional log file path. If logging is disabled in
    the configuration, no handlers are added.
    """
    logger.remove()

    if settings.disable_logging:
        return

    logger.add(
        sys.stdout,
        format=settings.log_format,
        level=settings.log_level,
        colorize=True,
        enqueue=True,
        backtrace=True,
        diagnose=True,
    )

    if settings.log_path:
        logger.debug(f"Adding file logger: {settings.log_path}")
        logger.add(
            settings.log_path,
            format=settings.log_format,
            level=settings.log_level,
            colorize=False,
            enqueue=True,
            backtrace=True,
            diagnose=True,
            rotation="10 MB",
            retention="10 days",
            compression="zip",
        )
    else:
        logger.debug("Log file path is not specified; file logging is disabled")

    logger.info("Logging has been initialized")
    logger.info(f"Logging level is set to: {settings.log_level}")
    if settings.log_path:
        logger.info(f"Logs will be written to file: {settings.log_path}")
    else:
        logger.info("Log file is not specified; output is console-only")
