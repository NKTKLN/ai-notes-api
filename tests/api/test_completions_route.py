"""Tests for chat completions API router."""

import json
from collections.abc import AsyncGenerator
from typing import Protocol
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ai_notes_api.api.v1.completions import llm_event_to_sse, router
from ai_notes_api.api.v1.dependencies import get_current_user, get_llm_service
from ai_notes_api.db.models import User
from ai_notes_api.llm.models import LLMResponse, LLMStreamEvent

TEST_USER_ID = UUID("11111111-1111-1111-1111-111111111111")
TEST_SESSION_ID = UUID("22222222-2222-2222-2222-222222222222")


def create_test_user() -> User:
    """Create current user for router tests.

    Returns:
        User: Test user model instance.
    """
    return User(
        id=TEST_USER_ID,
        email="test-user@example.com",
        username="test_user",
        hashed_password="test-password-hash",  # noqa: S106
        is_active=True,
        is_superuser=False,
    )


class MessageLike(Protocol):
    """Message shape passed to the LLM service."""

    session_id: UUID
    content: str


class FakeLLMService:
    """Fake LLM service yielding preconfigured stream events.

    Attributes:
        events (list[LLMStreamEvent]): Events yielded while streaming.
        raise_exc (Exception | None): Optional error raised during streaming.
        called_with (tuple | None): Recorded ``stream_response`` call arguments.
    """

    def __init__(self) -> None:
        """Initialize the fake LLM service."""
        self.events: list[LLMStreamEvent] = []
        self.raise_exc: Exception | None = None
        self.called_with: tuple[UUID, MessageLike] | None = None

    def stream_response(
        self,
        *,
        user_id: UUID,
        message: MessageLike,
    ) -> AsyncGenerator[LLMStreamEvent]:
        """Record the call and return an async generator of events.

        Args:
            user_id (UUID): Current authenticated user identifier.
            message (object): Validated user message data.

        Returns:
            AsyncGenerator[LLMStreamEvent]: Generator yielding stream events.
        """
        self.called_with = (user_id, message)
        events = self.events
        raise_exc = self.raise_exc

        async def generator() -> AsyncGenerator[LLMStreamEvent]:
            for event in events:
                yield event

            if raise_exc is not None:
                raise raise_exc

        return generator()


@pytest.fixture
def current_user() -> User:
    """Create mocked current user.

    Returns:
        User: Current authenticated user.
    """
    return create_test_user()


@pytest.fixture
def llm_service_mock() -> FakeLLMService:
    """Create fake LLM service.

    Returns:
        FakeLLMService: Fake LLM service dependency.
    """
    return FakeLLMService()


@pytest.fixture
def client(
    llm_service_mock: FakeLLMService,
    current_user: User,
) -> TestClient:
    """Create a test client with mocked dependencies.

    Args:
        llm_service_mock (FakeLLMService): Fake LLM service dependency.
        current_user (User): Mocked authenticated user.

    Returns:
        TestClient: FastAPI test client.
    """
    app = FastAPI()
    app.include_router(router)

    app.dependency_overrides[get_llm_service] = lambda: llm_service_mock
    app.dependency_overrides[get_current_user] = lambda: current_user

    return TestClient(app)


def parse_sse_events(body: str) -> list[dict[str, str]]:
    """Parse a server-sent events payload into a list of events.

    Args:
        body (str): Raw SSE response body.

    Returns:
        list[dict[str, str]]: Parsed events with ``event`` and ``data`` keys.
    """
    events: list[dict[str, str]] = []

    for block in body.split("\r\n\r\n"):
        event: dict[str, str] = {}

        for line in block.splitlines():
            if line.startswith("event:"):
                event["event"] = line[len("event:") :].strip()
            elif line.startswith("data:"):
                event["data"] = line[len("data:") :].strip()

        if "event" in event or "data" in event:
            events.append(event)

    return events


def test_llm_event_to_sse_delta() -> None:
    """Test that a delta event is converted to an SSE payload."""
    event = LLMStreamEvent(type="delta", id="evt-1", delta="Hello")

    payload = llm_event_to_sse(event)

    assert payload["event"] == "delta"

    data = json.loads(payload["data"])

    assert data["type"] == "delta"
    assert data["id"] == "evt-1"
    assert data["delta"] == "Hello"
    assert data["response"] is None


def test_llm_event_to_sse_final() -> None:
    """Test that a final event with a response is converted to an SSE payload."""
    event = LLMStreamEvent(
        type="final",
        response=LLMResponse(text="Hello there"),
    )

    payload = llm_event_to_sse(event)

    assert payload["event"] == "final"

    data = json.loads(payload["data"])

    assert data["type"] == "final"
    assert data["response"]["text"] == "Hello there"


def test_stream_chat_completion_success(
    client: TestClient,
    llm_service_mock: FakeLLMService,
) -> None:
    """Test successful chat completion streaming."""
    llm_service_mock.events = [
        LLMStreamEvent(type="delta", delta="Hel"),
        LLMStreamEvent(type="delta", delta="lo"),
        LLMStreamEvent(
            type="final",
            response=LLMResponse(text="Hello"),
        ),
    ]

    response = client.post(
        "/chat/completions/stream",
        json={"session_id": str(TEST_SESSION_ID), "content": "Hi"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    events = parse_sse_events(response.text)

    assert [event["event"] for event in events] == ["delta", "delta", "final"]
    assert json.loads(events[0]["data"])["delta"] == "Hel"
    assert json.loads(events[1]["data"])["delta"] == "lo"
    assert json.loads(events[2]["data"])["response"]["text"] == "Hello"


def test_stream_chat_completion_passes_user_and_message(
    client: TestClient,
    llm_service_mock: FakeLLMService,
) -> None:
    """Test that streaming passes the current user id and message to the service."""
    llm_service_mock.events = [LLMStreamEvent(type="delta", delta="Hi")]

    response = client.post(
        "/chat/completions/stream",
        json={"session_id": str(TEST_SESSION_ID), "content": "Hi there"},
    )

    assert response.status_code == 200
    assert llm_service_mock.called_with is not None

    user_id, message = llm_service_mock.called_with

    assert user_id == TEST_USER_ID
    assert message.session_id == TEST_SESSION_ID
    assert message.content == "Hi there"


def test_stream_chat_completion_emits_error_event(
    client: TestClient,
    llm_service_mock: FakeLLMService,
) -> None:
    """Test that a streaming failure emits an error event."""
    llm_service_mock.events = [LLMStreamEvent(type="delta", delta="Hi")]
    llm_service_mock.raise_exc = RuntimeError("boom")

    response = client.post(
        "/chat/completions/stream",
        json={"session_id": str(TEST_SESSION_ID), "content": "Hi"},
    )

    assert response.status_code == 200

    events = parse_sse_events(response.text)

    assert events[-1]["event"] == "error"
    assert json.loads(events[-1]["data"])["message"] == "boom"


def test_stream_chat_completion_validation_error(
    client: TestClient,
) -> None:
    """Test that an invalid request body returns a validation error."""
    response = client.post(
        "/chat/completions/stream",
        json={"session_id": str(TEST_SESSION_ID), "content": ""},
    )

    assert response.status_code == 422


def test_stream_chat_completion_missing_session_id(
    client: TestClient,
) -> None:
    """Test that a missing session id returns a validation error."""
    response = client.post(
        "/chat/completions/stream",
        json={"content": "Hi"},
    )

    assert response.status_code == 422
