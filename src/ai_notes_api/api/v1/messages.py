"""Messages API router.

This module defines API endpoints for reading and deleting messages.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from loguru import logger

from ai_notes_api.api.v1.dependencies import get_current_user, get_message_service
from ai_notes_api.db.models import User
from ai_notes_api.schemas import (
    ErrorResponseSchema,
    MessageResponseSchema,
    StatusResponseSchema,
)
from ai_notes_api.services import MessageService

router = APIRouter(
    prefix="/chat/messages",
    tags=["Messages"],
)


@router.get(
    "/{message_id}",
    summary="Get message by ID",
    description="Return a message by its unique identifier.",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_200_OK,
    responses={
        401: {
            "model": ErrorResponseSchema,
            "description": "Invalid authentication credentials",
        },
        404: {
            "model": ErrorResponseSchema,
            "description": "Message not found",
        },
    },
)
async def get_message(
    message_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[MessageService, Depends(get_message_service)],
) -> MessageResponseSchema:
    """Return a message by its identifier.

    Args:
        message_id (UUID): Unique message identifier.
        user (User): Current authenticated user.
        service (MessageService): Message service dependency used to retrieve
            the message.

    Returns:
        MessageResponseSchema: Message data.

    Raises:
        MessageNotFoundError: If no message with the given identifier exists.
    """
    logger.info("Message retrieval requested: message_id={}", message_id)

    message = await service.get_message(user.id, message_id)

    return MessageResponseSchema.model_validate(message)


@router.delete(
    "/{message_id}",
    summary="Delete message by ID",
    description="Delete a message by its unique identifier.",
    response_model=StatusResponseSchema,
    status_code=status.HTTP_200_OK,
    responses={
        401: {
            "model": ErrorResponseSchema,
            "description": "Invalid authentication credentials",
        },
        404: {
            "model": ErrorResponseSchema,
            "description": "Message not found",
        },
    },
)
async def delete_message(
    message_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[MessageService, Depends(get_message_service)],
) -> StatusResponseSchema:
    """Delete a message by its identifier.

    Args:
        message_id (UUID): Unique message identifier to delete.
        user (User): Current authenticated user.
        service (MessageService): Message service dependency used to delete the
            message.

    Returns:
        StatusResponseSchema: Response status.

    Raises:
        MessageNotFoundError: If no message with the given identifier exists.
    """
    logger.info("Message deletion requested: message_id={}", message_id)

    await service.delete_message(user.id, message_id)

    return StatusResponseSchema(status="deleted")
