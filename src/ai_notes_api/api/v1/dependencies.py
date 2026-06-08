"""Service dependencies module.

This module defines FastAPI dependencies for constructing application services
and resolving authenticated users.
"""

from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from ai_notes_api.core import decode_access_token
from ai_notes_api.db.session import get_db
from ai_notes_api.exceptions import InvalidTokenError
from ai_notes_api.repositories import NoteRepository, UserRepository
from ai_notes_api.services import AuthService, NoteService

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
)


def get_current_user_id(
    token: Annotated[str, Depends(oauth2_scheme)],
) -> int:
    """Return the current authenticated user identifier.

    Args:
        token (str): Bearer access token provided by FastAPI security
            dependency injection.

    Returns:
        int: Current authenticated user identifier.

    Raises:
        InvalidTokenError: If the token payload does not contain a valid user
            identifier.
    """
    payload = decode_access_token(token)
    user_id = payload.get("sub")

    if user_id is None:
        raise InvalidTokenError()

    try:
        return int(user_id)
    except ValueError as exc:
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
