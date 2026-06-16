"""Worker runtime module.

This module defines shared runtime dependencies used by Celery workers.
"""

from dataclasses import dataclass

from loguru import logger

from ai_notes_api.llm.client import LLMClient


class WorkerRuntimeNotInitializedError(RuntimeError):
    """Exception raised when worker runtime dependencies are not initialized."""

    def __init__(self) -> None:
        """Initialize the worker runtime not initialized exception."""
        super().__init__("Worker runtime dependencies are not initialized")


@dataclass
class WorkerRuntime:
    """Runtime dependencies shared by worker processes.

    Attributes:
        llm_client (LLMClient | None): Shared LLM client instance.
    """

    llm_client: LLMClient | None = None

    def init(self) -> None:
        """Initialize worker runtime dependencies."""
        if self.llm_client is not None:
            logger.debug("Worker runtime dependencies already initialized")

            return

        self.llm_client = LLMClient()

        logger.info("Worker runtime dependencies initialized")

    def get_llm_client(self) -> LLMClient:
        """Return the initialized LLM client.

        Returns:
            LLMClient: Initialized LLM client.

        Raises:
            WorkerRuntimeNotInitializedError: If worker runtime dependencies
                have not been initialized.
        """
        if self.llm_client is None:
            logger.error("LLM client requested before worker runtime initialization")

            raise WorkerRuntimeNotInitializedError()

        return self.llm_client


runtime = WorkerRuntime()
