"""Tests for LLM service."""

from collections.abc import AsyncGenerator, Generator
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import patch
from uuid import UUID

import pytest

from ai_notes_api.core import settings
from ai_notes_api.db.models import DocumentChunk, Message, MessageRole
from ai_notes_api.exceptions import ChatSessionNotFoundError
from ai_notes_api.llm import LLMClient
from ai_notes_api.llm.embeddings import EmbeddingClient
from ai_notes_api.llm.schemas import LLMResponse, LLMStreamEvent, LLMToolCall
from ai_notes_api.schemas import (
    AssistantMessageCreateSchema,
    UserMessageCreateSchema,
)
from ai_notes_api.services.chat_memory import ChatMemoryService
from ai_notes_api.services.chat_session import ChatSessionService
from ai_notes_api.services.document_chunk import DocumentChunkService
from ai_notes_api.services.llm_context import LLMContextBuilder
from ai_notes_api.services.llm_service import LLMService
from ai_notes_api.services.message import MessageService
from ai_notes_api.services.note import NoteService

TEST_USER_ID = UUID("11111111-1111-1111-1111-111111111111")
TEST_SESSION_ID = UUID("22222222-2222-2222-2222-222222222222")
TEST_MESSAGE_ID = UUID("33333333-3333-3333-3333-333333333333")
TEST_DOCUMENT_ID = UUID("44444444-4444-4444-4444-444444444444")
TEST_CHUNK_ID = UUID("55555555-5555-5555-5555-555555555555")


@pytest.fixture(autouse=True)
def patch_memory_task() -> Generator[None]:
    """Patch the Celery memory-summary task to avoid hitting the broker.

    Persisting an assistant message enqueues ``update_chat_memory_summary``;
    without this patch the ``.delay()`` call would block on the message broker.

    Yields:
        None: Control while the Celery task is patched.
    """
    with patch("ai_notes_api.services.llm_service.update_chat_memory_summary"):
        yield


class FakeMessageService:
    """Fake message service recording calls for LLM service testing."""

    def __init__(self) -> None:
        """Initialize the fake message service."""
        self.context_messages: list[Message] = []
        self.context_limit: int | None = None
        self.created_user_message: UserMessageCreateSchema | None = None
        self.created_assistant_data: list[AssistantMessageCreateSchema] = []
        self.raise_on_user_message: Exception | None = None

    async def create_user_message(
        self,
        user_id: UUID,  # noqa: ARG002
        data: UserMessageCreateSchema,
    ) -> Message:
        """Record and create a user message."""
        if self.raise_on_user_message is not None:
            raise self.raise_on_user_message

        self.created_user_message = data

        return Message(
            id=TEST_MESSAGE_ID,
            session_id=data.session_id,
            content=data.content,
            role=MessageRole.USER,
        )

    async def get_context_messages(
        self,
        user_id: UUID,  # noqa: ARG002
        session_id: UUID,  # noqa: ARG002
        limit: int,
    ) -> list[Message]:
        """Return the configured context messages."""
        self.context_limit = limit
        return self.context_messages

    async def create_assistant_message(
        self,
        user_id: UUID,  # noqa: ARG002
        data: AssistantMessageCreateSchema,
    ) -> Message:
        """Record and create an assistant message."""
        self.created_assistant_data.append(data)

        return Message(
            id=TEST_MESSAGE_ID,
            session_id=data.session_id,
            content=data.content,
            role=MessageRole.ASSISTANT,
            provider=data.provider,
            model_name=data.model_name,
            prompt_tokens=data.prompt_tokens,
            completion_tokens=data.completion_tokens,
            total_tokens=data.total_tokens,
        )


class FakeChatSessionService:
    """Fake chat session service recording lock operations for LLM testing."""

    def __init__(self) -> None:
        """Initialize the fake chat session service."""
        self.ensure_session_owner_called = False
        self.acquired_generation_id: UUID | None = None
        self.released_generation_id: UUID | None = None
        self.ensured_lock_owner_id: UUID | None = None

    async def ensure_session_owner(
        self,
        user_id: UUID,  # noqa: ARG002
        session_id: UUID,  # noqa: ARG002
    ) -> None:
        """Record that the session owner check was performed."""
        self.ensure_session_owner_called = True

    async def acquire_generation_lock(
        self,
        user_id: UUID,  # noqa: ARG002
        session_id: UUID,  # noqa: ARG002
        generation_id: UUID,
    ) -> None:
        """Record the acquired generation lock."""
        self.acquired_generation_id = generation_id

    async def release_generation_lock(
        self,
        user_id: UUID,  # noqa: ARG002
        session_id: UUID,  # noqa: ARG002
        generation_id: UUID,
    ) -> None:
        """Record the released generation lock."""
        self.released_generation_id = generation_id

    async def ensure_generation_lock_owner(
        self,
        user_id: UUID,  # noqa: ARG002
        session_id: UUID,  # noqa: ARG002
        generation_id: UUID,
    ) -> None:
        """Record the generation lock ownership check."""
        self.ensured_lock_owner_id = generation_id


class FakeLLMClient:
    """Fake LLM client returning preconfigured responses and stream events."""

    def __init__(self) -> None:
        """Initialize the fake LLM client."""
        self.response: LLMResponse | None = None
        self.events: list[LLMStreamEvent] = []
        # Optional queues used to return a different result per call, e.g. to
        # drive the tool-calls loop across successive model invocations.
        self.responses: list[LLMResponse] = []
        self.event_batches: list[list[LLMStreamEvent]] = []
        self.create_call_count = 0
        self.stream_call_count = 0
        self.create_input: Any = None
        self.stream_input: Any = None
        self.create_tools: Any = None
        self.stream_tools: Any = None
        self.create_instructions: str | None = None
        self.stream_instructions: str | None = None

    async def create_response(
        self,
        input_data: str | list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        instructions: str | None = None,
    ) -> LLMResponse:
        """Return the configured response (or the next queued one)."""
        self.create_call_count += 1
        self.create_input = input_data
        self.create_tools = tools
        self.create_instructions = instructions

        if self.responses:
            return self.responses.pop(0)

        assert self.response is not None
        return self.response

    async def stream_response_events(
        self,
        input_data: str | list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        instructions: str | None = None,
    ) -> AsyncGenerator[LLMStreamEvent]:
        """Yield the configured stream events (or the next queued batch)."""
        self.stream_call_count += 1
        self.stream_input = input_data
        self.stream_tools = tools
        self.stream_instructions = instructions

        events = self.event_batches.pop(0) if self.event_batches else self.events

        for event in events:
            yield event


class FakeEmbeddingClient:
    """Fake embedding client recording embedded texts for LLM service testing."""

    def __init__(self) -> None:
        """Initialize the fake embedding client."""
        self.embedded_texts: list[str] | None = None
        self.embedding: list[float] = [0.1, 0.2, 0.3]

    async def create_embedding(self, texts: list[str]) -> list[list[float]]:
        """Record the texts and return one embedding vector per text."""
        self.embedded_texts = texts
        return [self.embedding for _ in texts]


class FakeDocumentChunkService:
    """Fake document chunk service recording vector searches for LLM testing."""

    def __init__(self) -> None:
        """Initialize the fake document chunk service."""
        self.chunks: list[DocumentChunk] = []
        self.search_query_embedding: list[float] | None = None
        self.search_top_k: int | None = None

    async def vector_search(
        self,
        user_id: UUID,  # noqa: ARG002
        session_id: UUID,  # noqa: ARG002
        query_embedding: list[float],
        top_k: int = 5,
    ) -> list[DocumentChunk]:
        """Record the search parameters and return the configured chunks."""
        self.search_query_embedding = query_embedding
        self.search_top_k = top_k
        return self.chunks


class FakeChatMemoryService:
    """Fake chat memory service returning long-term memory for LLM testing."""

    def __init__(self) -> None:
        """Initialize the fake chat memory service."""
        self.memory: Any = SimpleNamespace(facts=[], summary="")

    async def get_by_session_id(
        self,
        user_id: UUID,  # noqa: ARG002
        session_id: UUID,  # noqa: ARG002
    ) -> Any:
        """Return the configured chat memory."""
        return self.memory


class FakeNoteService:
    """Fake note service used to build the LLM tool registry."""

    def __init__(self) -> None:
        """Initialize the fake note service."""
        self.notes: list[Any] = []

    async def get_notes_list(
        self,
        user_id: UUID,  # noqa: ARG002
        filters: Any,  # noqa: ARG002
    ) -> list[Any]:
        """Return the configured notes."""
        return self.notes


class FakeToolRegistry:
    """Fake tool registry recording tool executions for LLM service testing."""

    def __init__(self) -> None:
        """Initialize the fake tool registry."""
        self.calls: list[tuple[str, str]] = []

    def get_tools(self) -> list[dict[str, Any]]:
        """Return an empty tool schema list."""
        return []

    async def call(self, name: str, arguments: str) -> str:
        """Record and execute a tool call."""
        self.calls.append((name, arguments))
        return "tool-result"


def _build_service() -> tuple[FakeLLMClient, FakeMessageService, LLMService]:
    """Build an LLM service wired with fakes.

    The embedding client and document chunk service fakes are reachable through
    ``service.context.embeddings`` and ``service.context.chunks`` for assertions.
    """
    client = FakeLLMClient()
    messages = FakeMessageService()
    sessions = FakeChatSessionService()
    notes = FakeNoteService()
    embeddings = FakeEmbeddingClient()
    chunks = FakeDocumentChunkService()
    memories = FakeChatMemoryService()

    context_builder = LLMContextBuilder(
        embeddings=cast(EmbeddingClient, embeddings),
        message_service=cast(MessageService, messages),
        chunk_service=cast(DocumentChunkService, chunks),
        memory_service=cast(ChatMemoryService, memories),
    )

    service = LLMService(
        client=cast(LLMClient, client),
        note_service=cast(NoteService, notes),
        session_service=cast(ChatSessionService, sessions),
        message_service=cast(MessageService, messages),
        context_builder=context_builder,
    )

    return client, messages, service


def _user_message(content: str = "Hello") -> UserMessageCreateSchema:
    """Return a user message create schema for the test session."""
    return UserMessageCreateSchema(session_id=TEST_SESSION_ID, content=content)


def _raw_metadata() -> SimpleNamespace:
    """Return a raw provider response carrying token and model metadata."""
    return SimpleNamespace(
        provider="openai",
        model="gpt-4",
        usage=SimpleNamespace(
            input_tokens=10,
            output_tokens=20,
            total_tokens=30,
        ),
    )


@pytest.mark.asyncio
async def test_generate_response_persists_and_returns_metadata() -> None:
    """Test that generating a response persists messages and returns metadata."""
    client, messages, service = _build_service()
    client.response = LLMResponse(text="Hi there", raw=_raw_metadata())

    result = await service.generate_response(
        user_id=TEST_USER_ID,
        message=_user_message(),
    )

    assert messages.created_user_message is not None
    assert messages.created_user_message.content == "Hello"
    assert messages.created_user_message.session_id == TEST_SESSION_ID

    assert len(messages.created_assistant_data) == 1
    assistant_data = messages.created_assistant_data[0]
    assert assistant_data.content == "Hi there"
    assert assistant_data.provider == "openai"
    assert assistant_data.model_name == "gpt-4"
    assert assistant_data.prompt_tokens == 10
    assert assistant_data.completion_tokens == 20
    assert assistant_data.total_tokens == 30

    assert result.message_id == TEST_MESSAGE_ID
    assert result.answer == "Hi there"
    assert result.provider == "openai"
    assert result.model_name == "gpt-4"
    assert result.prompt_tokens == 10
    assert result.completion_tokens == 20
    assert result.total_tokens == 30


@pytest.mark.asyncio
async def test_generate_response_builds_prompt_from_context() -> None:
    """Test that the prompt is built from context messages and passed to client."""
    client, messages, service = _build_service()
    client.response = LLMResponse(text="Answer", raw=_raw_metadata())
    # Context is fetched before the current turn is persisted, so it holds only
    # prior messages and is passed to the prompt builder as-is.
    messages.context_messages = [
        Message(
            id=TEST_MESSAGE_ID,
            session_id=TEST_SESSION_ID,
            content="Earlier message",
            role=MessageRole.USER,
        )
    ]

    await service.generate_response(
        user_id=TEST_USER_ID,
        message=_user_message(),
    )

    assert isinstance(client.create_input, list)
    assert client.create_instructions == LLMService.SYSTEM_PROMPT
    assert any(item["content"] == "Earlier message" for item in client.create_input)


@pytest.mark.asyncio
async def test_generate_response_uses_context_messages_limit() -> None:
    """Test that the configured context message limit is forwarded."""
    client, messages, service = _build_service()
    client.response = LLMResponse(text="Answer", raw=_raw_metadata())

    await service.generate_response(
        user_id=TEST_USER_ID,
        message=_user_message(),
    )

    assert messages.context_limit == settings.llm_context_messages_limit


@pytest.mark.asyncio
async def test_generate_response_handles_missing_metadata() -> None:
    """Test that missing provider metadata falls back to defaults."""
    client, messages, service = _build_service()
    client.response = LLMResponse(text="Answer", raw=None)

    result = await service.generate_response(
        user_id=TEST_USER_ID,
        message=_user_message(),
    )

    assistant_data = messages.created_assistant_data[0]
    assert assistant_data.provider is None
    assert assistant_data.model_name is None
    assert assistant_data.prompt_tokens is None

    assert result.provider == ""
    assert result.model_name == ""
    assert result.prompt_tokens is None
    assert result.completion_tokens is None
    assert result.total_tokens is None


@pytest.mark.asyncio
async def test_generate_response_propagates_session_not_found() -> None:
    """Test that a missing session error is propagated without calling the client."""
    client, messages, service = _build_service()
    messages.raise_on_user_message = ChatSessionNotFoundError()

    with pytest.raises(ChatSessionNotFoundError):
        await service.generate_response(
            user_id=TEST_USER_ID,
            message=_user_message(),
        )

    assert client.create_input is None
    assert messages.created_assistant_data == []


@pytest.mark.asyncio
async def test_stream_response_yields_events_and_persists_final() -> None:
    """Test that streaming yields all events and persists the final response."""
    client, messages, service = _build_service()
    final_response = LLMResponse(text="Hello", raw=_raw_metadata())
    client.events = [
        LLMStreamEvent(type="delta", delta="Hel"),
        LLMStreamEvent(type="delta", delta="lo"),
        LLMStreamEvent(type="final", response=final_response),
    ]

    events = [
        event
        async for event in service.stream_response(
            user_id=TEST_USER_ID,
            message=_user_message(),
        )
    ]

    assert [event.type for event in events] == ["delta", "delta", "final"]
    assert [event.delta for event in events[:2]] == ["Hel", "lo"]

    assert messages.created_user_message is not None
    assert len(messages.created_assistant_data) == 1
    assert messages.created_assistant_data[0].content == "Hello"
    assert messages.created_assistant_data[0].provider == "openai"


@pytest.mark.asyncio
async def test_stream_response_without_final_does_not_persist() -> None:
    """Test that streaming without a final event persists no assistant message."""
    client, messages, service = _build_service()
    client.events = [
        LLMStreamEvent(type="delta", delta="Hel"),
        LLMStreamEvent(type="delta", delta="lo"),
    ]

    events = [
        event
        async for event in service.stream_response(
            user_id=TEST_USER_ID,
            message=_user_message(),
        )
    ]

    assert len(events) == 2
    assert messages.created_assistant_data == []


@pytest.mark.asyncio
async def test_stream_response_final_without_response_does_not_persist() -> None:
    """Test that a final event without a response persists no assistant message."""
    client, messages, service = _build_service()
    client.events = [
        LLMStreamEvent(type="final", response=None),
    ]

    events = [
        event
        async for event in service.stream_response(
            user_id=TEST_USER_ID,
            message=_user_message(),
        )
    ]

    assert len(events) == 1
    assert messages.created_assistant_data == []


@pytest.mark.asyncio
async def test_stream_response_propagates_session_not_found() -> None:
    """Test that a missing session error is propagated before streaming."""
    client, messages, service = _build_service()
    client.events = [LLMStreamEvent(type="delta", delta="Hi")]
    messages.raise_on_user_message = ChatSessionNotFoundError()

    with pytest.raises(ChatSessionNotFoundError):
        async for _ in service.stream_response(
            user_id=TEST_USER_ID,
            message=_user_message(),
        ):
            pass

    assert client.stream_input is None
    assert messages.created_assistant_data == []


@pytest.mark.asyncio
async def test_generate_response_executes_tool_calls_then_finishes() -> None:
    """Test that requested tool calls are executed and the model is re-invoked."""
    client, messages, service = _build_service()
    registry = FakeToolRegistry()
    client.responses = [
        LLMResponse(
            text="",
            tool_calls=[
                LLMToolCall(name="search_notes", arguments="{}", call_id="call-1")
            ],
            output_items=[{"type": "function_call", "call_id": "call-1"}],
            raw=None,
        ),
        LLMResponse(text="Final answer", raw=_raw_metadata()),
    ]

    with patch(
        "ai_notes_api.services.llm_service.build_registry",
        return_value=registry,
    ):
        result = await service.generate_response(
            user_id=TEST_USER_ID,
            message=_user_message(),
        )

    assert registry.calls == [("search_notes", "{}")]
    assert client.create_call_count == 2
    assert result.answer == "Final answer"
    assert messages.created_assistant_data[0].content == "Final answer"


@pytest.mark.asyncio
async def test_stream_response_executes_tool_calls_then_finishes() -> None:
    """Test that streaming executes tool calls and re-streams until completion."""
    client, messages, service = _build_service()
    registry = FakeToolRegistry()
    client.event_batches = [
        [
            LLMStreamEvent(
                type="final",
                response=LLMResponse(
                    text="",
                    tool_calls=[
                        LLMToolCall(name="search_notes", arguments="{}", call_id="c1")
                    ],
                    output_items=[{"type": "function_call", "call_id": "c1"}],
                    raw=None,
                ),
            )
        ],
        [
            LLMStreamEvent(type="delta", delta="Done"),
            LLMStreamEvent(
                type="final",
                response=LLMResponse(text="Done", raw=_raw_metadata()),
            ),
        ],
    ]

    with patch(
        "ai_notes_api.services.llm_service.build_registry",
        return_value=registry,
    ):
        events = [
            event
            async for event in service.stream_response(
                user_id=TEST_USER_ID,
                message=_user_message(),
            )
        ]

    assert registry.calls == [("search_notes", "{}")]
    assert client.stream_call_count == 2
    assert [event.type for event in events] == ["final", "delta", "final"]
    assert len(messages.created_assistant_data) == 1
    assert messages.created_assistant_data[0].content == "Done"


@pytest.mark.asyncio
async def test_generate_response_embeds_question_for_retrieval() -> None:
    """Test that the question is embedded and used for chunk vector search."""
    client, _messages, service = _build_service()
    client.response = LLMResponse(text="Answer", raw=_raw_metadata())

    embeddings = cast(FakeEmbeddingClient, service.context.embeddings)
    chunks = cast(FakeDocumentChunkService, service.context.chunks)

    await service.generate_response(
        user_id=TEST_USER_ID,
        message=_user_message(content="What is RAG?"),
    )

    assert embeddings.embedded_texts == ["What is RAG?"]
    assert chunks.search_query_embedding == embeddings.embedding
    assert chunks.search_top_k == 5


@pytest.mark.asyncio
async def test_generate_response_includes_retrieved_chunks_in_prompt() -> None:
    """Test that retrieved document chunks are injected into the LLM prompt."""
    client, _messages, service = _build_service()
    client.response = LLMResponse(text="Answer", raw=_raw_metadata())

    chunks = cast(FakeDocumentChunkService, service.context.chunks)
    chunks.chunks = [
        DocumentChunk(
            id=TEST_CHUNK_ID,
            document_id=TEST_DOCUMENT_ID,
            content="Relevant chunk content",
        )
    ]

    await service.generate_response(
        user_id=TEST_USER_ID,
        message=_user_message(),
    )

    assert isinstance(client.create_input, list)
    assert any(
        "Relevant chunk content" in str(item.get("content", ""))
        for item in client.create_input
    )


@pytest.mark.asyncio
async def test_generate_response_includes_question_in_prompt() -> None:
    """Test that the user question is included as a prompt message."""
    client, _messages, service = _build_service()
    client.response = LLMResponse(text="Answer", raw=_raw_metadata())

    await service.generate_response(
        user_id=TEST_USER_ID,
        message=_user_message(content="My question"),
    )

    assert isinstance(client.create_input, list)
    assert any(item.get("content") == "My question" for item in client.create_input)


@pytest.mark.asyncio
async def test_stream_response_embeds_question_for_retrieval() -> None:
    """Test that streaming embeds the question and runs chunk vector search."""
    client, _messages, service = _build_service()
    client.events = [
        LLMStreamEvent(
            type="final",
            response=LLMResponse(text="Hi", raw=_raw_metadata()),
        ),
    ]

    embeddings = cast(FakeEmbeddingClient, service.context.embeddings)
    chunks = cast(FakeDocumentChunkService, service.context.chunks)

    async for _ in service.stream_response(
        user_id=TEST_USER_ID,
        message=_user_message(content="Stream question?"),
    ):
        pass

    assert embeddings.embedded_texts == ["Stream question?"]
    assert chunks.search_query_embedding == embeddings.embedding
