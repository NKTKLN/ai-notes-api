"""Celery application module.

This module configures the Celery application used by background workers.
"""

from celery import Celery
from celery.signals import worker_process_init
from loguru import logger

from ai_notes_api.core import settings, setup_logger

celery_app = Celery(
    "ai_notes_api_worker",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["ai_notes_api.workers.tasks.generation"],
)


@worker_process_init.connect
def init_worker_process(**_kwargs: object) -> None:
    """Initialize runtime dependencies for a Celery worker process.

    Args:
        **kwargs (object): Celery signal keyword arguments.
    """
    setup_logger()

    logger.info("Celery worker process initialized")
