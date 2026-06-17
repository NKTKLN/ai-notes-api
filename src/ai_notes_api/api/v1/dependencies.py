"""Service dependencies module.

This module defines FastAPI dependencies for constructing application services,
resolving authenticated users, and accessing shared application clients.
"""

from typing import Annotated
from uuid import UUID

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from ai_notes_api.core import decode_access_token
from ai_notes_api.db.models import User
from ai_notes_api.db.session import get_db
from ai_notes_api.exceptions import InvalidTokenError
from ai_notes_api.integrations import openai_client
from ai_notes_api.llm import LLMClient
from ai_notes_api.repositories import (
    ChatMemoryRepository,
    ChatSessionRepository,
    GenerationJobRepository,
    MessageRepository,
    NoteRepository,
    UserRepository,
)
from ai_notes_api.services import (
    AuthService,
    ChatMemoryService,
    ChatSessionService,
    JobService,
    LLMService,
    MessageService,
    NoteService,
)

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

    return NoteService(repository=repository)


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

    return AuthService(repository=repository)


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
    sessions = ChatSessionRepository(session)
    memories = ChatMemoryRepository(session)

    return ChatSessionService(
        session_repository=sessions,
        memory_repository=memories,
    )


def get_message_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> MessageService:
    """Provide a message service instance.

    Args:
        session (AsyncSession): Asynchronous database session provided by FastAPI
            dependency injection.

    Returns:
        MessageService: Configured message service instance.
    """
    sessions = ChatSessionRepository(session)
    messages = MessageRepository(session)

    return MessageService(
        message_repository=messages,
        session_repository=sessions,
    )


def get_llm_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> LLMService:
    """Provide an LLM service instance.

    Args:
        session (AsyncSession): Asynchronous database session provided by FastAPI
            dependency injection.

    Returns:
        LLMService: Configured LLM service instance.
    """
    client = LLMClient(openai_client)
    notes = NoteRepository(session)
    messages = MessageRepository(session)
    sessions = ChatSessionRepository(session)
    memories = ChatMemoryRepository(session)
    notes_service = NoteService(notes)
    sessions_service = ChatSessionService(
        session_repository=sessions,
        memory_repository=memories,
    )
    messages_service = MessageService(messages, sessions)

    return LLMService(
        client=client,
        note_service=notes_service,
        session_service=sessions_service,
        message_service=messages_service,
    )


def get_job_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> JobService:
    """Provide a generation job service instance.

    Args:
        session (AsyncSession): Asynchronous database session provided by FastAPI
            dependency injection.

    Returns:
        JobService: Configured generation job service instance.
    """
    jobs = GenerationJobRepository(session)
    sessions = ChatSessionRepository(session)
    memories = ChatMemoryRepository(session)
    sessions_service = ChatSessionService(
        session_repository=sessions,
        memory_repository=memories,
    )

    return JobService(
        job_repository=jobs,
        session_service=sessions_service,
    )


def get_memory_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ChatMemoryService:
    """Provide a chat memory service instance.

    Args:
        session (AsyncSession): Asynchronous database session provided by FastAPI
            dependency injection.

    Returns:
        ChatMemoryService: Configured chat memory service instance.
    """
    repository = ChatMemoryRepository(session)

    return ChatMemoryService(repository=repository)
