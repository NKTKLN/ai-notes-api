"""Tests for application logging configuration."""

from types import SimpleNamespace
from typing import Any, cast

from loguru import logger

from ai_notes_api.core import logger as logging_module


def make_settings(
    disable_logging: bool = False,
    log_path: str | None = None,
) -> SimpleNamespace:
    """Create test settings for logger configuration.

    Args:
        disable_logging: Whether logging should be disabled.
        log_path: Optional path to the log file.

    Returns:
        SimpleNamespace: Settings object used to configure the logger in tests.
    """
    return SimpleNamespace(
        disable_logging=disable_logging,
        log_format="{time} | {level} | {message}",
        log_level="DEBUG",
        log_path=log_path,
    )


def handlers_count() -> int:
    """Return the number of registered Loguru handlers.

    Returns:
        int: Number of currently registered Loguru handlers.
    """
    logger_with_core = cast(Any, logger)
    return len(logger_with_core._core.handlers)


def test_setup_logger_disabled(monkeypatch: Any) -> None:
    """Test that logger setup adds no handlers when logging is disabled."""
    monkeypatch.setattr(
        logging_module,
        "settings",
        make_settings(disable_logging=True),
    )

    logging_module.setup_logger()

    assert handlers_count() == 0


def test_setup_logger_adds_console_handler(monkeypatch: Any) -> None:
    """Test that logger setup adds a console handler."""
    monkeypatch.setattr(
        logging_module,
        "settings",
        make_settings(disable_logging=False),
    )

    logging_module.setup_logger()

    assert handlers_count() == 1


def test_setup_logger_adds_file_handler(monkeypatch: Any, tmp_path: Any) -> None:
    """Test that logger setup adds console and file handlers."""
    log_file = tmp_path / "app.log"

    monkeypatch.setattr(
        logging_module,
        "settings",
        make_settings(
            disable_logging=False,
            log_path=str(log_file),
        ),
    )

    logging_module.setup_logger()

    assert handlers_count() == 2


def test_setup_logger_does_not_duplicate_handlers(monkeypatch: Any) -> None:
    """Test that repeated logger setup does not duplicate handlers."""
    monkeypatch.setattr(
        logging_module,
        "settings",
        make_settings(disable_logging=False),
    )

    logging_module.setup_logger()
    logging_module.setup_logger()

    assert handlers_count() == 1
