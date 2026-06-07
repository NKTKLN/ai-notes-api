"""Application entry point.

This module creates the FastAPI application instance, configures application
startup behavior, and registers API routers.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from ai_notes_api.api.v1 import router
from ai_notes_api.core import setup_logger
from ai_notes_api.exceptions import register_exception_handlers


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
    lifespan=lifespan,
)


@app.get(
    "/",
    include_in_schema=False,
)
def root() -> RedirectResponse:
    """Redirect the root endpoint to the API documentation.

    Returns:
        RedirectResponse: Redirect response pointing to the Swagger UI
        documentation page.
    """
    return RedirectResponse(
        url="/docs",
        status_code=302,
    )


register_exception_handlers(app)

app.include_router(router)
