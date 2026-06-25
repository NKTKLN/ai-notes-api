"""Chat sessions API router.

This module defines API endpoints for creating and managing chat sessions.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from loguru import logger

from ai_notes_api.api.v1.dependencies import (
    get_chat_session_service,
    get_current_user,
    get_memory_service,
    get_message_service,
)
from ai_notes_api.db.models import User
from ai_notes_api.schemas import (
    ChatMemoryResponseSchema,
    ChatSessionCreateSchema,
    ChatSessionListQuerySchema,
    ChatSessionListResponseSchema,
    ChatSessionResponseSchema,
    ChatSessionUpdateSchema,
    ErrorResponseSchema,
    MessageListQuerySchema,
    MessageListResponseSchema,
    MessageResponseSchema,
    StatusResponseSchema,
)
from ai_notes_api.services import ChatMemoryService, ChatSessionService, MessageService

router = APIRouter(
    prefix="/chat/sessions",
    tags=["Sessions"],
)


@router.post(
    "",
    summary="Create a new chat session",
    description="Create a new chat session and return the created data.",
    response_model=ChatSessionResponseSchema,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {
            "model": ErrorResponseSchema,
            "description": "Invalid authentication credentials",
        },
    },
)
async def create_chat_session(
    data: ChatSessionCreateSchema,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ChatSessionService, Depends(get_chat_session_service)],
) -> ChatSessionResponseSchema:
    """Create a new chat session.

    Args:
        data (ChatSessionCreateSchema): Validated chat session creation data.
        user (User): Current authenticated user.
        service (ChatSessionService): Chat session service dependency used to
            create the chat session.

    Returns:
        ChatSessionResponseSchema: Created chat session data.
    """
    logger.info("Chat session creation requested")

    chat_session = await service.create_chat_session(user.id, data)

    return ChatSessionResponseSchema.model_validate(chat_session)


@router.get(
    "",
    summary="Get chat sessions",
    description="Return a paginated list of chat sessions.",
    response_model=ChatSessionListResponseSchema,
    status_code=status.HTTP_200_OK,
    responses={
        401: {
            "model": ErrorResponseSchema,
            "description": "Invalid authentication credentials",
        },
    },
)
async def get_chat_sessions(
    filters: Annotated[
        ChatSessionListQuerySchema,
        Depends(),
    ],
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ChatSessionService, Depends(get_chat_session_service)],
) -> ChatSessionListResponseSchema:
    """Return a paginated list of chat sessions.

    Args:
        filters (ChatSessionListQuerySchema): Filters and pagination parameters.
        user (User): Current authenticated user.
        service (ChatSessionService): Chat session service dependency used to
            retrieve chat sessions.

    Returns:
        ChatSessionListResponseSchema: Paginated list of chat sessions.
    """
    logger.info(
        "Chat sessions list retrieval requested: limit={}, offset={}, search={}",
        filters.limit,
        filters.offset,
        filters.search,
    )

    chat_sessions = await service.get_chat_sessions_list(user.id, filters)

    return ChatSessionListResponseSchema(
        items=[
            ChatSessionResponseSchema.model_validate(chat_session)
            for chat_session in chat_sessions
        ],
        limit=filters.limit,
        offset=filters.offset,
        total=len(chat_sessions),
    )


@router.get(
    "/{session_id}",
    summary="Get chat session by ID",
    description="Return a chat session by its unique identifier.",
    response_model=ChatSessionResponseSchema,
    status_code=status.HTTP_200_OK,
    responses={
        401: {
            "model": ErrorResponseSchema,
            "description": "Invalid authentication credentials",
        },
        404: {
            "model": ErrorResponseSchema,
            "description": "Chat session not found",
        },
    },
)
async def get_chat_session(
    session_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ChatSessionService, Depends(get_chat_session_service)],
) -> ChatSessionResponseSchema:
    """Return a chat session by its identifier.

    Args:
        session_id (UUID): Unique chat session identifier.
        user (User): Current authenticated user.
        service (ChatSessionService): Chat session service dependency used to
            retrieve the chat session.

    Returns:
        ChatSessionResponseSchema: Chat session data.

    Raises:
        ChatSessionNotFoundError: If no chat session with the given identifier exists.
    """
    logger.info("Chat session retrieval requested: session_id={}", session_id)

    chat_session = await service.get_chat_session(user.id, session_id)

    return ChatSessionResponseSchema.model_validate(chat_session)


@router.patch(
    "/{session_id}",
    summary="Update chat session by ID",
    description="Update a chat session by its unique identifier.",
    response_model=ChatSessionResponseSchema,
    status_code=status.HTTP_200_OK,
    responses={
        401: {
            "model": ErrorResponseSchema,
            "description": "Invalid authentication credentials",
        },
        404: {
            "model": ErrorResponseSchema,
            "description": "Chat session not found",
        },
    },
)
async def update_chat_session(
    session_id: UUID,
    data: ChatSessionUpdateSchema,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ChatSessionService, Depends(get_chat_session_service)],
) -> ChatSessionResponseSchema:
    """Update a chat session by its identifier.

    Args:
        session_id (UUID): Unique chat session identifier to update.
        data (ChatSessionUpdateSchema): Validated chat session update data.
        user (User): Current authenticated user.
        service (ChatSessionService): Chat session service dependency used to
            update the chat session.

    Returns:
        ChatSessionResponseSchema: Updated chat session data.

    Raises:
        ChatSessionNotFoundError: If no chat session with the given identifier exists.
    """
    logger.info("Chat session update requested: session_id={}", session_id)

    chat_session = await service.update_chat_session(user.id, session_id, data)

    return ChatSessionResponseSchema.model_validate(chat_session)


@router.delete(
    "/{session_id}",
    summary="Delete chat session by ID",
    description="Delete a chat session by its unique identifier.",
    response_model=StatusResponseSchema,
    status_code=status.HTTP_200_OK,
    responses={
        401: {
            "model": ErrorResponseSchema,
            "description": "Invalid authentication credentials",
        },
        404: {
            "model": ErrorResponseSchema,
            "description": "Chat session not found",
        },
    },
)
async def delete_chat_session(
    session_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ChatSessionService, Depends(get_chat_session_service)],
) -> StatusResponseSchema:
    """Delete a chat session by its identifier.

    Args:
        session_id (UUID): Unique chat session identifier to delete.
        user (User): Current authenticated user.
        service (ChatSessionService): Chat session service dependency used to
            delete the chat session.

    Returns:
        StatusResponseSchema: Response status.

    Raises:
        ChatSessionNotFoundError: If no chat session with the given identifier exists.
    """
    logger.info("Chat session deletion requested: session_id={}", session_id)

    await service.delete_chat_session(user.id, session_id)

    return StatusResponseSchema(status="deleted")


@router.get(
    "/{session_id}/messages",
    summary="Get chat session messages",
    description="Return a paginated list of messages for a chat session.",
    response_model=MessageListResponseSchema,
    status_code=status.HTTP_200_OK,
    responses={
        401: {
            "model": ErrorResponseSchema,
            "description": "Invalid authentication credentials",
        },
        404: {
            "model": ErrorResponseSchema,
            "description": "Chat session not found",
        },
    },
)
async def get_chat_session_messages(
    session_id: UUID,
    filters: Annotated[
        MessageListQuerySchema,
        Depends(),
    ],
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[MessageService, Depends(get_message_service)],
) -> MessageListResponseSchema:
    """Return a paginated list of chat session messages.

    Args:
        session_id (UUID): Unique chat session identifier.
        filters (MessageListQuerySchema): Filters and pagination parameters.
        user (User): Current authenticated user.
        service (MessageService): Message service dependency used to retrieve messages.

    Returns:
        MessageListResponseSchema: Paginated list of messages.

    Raises:
        ChatSessionNotFoundError: If no accessible chat session exists.
    """
    logger.info("Chat session messages retrieval requested: session_id={}", session_id)

    messages = await service.get_messages_list(user.id, session_id, filters)

    return MessageListResponseSchema(
        items=[MessageResponseSchema.model_validate(message) for message in messages],
        limit=filters.limit,
        offset=filters.offset,
        total=len(messages),
    )


@router.get(
    "/{session_id}/memory",
    summary="Get chat session memory",
    description="Return memory data for a chat session.",
    response_model=ChatMemoryResponseSchema,
    status_code=status.HTTP_200_OK,
    responses={
        401: {
            "model": ErrorResponseSchema,
            "description": "Invalid authentication credentials",
        },
        404: {
            "model": ErrorResponseSchema,
            "description": "Chat memory not found",
        },
    },
)
async def get_chat_session_memory(
    session_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ChatMemoryService, Depends(get_memory_service)],
) -> ChatMemoryResponseSchema:
    """Return chat memory for a chat session.

    Args:
        session_id (UUID): Unique chat session identifier.
        user (User): Current authenticated user.
        service (ChatMemoryService): Chat memory service dependency used to
            retrieve chat memory.

    Returns:
        ChatMemoryResponseSchema: Chat memory data.

    Raises:
        ChatMemoryNotFoundError: If no accessible chat memory exists for the
            given chat session.
    """
    logger.info("Chat session memory retrieval requested: session_id={}", session_id)

    memory = await service.get_by_session_id(user.id, session_id)

    return ChatMemoryResponseSchema.model_validate(memory)
