"""Authentication API router.

This module defines API endpoints for user authentication and registration.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from loguru import logger

from ai_notes_api.api.v1.dependencies import get_auth_service
from ai_notes_api.schemas import (
    UserCreateSchema,
    UserResponseSchema,
)
from ai_notes_api.services import AuthService

router = APIRouter(
    prefix="/auth",
    tags=["Auth"],
)


@router.post(
    "/register",
    summary="Register a new user",
    description="Create a new user account and return the created user data.",
    response_model=UserResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def register_user(
    data: UserCreateSchema,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserResponseSchema:
    """Register a new user.

    Args:
        data (UserCreateSchema): Validated user registration data.
        service (AuthService): Authentication service dependency used to
            register the user.

    Returns:
        UserResponseSchema: Created user data.

    Raises:
        UserAlreadyExistsError: If a user with the given email already exists.
    """
    logger.info("User registration requested: email={}", data.email)

    user = await service.register_user(data)

    return UserResponseSchema.model_validate(user)
