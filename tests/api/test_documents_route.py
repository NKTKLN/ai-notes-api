"""Tests for documents API router."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ai_notes_api.api.v1 import documents as documents_module
from ai_notes_api.api.v1.dependencies import (
    get_current_user,
    get_document_processinng_job_service,
    get_document_service,
)
from ai_notes_api.api.v1.documents import router
from ai_notes_api.db.models import Document, DocumentProcessingJob, DocumentStatus, User

TEST_USER_ID = UUID("11111111-1111-1111-1111-111111111111")
TEST_SESSION_ID = UUID("22222222-2222-2222-2222-222222222222")
TEST_DOCUMENT_ID = UUID("55555555-5555-5555-5555-555555555555")
TEST_DOCUMENT_ID_2 = UUID("66666666-6666-6666-6666-666666666666")

TEST_DOWNLOAD_URL = "https://storage.example.com/download"
TEST_PROCESSING_JOB_ID = UUID("77777777-7777-7777-7777-777777777777")


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


def create_document(  # noqa: PLR0913
    *,
    document_id: UUID = TEST_DOCUMENT_ID,
    session_id: UUID = TEST_SESSION_ID,
    filename: str = "document.txt",
    content_type: str = "text/plain",
    file_size: int = 12,
    status: DocumentStatus = DocumentStatus.READY,
) -> Document:
    """Create a document model instance for router tests.

    Args:
        document_id (UUID): Unique document identifier.
        session_id (UUID): Unique chat session identifier.
        filename (str): Original document file name.
        content_type (str): MIME type of the document.
        file_size (int): Document size in bytes.
        status (DocumentStatus): Current document processing status.

    Returns:
        Document: Document model instance.
    """
    now = datetime.now(UTC)

    return Document(
        id=document_id,
        user_id=TEST_USER_ID,
        session_id=session_id,
        filename=filename,
        content_type=content_type,
        file_size=file_size,
        checksum_sha256="checksum",
        storage_bucket="test-bucket",
        storage_object_name="users/test/document.txt",
        status=status,
        error_message=None,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def current_user() -> User:
    """Create mocked current user.

    Returns:
        User: Current authenticated user.
    """
    return create_test_user()


@pytest.fixture
def document_service_mock() -> AsyncMock:
    """Create mocked document service.

    Returns:
        AsyncMock: Mocked document service dependency.
    """
    return AsyncMock()


@pytest.fixture
def job_service_mock() -> AsyncMock:
    """Create mocked document processing job service.

    Returns:
        AsyncMock: Mocked document processing job service dependency.
    """
    return AsyncMock()


@pytest.fixture
def client(
    document_service_mock: AsyncMock,
    job_service_mock: AsyncMock,
    current_user: User,
) -> TestClient:
    """Create a test client with mocked dependencies.

    Args:
        document_service_mock (AsyncMock): Mocked document service dependency.
        job_service_mock (AsyncMock): Mocked processing job service dependency.
        current_user (User): Mocked authenticated user.

    Returns:
        TestClient: FastAPI test client.
    """
    app = FastAPI()
    app.include_router(router)

    app.dependency_overrides[get_document_service] = lambda: document_service_mock
    app.dependency_overrides[get_document_processinng_job_service] = lambda: (
        job_service_mock
    )
    app.dependency_overrides[get_current_user] = lambda: current_user

    return TestClient(app)


def test_upload_document_success(
    client: TestClient,
    document_service_mock: AsyncMock,
    job_service_mock: AsyncMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test successful document upload, job creation, and processing enqueue."""
    document_service_mock.create_document.return_value = create_document(
        document_id=TEST_DOCUMENT_ID,
        filename="notes.txt",
    )
    job_service_mock.create_job.return_value = DocumentProcessingJob(
        id=TEST_PROCESSING_JOB_ID,
        document_id=TEST_DOCUMENT_ID,
    )

    delay_mock = MagicMock()
    monkeypatch.setattr(
        documents_module.run_document_processing_job, "delay", delay_mock
    )

    response = client.post(
        f"/chat/sessions/{TEST_SESSION_ID}/documents",
        files={"file": ("notes.txt", b"hello world", "text/plain")},
    )

    assert response.status_code == 201

    data = response.json()

    assert data["id"] == str(TEST_DOCUMENT_ID)
    assert data["filename"] == "notes.txt"
    assert data["chat_session_id"] == str(TEST_SESSION_ID)

    document_service_mock.create_document.assert_awaited_once()

    create_args = document_service_mock.create_document.await_args.args

    assert create_args[0] == TEST_USER_ID
    assert create_args[1] == TEST_SESSION_ID

    job_service_mock.create_job.assert_awaited_once_with(TEST_DOCUMENT_ID)
    delay_mock.assert_called_once_with(str(TEST_PROCESSING_JOB_ID))


def test_list_documents_success(
    client: TestClient,
    document_service_mock: AsyncMock,
) -> None:
    """Test successful documents list retrieval."""
    document_service_mock.list_documents.return_value = [
        create_document(document_id=TEST_DOCUMENT_ID, filename="first.txt"),
        create_document(document_id=TEST_DOCUMENT_ID_2, filename="second.txt"),
    ]

    response = client.get(f"/chat/sessions/{TEST_SESSION_ID}/documents")

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert data["items"][0]["id"] == str(TEST_DOCUMENT_ID)
    assert data["items"][0]["filename"] == "first.txt"
    assert data["items"][0]["chat_session_id"] == str(TEST_SESSION_ID)
    assert data["items"][1]["id"] == str(TEST_DOCUMENT_ID_2)

    document_service_mock.list_documents.assert_awaited_once_with(
        TEST_USER_ID, TEST_SESSION_ID
    )


def test_list_documents_empty_success(
    client: TestClient,
    document_service_mock: AsyncMock,
) -> None:
    """Test successful empty documents list retrieval."""
    document_service_mock.list_documents.return_value = []

    response = client.get(f"/chat/sessions/{TEST_SESSION_ID}/documents")

    assert response.status_code == 200

    data = response.json()

    assert data["items"] == []
    assert data["total"] == 0

    document_service_mock.list_documents.assert_awaited_once_with(
        TEST_USER_ID, TEST_SESSION_ID
    )


def test_get_document_success(
    client: TestClient,
    document_service_mock: AsyncMock,
) -> None:
    """Test successful document retrieval by identifier."""
    document_service_mock.get_document.return_value = create_document(
        document_id=TEST_DOCUMENT_ID,
        filename="notes.txt",
        content_type="text/plain",
        status=DocumentStatus.READY,
    )

    response = client.get(
        f"/chat/sessions/{TEST_SESSION_ID}/documents/{TEST_DOCUMENT_ID}"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == str(TEST_DOCUMENT_ID)
    assert data["chat_session_id"] == str(TEST_SESSION_ID)
    assert data["filename"] == "notes.txt"
    assert data["content_type"] == "text/plain"
    assert data["status"] == DocumentStatus.READY.value

    document_service_mock.get_document.assert_awaited_once_with(
        TEST_USER_ID, TEST_SESSION_ID, TEST_DOCUMENT_ID
    )


def test_download_document_success(
    client: TestClient,
    document_service_mock: AsyncMock,
) -> None:
    """Test successful document download URL retrieval."""
    document_service_mock.get_document_download_url.return_value = TEST_DOWNLOAD_URL

    response = client.get(
        f"/chat/sessions/{TEST_SESSION_ID}/documents/{TEST_DOCUMENT_ID}/download"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["url"] == TEST_DOWNLOAD_URL
    assert data["expires_in_seconds"] == 60

    document_service_mock.get_document_download_url.assert_awaited_once()

    kwargs = document_service_mock.get_document_download_url.await_args.kwargs

    assert kwargs["user_id"] == TEST_USER_ID
    assert kwargs["session_id"] == TEST_SESSION_ID
    assert kwargs["document_id"] == TEST_DOCUMENT_ID
    assert kwargs["expires_in_seconds"] == 60


def test_delete_document_success(
    client: TestClient,
    document_service_mock: AsyncMock,
) -> None:
    """Test successful document deletion."""
    document_service_mock.delete_document.return_value = None

    response = client.delete(
        f"/chat/sessions/{TEST_SESSION_ID}/documents/{TEST_DOCUMENT_ID}"
    )

    assert response.status_code == 200
    assert response.json() == {"status": "deleted"}

    document_service_mock.delete_document.assert_awaited_once_with(
        TEST_USER_ID, TEST_SESSION_ID, TEST_DOCUMENT_ID
    )
