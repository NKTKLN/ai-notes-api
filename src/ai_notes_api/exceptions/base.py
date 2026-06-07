"""Application exception handlers module.

This module defines the base application exception and registers custom
exception handlers for the FastAPI application.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AppException(Exception):
    """Base exception for application-specific errors.

    Attributes:
        status_code (int): HTTP status code returned for the exception.
        detail (str): Human-readable error message.
    """

    status_code: int = 500

    def __init__(self, detail: str) -> None:
        """Initialize the application exception.

        Args:
            detail (str): Human-readable error message.
        """
        self.detail = detail


async def app_exception_handler(
    _request: Request,
    exc: Exception,
) -> JSONResponse:
    """Handle application-specific exceptions.

    Args:
        _request (Request): Incoming FastAPI request.
        exc (Exception): Exception instance raised during request handling.

    Returns:
        JSONResponse: JSON response containing the exception details.

    Raises:
        TypeError: If the exception is not an application exception.
    """
    if not isinstance(exc, AppException):
        raise TypeError

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register custom exception handlers for the FastAPI application.

    Args:
        app (FastAPI): FastAPI application instance.
    """
    app.add_exception_handler(
        AppException,
        app_exception_handler,
    )
