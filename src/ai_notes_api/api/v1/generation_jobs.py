"""Generation jobs API router.

This module defines API endpoints for creating and retrieving LLM generation
jobs.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from loguru import logger

from ai_notes_api.api.v1.dependencies import get_current_user, get_job_service
from ai_notes_api.db.models import User
from ai_notes_api.schemas import (
    ErrorResponseSchema,
    GenerationJobCreateSchema,
    GenerationJobResponseSchema,
)
from ai_notes_api.services import JobService
from ai_notes_api.workers.tasks.generation import run_generation_job

router = APIRouter(
    prefix="/chat/completions/jobs",
    tags=["Jobs"],
)


@router.post(
    "",
    summary="Create generation job",
    description="Create a generation job and enqueue it for background execution.",
    response_model=GenerationJobResponseSchema,
    status_code=status.HTTP_201_CREATED,
    responses={
        409: {
            "model": ErrorResponseSchema,
            "description": "Generation already in progress",
        },
    },
)
async def create_completion_job(
    data: GenerationJobCreateSchema,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[JobService, Depends(get_job_service)],
) -> GenerationJobResponseSchema:
    """Create a generation job.

    Args:
        data (GenerationJobCreateSchema): Validated generation job creation
            data.
        user (User): Current authenticated user.
        service (JobService): Generation job service dependency used to create
            the generation job.

    Returns:
        GenerationJobResponseSchema: Created generation job data.

    Raises:
        ChatSessionNotFoundError: If no accessible chat session exists.
        GenerationInProgressError: If generation is already in progress.
    """
    logger.info("Generation job creation requested")

    job = await service.create_job(user.id, data)

    run_generation_job.delay(str(job.id))

    return GenerationJobResponseSchema.model_validate(job)


@router.get(
    "/{job_id}",
    summary="Get generation job by ID",
    description="Return a generation job by its unique identifier.",
    response_model=GenerationJobResponseSchema,
    status_code=status.HTTP_200_OK,
    responses={
        404: {
            "model": ErrorResponseSchema,
            "description": "Generation job not found",
        },
    },
)
async def get_completion_job(
    job_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[JobService, Depends(get_job_service)],
) -> GenerationJobResponseSchema:
    """Return a generation job by its identifier.

    Args:
        job_id (UUID): Unique generation job identifier.
        user (User): Current authenticated user.
        service (JobService): Generation job service dependency used to
            retrieve the generation job.

    Returns:
        GenerationJobResponseSchema: Generation job data.

    Raises:
        GenerationNotFoundError: If no generation job with the given identifier
            exists.
    """
    logger.info("Generation job retrieval requested: job_id={}", job_id)

    job = await service.get_by_id(user.id, job_id)

    return GenerationJobResponseSchema.model_validate(job)
