"""Application configuration module.

This module defines application settings loaded from environment variables
and the `.env` file.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings.

    Attributes:
        disable_logging: Whether application logging is disabled.
        log_level: Logging level used by the application.
        log_path: Optional path to the log file. If empty, logs are written
            only to the console.
        log_format: Format string used by Loguru for log messages.
        model_config: Pydantic settings configuration.
    """

    disable_logging: bool = Field(default=False)
    log_level: str = Field(default="INFO")
    log_path: str = Field(default="")

    log_format: str = (
        "<cyan>[{time:DD/MM/YY HH:mm:ss}]</cyan> "
        "<light-magenta>[{file}:{function}:{line}]</light-magenta> "
        "<lvl>[{level}]</lvl> - {message}"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = Settings()
