"""LLM service module.

This module provides business logic for generating and streaming LLM responses.
"""

from collections.abc import AsyncGenerator
from typing import Any
from uuid import UUID, uuid4

from ai_notes_api.core import settings
from ai_notes_api.db.models import Message
from ai_notes_api.llm import LLMClient, PromptBuilder
from ai_notes_api.llm.models import LLMResponse, LLMStreamEvent
from ai_notes_api.schemas import (
    AssistantMessageCreateSchema,
    ChatCompletionResponseSchema,
    UserMessageCreateSchema,
)
from ai_notes_api.services.chat_session import ChatSessionService
from ai_notes_api.services.message import MessageService


class LLMService:
    """Service for LLM-related business operations.

    Args:
        client (LLMClient): LLM client used to generate model responses.
        sessions (ChatSessionService): Chat session service used to validate
            access and manage generation locks.
        messages (MessageService): Message service used to persist chat messages.
    """

    def __init__(
        self,
        client: LLMClient,
        sessions: ChatSessionService,
        messages: MessageService,
    ) -> None:
        """Initialize the LLM service.

        Args:
            client (LLMClient): LLM client used by the service.
            sessions (ChatSessionService): Chat session service used by the service.
            messages (MessageService): Message service used by the service.
        """
        self.client = client
        self.sessions = sessions
        self.messages = messages

    def _get_value(self, source: Any, name: str) -> Any:
        """Return a value from an object or dictionary.

        Args:
            source (Any): Object or dictionary to read from.
            name (str): Attribute or dictionary key name.

        Returns:
            Any: Resolved value if found; otherwise, None.
        """
        if source is None:
            return None

        if isinstance(source, dict):
            return source.get(name)

        return getattr(source, name, None)

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
        raw_response = llm_response.raw
        usage = self._get_value(raw_response, "usage")
        model_name = self._get_value(raw_response, "model")
        provider = self._get_value(raw_response, "provider")

        return await self.messages.create_assistant_message(
            user_id=user_id,
            data=AssistantMessageCreateSchema(
                session_id=session_id,
                content=llm_response.text,
                model_name=model_name,
                provider=provider,
                prompt_tokens=self._get_value(usage, "input_tokens"),
                completion_tokens=self._get_value(usage, "output_tokens"),
                total_tokens=self._get_value(usage, "total_tokens"),
            ),
        )

    async def _generate_response_locked(
        self,
        user_id: UUID,
        message: UserMessageCreateSchema,
    ) -> ChatCompletionResponseSchema:
        """Generate and persist an assistant response under an existing lock.

        This method assumes that the chat session generation lock has already been
        acquired by the caller.

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

        input_data = PromptBuilder.build(context_messages)

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

    async def generate_job_response(
        self,
        user_id: UUID,
        generation_id: UUID,
        message: UserMessageCreateSchema,
    ) -> ChatCompletionResponseSchema:
        """Generate and persist an assistant response for an existing generation job.

        Args:
            user_id (UUID): Unique identifier of the user who owns the generation job.
            generation_id (UUID): Unique generation job identifier that owns the
                chat session lock.
            message (UserMessageCreateSchema): Validated user message data.

        Returns:
            ChatCompletionResponseSchema: Generated assistant response data.

        Raises:
            ChatSessionNotFoundError: If no accessible chat session exists.
            GenerationNotFoundError: If the generation job does not own the lock.
        """
        generation_id = uuid4()

        await self.sessions.ensure_generation_lock_owner(
            user_id, message.session_id, generation_id
        )

        try:
            return await self._generate_response_locked(
                user_id=user_id,
                message=message,
            )

        finally:
            await self.sessions.release_generation_lock(
                user_id=user_id,
                session_id=message.session_id,
                generation_id=generation_id,
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
            GenerationInProgressError: If generation is already in progress.
        """
        generation_id = uuid4()

        await self.sessions.ensure_session_owner(user_id, message.session_id)
        await self.sessions.acquire_generation_lock(
            user_id=user_id,
            session_id=message.session_id,
            generation_id=generation_id,
        )

        try:
            return await self._generate_response_locked(
                user_id=user_id,
                message=message,
            )

        finally:
            await self.sessions.release_generation_lock(
                user_id=user_id,
                session_id=message.session_id,
                generation_id=generation_id,
            )

    async def stream_response(
        self,
        user_id: UUID,
        message: UserMessageCreateSchema,
    ) -> AsyncGenerator[LLMStreamEvent]:
        """Stream and persist an assistant response.

        Args:
            user_id (UUID): Unique identifier of the user requesting the
                response.
            message (UserMessageCreateSchema): Validated user message data.

        Yields:
            LLMStreamEvent: Stream event containing a text delta or final
            response.

        Raises:
            ChatSessionNotFoundError: If no accessible chat session exists.
            GenerationInProgressError: If generation is already in progress.
        """
        generation_id = uuid4()

        await self.sessions.ensure_session_owner(user_id, message.session_id)
        await self.sessions.acquire_generation_lock(
            user_id=user_id,
            session_id=message.session_id,
            generation_id=generation_id,
        )

        try:
            await self.messages.create_user_message(
                user_id=user_id,
                data=message,
            )

            context_messages = await self.messages.get_context_messages(
                user_id=user_id,
                session_id=message.session_id,
                limit=settings.llm_context_messages_limit,
            )

            input_data = PromptBuilder.build(context_messages)

            async for event in self.client.stream_response_events(input_data):
                if event.type == "final" and event.response is not None:
                    await self._create_assistant_message_from_response(
                        user_id=user_id,
                        session_id=message.session_id,
                        llm_response=event.response,
                    )

                yield event

        finally:
            await self.sessions.release_generation_lock(
                user_id=user_id,
                session_id=message.session_id,
                generation_id=generation_id,
            )
