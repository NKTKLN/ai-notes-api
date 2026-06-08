"""Authentication API router.

This module defines API endpoints for user authentication and registration.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from loguru import logger

from ai_notes_api.api.v1.dependencies import get_auth_service, get_current_user_id
from ai_notes_api.schemas import (
    TokenResponseSchema,
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


@router.post(
    "/login",
    summary="Log in user",
    description="Authenticate a user and return an access token.",
    response_model=TokenResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def login_user(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponseSchema:
    """Log in a user.

    Args:
        form_data (OAuth2PasswordRequestForm): OAuth2 password form containing
            the username and password.
        service (AuthService): Authentication service dependency used to
            authenticate the user.

    Returns:
        TokenResponseSchema: Access token data.

    Raises:
        InvalidCredentialsError: If the username or password is invalid.
        InactiveUserError: If the user account is inactive.
    """
    logger.info("User login requested")

    user = await service.authenticate_user(form_data.username, form_data.password)
    access_token = service.create_token_for_user(user)

    return TokenResponseSchema(
        access_token=access_token,
        token_type="bearer",  # noqa: S106
    )


@router.get(
    "/me",
    summary="Get current user",
    description="Return the currently authenticated user.",
    response_model=UserResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def get_current_user(
    user_id: Annotated[int, Depends(get_current_user_id)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserResponseSchema:
    """Return the currently authenticated user.

    Args:
        user_id (int): Current authenticated user identifier.
        service (AuthService): Authentication service dependency used to
            retrieve the user.

    Returns:
        UserResponseSchema: Current authenticated user data.

    Raises:
        InvalidTokenError: If the access token is invalid.
        UserNotFoundError: If no user with the authenticated identifier exists.
    """
    logger.info("Current user retrieval requested: user_id={}", user_id)

    user = await service.get_user(user_id)

    return UserResponseSchema.model_validate(user)
