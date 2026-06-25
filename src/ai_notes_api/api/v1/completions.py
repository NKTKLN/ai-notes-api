"""Chat completions API router.

This module defines API endpoints for generating and streaming chat completion
responses.
"""

import asyncio
import json
from collections.abc import AsyncGenerator
from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from loguru import logger
from sse_starlette import EventSourceResponse

from ai_notes_api.api.v1.dependencies import get_current_user, get_llm_service
from ai_notes_api.db.models import User
from ai_notes_api.llm.schemas import LLMStreamEvent
from ai_notes_api.schemas import ErrorResponseSchema, UserMessageCreateSchema
from ai_notes_api.services import LLMService

router = APIRouter(
    prefix="/chat/completions",
    tags=["Completions"],
)


def llm_event_to_sse(event: LLMStreamEvent) -> dict[str, str]:
    """Convert an LLM stream event to an SSE event payload.

    Args:
        event (LLMStreamEvent): LLM stream event to convert.

    Returns:
        dict[str, str]: Server-sent event payload.
    """
    payload = asdict(event)

    return {
        "event": event.type,
        "data": json.dumps(payload, ensure_ascii=False, default=str),
    }


@router.post(
    "/stream",
    summary="Stream chat completion",
    description="Generate and stream an assistant response for a chat session.",
    status_code=status.HTTP_200_OK,
    responses={
        404: {
            "model": ErrorResponseSchema,
            "description": "Chat session not found",
        },
    },
)
async def stream_chat_completion(
    request: Request,
    message: UserMessageCreateSchema,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[LLMService, Depends(get_llm_service)],
) -> EventSourceResponse:
    """Stream an assistant response for a chat session.

    Args:
        request (Request): FastAPI request object used to detect client disconnects.
        message (UserMessageCreateSchema): Validated user message data.
        user (User): Current authenticated user.
        service (LLMService): LLM service dependency used to stream the
            assistant response.

    Returns:
        EventSourceResponse: Server-sent events response.

    Raises:
        ChatSessionNotFoundError: If no accessible chat session exists.
    """
    logger.info(
        "Chat completion stream requested: session_id={}",
        message.session_id,
    )

    async def event_generator() -> AsyncGenerator[dict[str, str]]:
        """Yield server-sent events from the LLM stream.

        Yields:
            dict[str, str]: Server-sent event payload.
        """
        try:
            async for event in service.stream_response(
                user_id=user.id,
                message=message,
            ):
                if await request.is_disconnected():
                    break

                yield llm_event_to_sse(event)

        except asyncio.CancelledError:
            raise

        except Exception as exc:
            logger.exception("Chat completion stream failed")

            yield {
                "event": "error",
                "data": json.dumps(
                    {
                        "message": str(exc),
                    },
                    ensure_ascii=False,
                ),
            }

    return EventSourceResponse(
        event_generator(),
        ping=15,
    )
