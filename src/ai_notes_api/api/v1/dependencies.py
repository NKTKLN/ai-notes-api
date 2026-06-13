"""Service dependencies module.

This module defines FastAPI dependencies for constructing application services,
resolving authenticated users, and accessing shared application clients.
"""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from ai_notes_api.core import decode_access_token
from ai_notes_api.db.models import User
from ai_notes_api.db.session import get_db
from ai_notes_api.exceptions import InvalidTokenError
from ai_notes_api.llm import LLMClient
from ai_notes_api.repositories import (
    ChatSessionRepository,
    NoteRepository,
    UserRepository,
)
from ai_notes_api.services import AuthService, ChatSessionService, NoteService

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
)


def get_current_user_id(
    token: Annotated[str, Depends(oauth2_scheme)],
) -> UUID:
    """Return the current authenticated user identifier.

    Args:
        token (str): Bearer access token provided by FastAPI security
            dependency injection.

    Returns:
        UUID: Current authenticated user identifier.

    Raises:
        InvalidTokenError: If the token payload does not contain a valid user
            identifier.
    """
    payload = decode_access_token(token)
    user_id = payload.get("sub")

    if user_id is None:
        raise InvalidTokenError()

    try:
        return UUID(user_id)
    except (ValueError, TypeError) as exc:
        raise InvalidTokenError() from exc


def get_note_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> NoteService:
    """Provide a note service instance.

    Args:
        session (AsyncSession): Asynchronous database session provided by FastAPI
            dependency injection.

    Returns:
        NoteService: Configured note service instance.
    """
    repository = NoteRepository(session)

    return NoteService(repository)


def get_auth_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AuthService:
    """Provide an authentication service instance.

    Args:
        session (AsyncSession): Asynchronous database session provided by FastAPI
            dependency injection.

    Returns:
        AuthService: Configured authentication service instance.
    """
    repository = UserRepository(session)

    return AuthService(repository)


async def get_current_user(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> User:
    """Return the current authenticated user.

    Args:
        user_id (UUID): Current authenticated user identifier.
        service (AuthService): Authentication service dependency used to
            retrieve the user.

    Returns:
        User: Current authenticated user.

    Raises:
        InvalidTokenError: If the token payload is invalid.
        UserNotFoundError: If no user with the authenticated identifier exists.
    """
    return await service.get_user(user_id)


def get_chat_session_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ChatSessionService:
    """Provide a chat session service instance.

    Args:
        session (AsyncSession): Asynchronous database session provided by FastAPI
            dependency injection.

    Returns:
        ChatSessionService: Configured chat session service instance.
    """
    repository = ChatSessionRepository(session)

    return ChatSessionService(repository)


def get_llm_client(request: Request) -> LLMClient:
    """Provide the shared LLM client instance.

    Args:
        request (Request): FastAPI request object containing application state.

    Returns:
        LLMClient: Shared LLM client instance.
    """
    return request.app.state.llm_client
