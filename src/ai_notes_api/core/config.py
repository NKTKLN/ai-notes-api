"""Application configuration module.

This module defines application settings loaded from environment variables
and the `.env` file.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings.

    Attributes:
        disable_logging (bool): Whether application logging is disabled.
        log_level (str): Logging level used by the application.
        log_path (str): Optional path to the log file. If empty, logs are
            written only to the console.
        postgres_host (str): PostgreSQL server host.
        postgres_port (int): PostgreSQL server port.
        postgres_user (str): PostgreSQL username.
        postgres_password (str): PostgreSQL password.
        postgres_db (str): PostgreSQL database name.
        jwt_secret_key (str): Secret key used to sign and verify JWT tokens.
        jwt_algorithm (str): Algorithm used to sign and verify JWT tokens.
        access_token_expire_minutes (int): Access token lifetime in minutes.
        open_ai_api_key (str): OpenAI API key.
        open_ai_model (str): OpenAI chat/completion model name.
        open_ai_embedding_model (str): OpenAI embedding model name.
        open_ai_api_url (str | None): Optional custom OpenAI-compatible API URL.
        open_ai_max_output_tokens (int): Maximum number of output tokens.
        llm_context_messages_limit (int): Maximum number of context messages
            sent to the LLM.
        celery_broker_url (str): Celery broker URL.
        celery_result_backend (str): Celery result backend URL.
        log_format (str): Format string used by Loguru for log messages.
        database_url (str): Async PostgreSQL database connection URL.
        model_config (SettingsConfigDict): Pydantic settings configuration.
    """

    disable_logging: bool = Field(default=False)
    log_level: str = Field(default="INFO")
    log_path: str = Field(default="")

    postgres_host: str = Field(...)
    postgres_port: int = Field(...)
    postgres_user: str = Field(...)
    postgres_password: str = Field(...)
    postgres_db: str = Field(...)

    jwt_secret_key: str = Field(...)
    jwt_algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=30)

    open_ai_api_key: str = Field(...)
    open_ai_model: str = Field(...)
    open_ai_embedding_model: str = Field(default="text-embedding-3-small")
    open_ai_api_url: str | None = Field(default=None)
    open_ai_max_output_tokens: int = Field(default=700)

    llm_context_messages_limit: int = Field(default=20)

    celery_broker_url: str = Field(...)
    celery_result_backend: str = Field(...)

    log_format: str = (
        "<cyan>[{time:DD/MM/YY HH:mm:ss}]</cyan> "
        "<light-magenta>[{file}:{function}:{line}]</light-magenta> "
        "<lvl>[{level}]</lvl> - {message}"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

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


settings: Settings = Settings()  # type: ignore[call-arg]
