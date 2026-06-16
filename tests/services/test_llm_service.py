"""Tests for LLM service."""

from collections.abc import AsyncGenerator
from types import SimpleNamespace
from typing import Any, cast
from uuid import UUID

import pytest

from ai_notes_api.core import settings
from ai_notes_api.db.models import Message, MessageRole
from ai_notes_api.exceptions import ChatSessionNotFoundError
from ai_notes_api.llm import LLMClient
from ai_notes_api.llm.models import LLMResponse, LLMStreamEvent
from ai_notes_api.schemas import (
    AssistantMessageCreateSchema,
    UserMessageCreateSchema,
)
from ai_notes_api.services.chat_session import ChatSessionService
from ai_notes_api.services.llm_service import LLMService
from ai_notes_api.services.message import MessageService
from ai_notes_api.services.note import NoteService

TEST_USER_ID = UUID("11111111-1111-1111-1111-111111111111")
TEST_SESSION_ID = UUID("22222222-2222-2222-2222-222222222222")
TEST_MESSAGE_ID = UUID("33333333-3333-3333-3333-333333333333")


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
        self.create_input: Any = None
        self.stream_input: Any = None
        self.create_tools: Any = None
        self.stream_tools: Any = None

    async def create_response(
        self,
        input_data: str | list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        """Return the configured response."""
        self.create_input = input_data
        self.create_tools = tools
        assert self.response is not None
        return self.response

    async def stream_response_events(
        self,
        input_data: str | list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncGenerator[LLMStreamEvent]:
        """Yield the configured stream events."""
        self.stream_input = input_data
        self.stream_tools = tools
        for event in self.events:
            yield event


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


def _build_service() -> tuple[FakeLLMClient, FakeMessageService, LLMService]:
    """Build an LLM service wired with fakes."""
    client = FakeLLMClient()
    messages = FakeMessageService()
    sessions = FakeChatSessionService()
    notes = FakeNoteService()

    service = LLMService(
        client=cast(LLMClient, client),
        note_service=cast(NoteService, notes),
        session_service=cast(ChatSessionService, sessions),
        message_service=cast(MessageService, messages),
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
    assert client.create_input[0]["role"] == MessageRole.SYSTEM
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
