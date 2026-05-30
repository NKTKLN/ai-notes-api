"""Tests for application configuration settings."""

from collections.abc import Generator
from typing import Any

import pytest

from ai_notes_api.core.config import Settings


@pytest.fixture
def postgres_env(monkeypatch: Any) -> Generator[None]:
    """Set PostgreSQL environment variables for tests.

    Args:
        monkeypatch: Pytest fixture used to modify environment variables.

    Yields:
        None: Control back to the test after setting environment variables.
    """
    monkeypatch.setenv("POSTGRES_HOST", "localhost")
    monkeypatch.setenv("POSTGRES_PORT", "5432")
    monkeypatch.setenv("POSTGRES_USER", "postgres")
    monkeypatch.setenv("POSTGRES_PASSWORD", "postgres")
    monkeypatch.setenv("POSTGRES_DB", "postgres")

    yield


@pytest.mark.usefixtures("postgres_env")
def test_default_config() -> None:
    """Test default application configuration values."""
    settings = Settings()  # type: ignore[call-arg]

    assert settings.disable_logging is False
    assert settings.log_level == "INFO"
    assert settings.log_path == ""


@pytest.mark.usefixtures("postgres_env")
def test_config_from_env(monkeypatch: Any) -> None:
    """Test that application configuration can be loaded from environment variables."""
    monkeypatch.setenv("DISABLE_LOGGING", "true")

    settings = Settings()  # type: ignore[call-arg]

    assert settings.disable_logging is True


@pytest.mark.usefixtures("postgres_env")
def test_pg_link_generation() -> None:
    """Test PostgreSQL database URL generation."""
    settings = Settings()  # type: ignore[call-arg]

    assert settings.database_url == (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"
    )
