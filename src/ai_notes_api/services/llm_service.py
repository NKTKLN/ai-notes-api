"""LLM service module.

This module provides business logic for generating and streaming LLM responses.
"""

from collections.abc import AsyncGenerator
from typing import Any, ClassVar
from uuid import UUID, uuid4

from ai_notes_api.db.models import Message
from ai_notes_api.llm import LLMClient
from ai_notes_api.llm.embeddings import EmbeddingClient
from ai_notes_api.llm.schemas import LLMResponse, LLMStreamEvent
from ai_notes_api.schemas import (
    AssistantMessageCreateSchema,
    ChatCompletionResponseSchema,
    UserMessageCreateSchema,
)
from ai_notes_api.services.chat_session import ChatSessionService
from ai_notes_api.services.document_chunk import DocumentChunkService
from ai_notes_api.services.llm_context import LLMContextBuilder
from ai_notes_api.services.message import MessageService
from ai_notes_api.services.note import NoteService
from ai_notes_api.tools import build_registry
from ai_notes_api.tools.registry import ToolRegistry
from ai_notes_api.workers.tasks.memory import update_chat_memory_summary


class LLMService:
    """Service for LLM-related business operations.

    Args:
        client (LLMClient): LLM client used to generate model responses.
        embeddings (EmbeddingClient): Embedding client used to embed questions
            for document chunk retrieval.
        note_service (NoteService): Note service used by LLM tools.
        session_service (ChatSessionService): Chat session service used to
            validate access and manage generation locks.
        message_service (MessageService): Message service used to persist chat
            messages.
        document_chunks_service (DocumentChunkService): Document chunk service
            used to retrieve grounding context via vector search.

    Attributes:
        SYSTEM_PROMPT (ClassVar[str]): System prompt prepended to the chat context.
    """

    SYSTEM_PROMPT: ClassVar[str] = (
        "Respond in the user's language. Do not invent facts about the user. "
        "Use note-management tools only when the user clearly asks for it."
    )

    def __init__(  # noqa: PLR0913
        self,
        client: LLMClient,
        embeddings: EmbeddingClient,
        note_service: NoteService,
        session_service: ChatSessionService,
        message_service: MessageService,
        document_chunks_service: DocumentChunkService,
    ) -> None:
        """Initialize the LLM service.

        Args:
            client (LLMClient): LLM client used by the service.
            embeddings (EmbeddingClient): Embedding client used by the service.
            note_service (NoteService): Note service used by LLM tools.
            session_service (ChatSessionService): Chat session service used by
                the service.
            message_service (MessageService): Message service used by the service.
            document_chunks_service (DocumentChunkService): Document chunk service
                used by the service.
        """
        self.client = client
        self.notes = note_service
        self.sessions = session_service
        self.messages = message_service
        self.context = LLMContextBuilder(
            embeddings=embeddings,
            message_service=message_service,
            chunk_service=document_chunks_service,
        )

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

        assistant_message = await self.messages.create_assistant_message(
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

        update_chat_memory_summary.delay(str(user_id), str(session_id))

        return assistant_message

    async def _collect_tool_outputs(
        self,
        tools_registry: ToolRegistry,
        input_data: list[dict[str, Any]],
        llm_response: LLMResponse,
    ) -> list[dict[str, Any]]:
        """Execute requested tool calls and append their outputs to the input.

        Args:
            tools_registry (ToolRegistry): Registry used to execute tool calls.
            input_data (list[dict[str, Any]]): Current LLM input messages.
            llm_response (LLMResponse): Model response carrying the tool calls
                and raw output items.

        Returns:
            list[dict[str, Any]]: New input messages extended with the model
            output items and the corresponding tool call results.
        """
        tool_outputs = [*input_data, *llm_response.output_items]

        for tool_call in llm_response.tool_calls:
            tool_result = await tools_registry.call(
                name=tool_call.name,
                arguments=tool_call.arguments,
            )

            tool_outputs.append(
                {
                    "type": "function_call_output",
                    "call_id": tool_call.call_id,
                    "output": tool_result,
                }
            )

        return tool_outputs

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
        tools_registry = build_registry(notes_service=self.notes, user_id=user_id)
        tools = tools_registry.get_tools()

        input_data = await self.context.build(
            user_id=user_id,
            session_id=message.session_id,
            question=message.content,
        )

        await self.messages.create_user_message(
            user_id=user_id,
            data=message,
        )

        while True:
            llm_response = await self.client.create_response(
                instructions=self.SYSTEM_PROMPT,
                input_data=input_data,
                tools=tools,
            )

            if not llm_response.tool_calls:
                break

            input_data = await self._collect_tool_outputs(
                tools_registry=tools_registry,
                input_data=input_data,
                llm_response=llm_response,
            )

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
            user_id (UUID): Unique identifier of the user requesting the response.
            message (UserMessageCreateSchema): Validated user message data.

        Yields:
            LLMStreamEvent: Stream event containing a text delta or final response.

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
            tools_registry = build_registry(notes_service=self.notes, user_id=user_id)
            tools = tools_registry.get_tools()

            input_data = await self.context.build(
                user_id=user_id,
                session_id=message.session_id,
                question=message.content,
            )

            await self.messages.create_user_message(
                user_id=user_id,
                data=message,
            )

            llm_response: LLMResponse | None = None

            while True:
                llm_response = None

                async for event in self.client.stream_response_events(
                    instructions=self.SYSTEM_PROMPT,
                    input_data=input_data,
                    tools=tools,
                ):
                    if event.type == "final" and event.response is not None:
                        llm_response = event.response

                    yield event

                if llm_response is None or not llm_response.tool_calls:
                    break

                input_data = await self._collect_tool_outputs(
                    tools_registry=tools_registry,
                    input_data=input_data,
                    llm_response=llm_response,
                )

            if llm_response is not None:
                await self._create_assistant_message_from_response(
                    user_id=user_id,
                    session_id=message.session_id,
                    llm_response=llm_response,
                )

        finally:
            await self.sessions.release_generation_lock(
                user_id=user_id,
                session_id=message.session_id,
                generation_id=generation_id,
            )
