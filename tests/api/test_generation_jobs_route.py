"""Tests for generation jobs API router."""

from collections.abc import Generator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ai_notes_api.api.v1.dependencies import get_current_user, get_job_service
from ai_notes_api.api.v1.generation_job import router
from ai_notes_api.db.models import GenerationJobStatus, User
from ai_notes_api.exceptions import (
    ChatSessionNotFoundError,
    GenerationInProgressError,
    GenerationNotFoundError,
)
from ai_notes_api.exceptions.base import register_exception_handlers
from ai_notes_api.schemas import GenerationJobResponseSchema

TEST_USER_ID = UUID("11111111-1111-1111-1111-111111111111")
TEST_SESSION_ID = UUID("22222222-2222-2222-2222-222222222222")
TEST_JOB_ID = UUID("33333333-3333-3333-3333-333333333333")


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


def create_generation_job_response(
    *,
    job_id: UUID = TEST_JOB_ID,
    status: GenerationJobStatus = GenerationJobStatus.QUEUED,
    input_message: str = "Test input message",
) -> GenerationJobResponseSchema:
    """Create generation job response schema for router tests.

    Args:
        job_id (UUID): Unique generation job identifier.
        status (GenerationJobStatus): Current generation job status.
        input_message (str): User input message used for generation.

    Returns:
        GenerationJobResponseSchema: Generation job response schema instance.
    """
    return GenerationJobResponseSchema(
        id=job_id,
        session_id=TEST_SESSION_ID,
        status=status,
        input_message=input_message,
        created_at=datetime.now(UTC),
    )


@pytest.fixture
def current_user() -> User:
    """Create mocked current user.

    Returns:
        User: Current authenticated user.
    """
    return create_test_user()


@pytest.fixture
def job_service_mock() -> AsyncMock:
    """Create mocked generation job service.

    Returns:
        AsyncMock: Mocked generation job service dependency.
    """
    return AsyncMock()


@pytest.fixture
def run_generation_job_mock() -> Generator[MagicMock]:
    """Patch the Celery task used to enqueue generation jobs.

    Yields:
        MagicMock: Mocked ``run_generation_job`` Celery task.
    """
    with patch("ai_notes_api.api.v1.generation_job.run_generation_job") as task_mock:
        yield task_mock


@pytest.fixture
def client(
    job_service_mock: AsyncMock,
    current_user: User,
) -> TestClient:
    """Create a test client with mocked dependencies.

    Args:
        job_service_mock (AsyncMock): Mocked generation job service dependency.
        current_user (User): Mocked authenticated user.

    Returns:
        TestClient: FastAPI test client.
    """
    app = FastAPI()
    app.include_router(router)
    register_exception_handlers(app)

    app.dependency_overrides[get_job_service] = lambda: job_service_mock
    app.dependency_overrides[get_current_user] = lambda: current_user

    return TestClient(app)


def test_create_completion_job_success(
    client: TestClient,
    job_service_mock: AsyncMock,
    run_generation_job_mock: MagicMock,
) -> None:
    """Test successful generation job creation."""
    job_service_mock.create_job.return_value = create_generation_job_response(
        input_message="Hello",
    )

    response = client.post(
        "/chat/completions/jobs",
        json={
            "session_id": str(TEST_SESSION_ID),
            "message": "Hello",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["id"] == str(TEST_JOB_ID)
    assert data["session_id"] == str(TEST_SESSION_ID)
    assert data["status"] == GenerationJobStatus.QUEUED.value
    assert data["input_message"] == "Hello"

    job_service_mock.create_job.assert_awaited_once()

    user_id, create_data = job_service_mock.create_job.await_args.args

    assert user_id == TEST_USER_ID
    assert create_data.session_id == TEST_SESSION_ID
    assert create_data.message == "Hello"

    run_generation_job_mock.delay.assert_called_once_with(str(TEST_JOB_ID))


def test_create_completion_job_enqueues_task(
    client: TestClient,
    job_service_mock: AsyncMock,
    run_generation_job_mock: MagicMock,
) -> None:
    """Test that creating a job enqueues it for background execution."""
    job_service_mock.create_job.return_value = create_generation_job_response()

    response = client.post(
        "/chat/completions/jobs",
        json={
            "session_id": str(TEST_SESSION_ID),
            "message": "Hello",
        },
    )

    assert response.status_code == 201

    run_generation_job_mock.delay.assert_called_once_with(str(TEST_JOB_ID))


def test_create_completion_job_session_not_found(
    client: TestClient,
    job_service_mock: AsyncMock,
    run_generation_job_mock: MagicMock,
) -> None:
    """Test that creating a job for a missing session returns a 404 error."""
    job_service_mock.create_job.side_effect = ChatSessionNotFoundError()

    response = client.post(
        "/chat/completions/jobs",
        json={
            "session_id": str(TEST_SESSION_ID),
            "message": "Hello",
        },
    )

    assert response.status_code == 404

    run_generation_job_mock.delay.assert_not_called()


def test_create_completion_job_generation_in_progress(
    client: TestClient,
    job_service_mock: AsyncMock,
    run_generation_job_mock: MagicMock,
) -> None:
    """Test that creating a job during an active generation returns a 409 error."""
    job_service_mock.create_job.side_effect = GenerationInProgressError()

    response = client.post(
        "/chat/completions/jobs",
        json={
            "session_id": str(TEST_SESSION_ID),
            "message": "Hello",
        },
    )

    assert response.status_code == 409

    run_generation_job_mock.delay.assert_not_called()


def test_create_completion_job_validation_error(
    client: TestClient,
) -> None:
    """Test that an empty message returns a validation error."""
    response = client.post(
        "/chat/completions/jobs",
        json={
            "session_id": str(TEST_SESSION_ID),
            "message": "",
        },
    )

    assert response.status_code == 422


def test_create_completion_job_missing_session_id(
    client: TestClient,
) -> None:
    """Test that a missing session id returns a validation error."""
    response = client.post(
        "/chat/completions/jobs",
        json={
            "message": "Hello",
        },
    )

    assert response.status_code == 422


def test_get_completion_job_success(
    client: TestClient,
    job_service_mock: AsyncMock,
) -> None:
    """Test successful generation job retrieval by identifier."""
    job_service_mock.get_by_id_for_user.return_value = create_generation_job_response(
        status=GenerationJobStatus.COMPLETED,
        input_message="Hello",
    )

    response = client.get(f"/chat/completions/jobs/{TEST_JOB_ID}")

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == str(TEST_JOB_ID)
    assert data["status"] == GenerationJobStatus.COMPLETED.value
    assert data["input_message"] == "Hello"

    job_service_mock.get_by_id_for_user.assert_awaited_once_with(
        TEST_USER_ID, TEST_JOB_ID
    )


def test_get_completion_job_not_found(
    client: TestClient,
    job_service_mock: AsyncMock,
) -> None:
    """Test that retrieving a missing generation job returns a 404 error."""
    job_service_mock.get_by_id_for_user.side_effect = GenerationNotFoundError()

    response = client.get(f"/chat/completions/jobs/{TEST_JOB_ID}")

    assert response.status_code == 404


def test_get_completion_job_invalid_id(
    client: TestClient,
) -> None:
    """Test that an invalid job identifier returns a validation error."""
    response = client.get("/chat/completions/jobs/not-a-uuid")

    assert response.status_code == 422
