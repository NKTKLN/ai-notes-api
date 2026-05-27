"""Application configuration module.

This module defines application settings loaded from environment variables
and the `.env` file.
"""

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings.

    Attributes:
        disable_logging: Whether application logging is disabled.
        log_level: Logging level used by the application.
        log_path: Optional path to the log file. If empty, logs are written
            only to the console.
        postgres_host: PostgreSQL server host.
        postgres_port: PostgreSQL server port.
        postgres_user: PostgreSQL username.
        postgres_password: PostgreSQL password.
        postgres_db: PostgreSQL database name.
        log_format: Format string used by Loguru for log messages.
        database_url: Async PostgreSQL database connection URL.
        model_config: Pydantic settings configuration.
    """

    disable_logging: bool = Field(default=False)
    log_level: str = Field(default="INFO")
    log_path: str = Field(default="")

    postgres_host: str
    postgres_port: int
    postgres_user: str
    postgres_password: str
    postgres_db: str

    log_format: str = (
        "<cyan>[{time:DD/MM/YY HH:mm:ss}]</cyan> "
        "<light-magenta>[{file}:{function}:{line}]</light-magenta> "
        "<lvl>[{level}]</lvl> - {message}"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    @computed_field
    @property
    def database_url(self) -> str:
        """Build the asynchronous PostgreSQL database URL.

        Returns:
            str: PostgreSQL connection URL using the asyncpg driver.
        """
        return (
            "postgresql+asyncpg://"
            f"{self.postgres_user}:"
            f"{self.postgres_password}@"
            f"{self.postgres_host}:"
            f"{self.postgres_port}/"
            f"{self.postgres_db}"
        )


settings = Settings()
