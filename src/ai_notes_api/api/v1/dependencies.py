"""Service dependencies module.

This module defines FastAPI dependencies for constructing application services.
"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ai_notes_api.db.session import get_db
from ai_notes_api.repositories import NoteRepository, UserRepository
from ai_notes_api.services import AuthService, NoteService


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
