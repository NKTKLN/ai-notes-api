"""Application exception handlers module.

This module defines the base application exception and registers custom
exception handlers for the FastAPI application.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AppException(Exception):
    """Base exception for application-specific errors.

    Attributes:
        status_code: HTTP status code returned for the exception.
        detail: Human-readable error message.
    """

    status_code: int = 500

    def __init__(self, detail: str) -> None:
        """Initialize the application exception.

        Args:
            detail: Human-readable error message.
        """
        self.detail = detail


async def app_exception_handler(
    _request: Request,
    exc: AppException,
) -> JSONResponse:
    """Handle application-specific exceptions.

    Args:
        _request: Incoming FastAPI request.
        exc: Application exception instance.

    Returns:
        JSONResponse: JSON response containing the exception details.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register custom exception handlers for the FastAPI application.

    Args:
        app: FastAPI application instance.

    Returns:
        None.
    """
    app.add_exception_handler(
        AppException,
        app_exception_handler,
    )
