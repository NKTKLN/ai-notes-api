"""Healthcheck API router.

This module defines the healthcheck endpoint used to verify that the API
is running and able to respond to requests.
"""

from fastapi import APIRouter

from loguru import logger

from ai_notes_api.schemas import HealthcheckResponseSchema

router = APIRouter(
    prefix="/health",
    tags=["Healthcheck"],
)


@router.get("", response_model=HealthcheckResponseSchema)
def healthcheck() -> HealthcheckResponseSchema:
    """Return the current API health status.

    Returns:
        HealthcheckResponseSchema: Healthcheck response containing the current
        service status.
    """
    logger.info("Healthcheck requested")
    return HealthcheckResponseSchema(status="ok")
