"""Application entry point.

This module creates the FastAPI application instance, configures application
startup behavior, and registers API routers.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from ai_notes_api.api.v1 import router
from ai_notes_api.core import setup_logger


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Manage the application lifespan.

    Initializes application-wide resources before the application starts
    handling requests.

    Args:
        _app: FastAPI application instance.

    Yields:
        None: Control back to FastAPI while the application is running.
    """
    setup_logger()

    yield


app: FastAPI = FastAPI(
    title="AI Note's API",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(router)
