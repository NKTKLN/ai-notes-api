"""API v1 router.

This module configures the main API v1 router and includes all endpoint
routers that belong to the first version of the API.
"""

from fastapi import APIRouter

from ai_notes_api.api.v1 import (
    auth,
    chat_sessions,
    completions,
    documents,
    generation_job,
    healthcheck,
    messages,
    notes,
)

router = APIRouter(
    prefix="/api/v1",
)

router.include_router(healthcheck.router)
router.include_router(auth.router)
router.include_router(notes.router)
router.include_router(chat_sessions.router)
router.include_router(messages.router)
router.include_router(documents.router)
router.include_router(completions.router)
router.include_router(generation_job.router)
