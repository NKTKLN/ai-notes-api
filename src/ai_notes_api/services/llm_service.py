"""LLM service module.

This module provides business logic for generating and streaming LLM responses.
"""

from collections.abc import AsyncGenerator
from uuid import UUID

from ai_notes_api.core import settings
from ai_notes_api.db.models import Message
from ai_notes_api.llm import LLMClient, PromptBuilder
from ai_notes_api.llm.models import LLMResponse, LLMStreamEvent
from ai_notes_api.schemas import (
    AssistantMessageCreateSchema,
    ChatCompletionResponseSchema,
    UserMessageCreateSchema,
)
from ai_notes_api.services.message import MessageService


class LLMService:
    """Service for LLM-related business operations.

    Args:
        client (LLMClient): LLM client used to generate model responses.
        messages (MessageService): Message service used to persist chat messages.
    """

    def __init__(self, client: LLMClient, messages: MessageService) -> None:
        """Initialize the LLM service.

        Args:
            client (LLMClient): LLM client used by the service.
            messages (MessageService): Message service used by the service.
        """
        self.client = client
        self.messages = messages
        self.prompt_builder = PromptBuilder()

    async def _create_assistant_message_from_response(
        self,
        user_id: UUID,
        session_id: UUID,
        llm_response: LLMResponse,
    ) -> Message:
        """Create an assistant message from an LLM response.

        Args:
            user_id (UUID): Unique identifier of the user who owns the chat session.
            session_id (UUID): Unique chat session identifier.
            llm_response (LLMResponse): LLM response used to create the
                assistant message.

        Returns:
            Message: Created assistant message.

        Raises:
            ChatSessionNotFoundError: If no accessible chat session exists.
        """
        return await self.messages.create_assistant_message(
            user_id=user_id,
            data=AssistantMessageCreateSchema(
                session_id=session_id,
                content=llm_response.text,
                provider=getattr(llm_response.raw, "provider", None),
                model_name=getattr(llm_response.raw, "model_name", None),
                prompt_tokens=getattr(llm_response.raw, "prompt_tokens", None),
                completion_tokens=getattr(
                    llm_response.raw,
                    "completion_tokens",
                    None,
                ),
                total_tokens=getattr(llm_response.raw, "total_tokens", None),
            ),
        )

    async def generate_response(
        self,
        user_id: UUID,
        message: UserMessageCreateSchema,
    ) -> ChatCompletionResponseSchema:
        """Generate and persist an assistant response.

        Args:
            user_id (UUID): Unique identifier of the user requesting the response.
            message (UserMessageCreateSchema): Validated user message data.

        Returns:
            ChatCompletionResponseSchema: Generated assistant response data.

        Raises:
            ChatSessionNotFoundError: If no accessible chat session exists.
        """
        await self.messages.create_user_message(
            user_id=user_id,
            data=message,
        )

        context_messages = await self.messages.get_context_messages(
            user_id=user_id,
            session_id=message.session_id,
            limit=settings.llm_context_messages_limit,
        )

        input_data = self.prompt_builder.build(context_messages)

        llm_response = await self.client.create_response(input_data)

        assistant_message = await self._create_assistant_message_from_response(
            user_id=user_id,
            session_id=message.session_id,
            llm_response=llm_response,
        )

        return ChatCompletionResponseSchema(
            message_id=assistant_message.id,
            answer=llm_response.text,
            provider=assistant_message.provider or "",
            model_name=assistant_message.model_name or "",
            prompt_tokens=assistant_message.prompt_tokens,
            completion_tokens=assistant_message.completion_tokens,
            total_tokens=assistant_message.total_tokens,
        )

    async def stream_response(
        self,
        user_id: UUID,
        message: UserMessageCreateSchema,
    ) -> AsyncGenerator[LLMStreamEvent]:
        """Stream and persist an assistant response.

        Args:
            user_id (UUID): Unique identifier of the user requesting the response.
            message (UserMessageCreateSchema): Validated user message data.

        Yields:
            LLMStreamEvent: Stream event containing a text delta or final response.

        Raises:
            ChatSessionNotFoundError: If no accessible chat session exists.
        """
        await self.messages.create_user_message(
            user_id=user_id,
            data=message,
        )

        context_messages = await self.messages.get_context_messages(
            user_id=user_id,
            session_id=message.session_id,
            limit=settings.llm_context_messages_limit,
        )

        input_data = self.prompt_builder.build(context_messages)

        async for event in self.client.stream_response_events(input_data):
            if event.type == "final" and event.response is not None:
                await self._create_assistant_message_from_response(
                    user_id=user_id,
                    session_id=message.session_id,
                    llm_response=event.response,
                )

            yield event
