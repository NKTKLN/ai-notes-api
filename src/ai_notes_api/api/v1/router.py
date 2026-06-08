"""API v1 router.

This module configures the main API v1 router and includes all endpoint
routers that belong to the first version of the API.
"""

from fastapi import APIRouter

from ai_notes_api.api.v1 import auth, healthcheck, notes

router = APIRouter(
    prefix="/api/v1",
)

router.include_router(healthcheck.router)
router.include_router(auth.router)
router.include_router(notes.router)
