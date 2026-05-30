"""API v1 router.

This module configures the main API v1 router and includes all endpoint
routers that belong to the first version of the API.
"""

from fastapi import APIRouter

from .healthcheck import router as healthcheck_router

router = APIRouter(
    prefix="/api/v1",
)

router.include_router(healthcheck_router)
