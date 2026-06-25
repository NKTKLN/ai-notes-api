"""Tests for document service."""

import hashlib
from datetime import UTC, datetime
from typing import cast
from uuid import UUID, uuid4

import pytest
from fastapi import UploadFile

from ai_notes_api.db.models import Document, DocumentStatus
from ai_notes_api.exceptions import ChatSessionNotFoundError, DocumentNotFoundError
from ai_notes_api.repositories.document import DocumentRepository
from ai_notes_api.services import ChatSessionService
from ai_notes_api.services.document import DocumentService
from ai_notes_api.storage import DocumentStorage

TEST_USER_ID = UUID("11111111-1111-1111-1111-111111111111")
TEST_USER_ID_2 = UUID("44444444-4444-4444-4444-444444444444")
TEST_SESSION_ID = UUID("22222222-2222-2222-2222-222222222222")
TEST_SESSION_ID_2 = UUID("33333333-3333-3333-3333-333333333333")
TEST_DOCUMENT_ID = UUID("55555555-5555-5555-5555-555555555555")

TEST_OBJECT_NAME = "users/test/document.txt"
TEST_DOWNLOAD_URL = "https://storage.example.com/download"


class FakeUploadFile:
    """Fake uploaded file used for testing document service behavior."""

    def __init__(
        self,
        *,
        data: bytes = b"file content",
        filename: str | None = "document.txt",
        content_type: str | None = "text/plain",
    ) -> None:
        """Initialize the fake uploaded file."""
        self._data = data
        self.filename = filename
        self.content_type = content_type

    async def read(self) -> bytes:
        """Return the in-memory file content."""
        return self._data


class FakeChatSessionService:
    """Fake chat session service used for testing document service behavior."""

    def __init__(self) -> None:
        """Initialize the fake chat session service."""
        # Maps session id to the user that owns it.
        self.owners: dict[UUID, UUID] = {}

    async def ensure_session_owner(self, user_id: UUID, session_id: UUID) -> None:
        """Ensure a chat session belongs to a user."""
        if self.owners.get(session_id) != user_id:
            raise ChatSessionNotFoundError()


class FakeDocumentRepository:
    """Fake document repository used for testing document service behavior."""

    def __init__(self) -> None:
        """Initialize the fake document repository."""
        self.documents: dict[UUID, Document] = {}
        self.created_document: Document | None = None

    async def create(self, document: Document) -> Document:
        """Create a document in the fake repository."""
        self.created_document = document
        self.documents[document.id] = document
        return document

    async def get_by_id_for_user(
        self,
        user_id: UUID,
        document_id: UUID,
    ) -> Document | None:
        """Return a non-deleted document scoped to the owning user."""
        document = self.documents.get(document_id)

        if (
            document is not None
            and document.user_id == user_id
            and document.deleted_at is None
        ):
            return document

        return None

    async def get_list_for_session(
        self,
        user_id: UUID,
        session_id: UUID,
    ) -> list[Document]:
        """Return a user's non-deleted documents for a chat session."""
        return [
            document
            for document in self.documents.values()
            if document.user_id == user_id
            and document.session_id == session_id
            and document.deleted_at is None
        ]

    async def soft_delete(self, document: Document) -> None:
        """Soft-delete a document in the fake repository."""
        document.deleted_at = datetime.now(UTC)


class FakeDocumentStorage:
    """Fake document storage used for testing document service behavior."""

    def __init__(self) -> None:
        """Initialize the fake document storage."""
        self.bucket = "test-bucket"
        self.uploaded: list[dict[str, object]] = []
        self.presigned_calls: list[dict[str, object]] = []
        self.deleted: list[str] = []

    async def upload_file(
        self,
        user_id: UUID,
        document_id: UUID,
        filename: str,
        data: bytes,
        content_type: str,
    ) -> str:
        """Record an upload and return a fixed object name."""
        self.uploaded.append(
            {
                "user_id": user_id,
                "document_id": document_id,
                "filename": filename,
                "data": data,
                "content_type": content_type,
            }
        )
        return TEST_OBJECT_NAME

    async def get_presigned_download_url(
        self,
        object_name: str,
        expires_in_seconds: int | None = None,
    ) -> str:
        """Record a presigned URL request and return a fixed URL."""
        self.presigned_calls.append(
            {"object_name": object_name, "expires_in_seconds": expires_in_seconds}
        )
        return TEST_DOWNLOAD_URL

    async def delete_file(self, object_name: str) -> None:
        """Record a delete request."""
        self.deleted.append(object_name)


def build_service(
    documents: FakeDocumentRepository,
    sessions: FakeChatSessionService,
    storage: FakeDocumentStorage,
) -> DocumentService:
    """Build a DocumentService wired with fake dependencies."""
    return DocumentService(
        document_repository=cast(DocumentRepository, documents),
        session_service=cast(ChatSessionService, sessions),
        storage=cast(DocumentStorage, storage),
    )


def store_document(
    repository: FakeDocumentRepository,
    *,
    document_id: UUID = TEST_DOCUMENT_ID,
    user_id: UUID = TEST_USER_ID,
    session_id: UUID = TEST_SESSION_ID,
    object_name: str = TEST_OBJECT_NAME,
) -> Document:
    """Persist a document into the fake repository."""
    document = Document(
        id=document_id,
        user_id=user_id,
        session_id=session_id,
        filename="document.txt",
        content_type="text/plain",
        file_size=12,
        checksum_sha256="checksum",
        storage_bucket="test-bucket",
        storage_object_name=object_name,
        status=DocumentStatus.READY,
    )

    repository.documents[document_id] = document

    return document


@pytest.mark.asyncio
async def test_create_document_success() -> None:
    """Test successful document creation."""
    documents = FakeDocumentRepository()
    sessions = FakeChatSessionService()
    storage = FakeDocumentStorage()
    sessions.owners[TEST_SESSION_ID] = TEST_USER_ID
    service = build_service(documents, sessions, storage)

    data = b"hello world"
    file = FakeUploadFile(data=data, filename="notes.txt", content_type="text/plain")

    document = await service.create_document(
        TEST_USER_ID, TEST_SESSION_ID, cast(UploadFile, file)
    )

    assert document.user_id == TEST_USER_ID
    assert document.session_id == TEST_SESSION_ID
    assert document.filename == "notes.txt"
    assert document.content_type == "text/plain"
    assert document.file_size == len(data)
    assert document.checksum_sha256 == hashlib.sha256(data).hexdigest()
    assert document.storage_bucket == storage.bucket
    assert document.storage_object_name == TEST_OBJECT_NAME
    assert document.status == DocumentStatus.UPLOADED
    assert documents.created_document is document


@pytest.mark.asyncio
async def test_create_document_uploads_file() -> None:
    """Test that document creation uploads the file to storage."""
    documents = FakeDocumentRepository()
    sessions = FakeChatSessionService()
    storage = FakeDocumentStorage()
    sessions.owners[TEST_SESSION_ID] = TEST_USER_ID
    service = build_service(documents, sessions, storage)

    data = b"hello world"
    file = FakeUploadFile(data=data, filename="notes.txt", content_type="text/plain")

    document = await service.create_document(
        TEST_USER_ID, TEST_SESSION_ID, cast(UploadFile, file)
    )

    assert len(storage.uploaded) == 1

    upload = storage.uploaded[0]

    assert upload["user_id"] == TEST_USER_ID
    assert upload["document_id"] == document.id
    assert upload["filename"] == "notes.txt"
    assert upload["data"] == data
    assert upload["content_type"] == "text/plain"


@pytest.mark.asyncio
async def test_create_document_uses_default_filename_and_content_type() -> None:
    """Test that document creation falls back to default filename and type."""
    documents = FakeDocumentRepository()
    sessions = FakeChatSessionService()
    storage = FakeDocumentStorage()
    sessions.owners[TEST_SESSION_ID] = TEST_USER_ID
    service = build_service(documents, sessions, storage)

    file = FakeUploadFile(filename=None, content_type=None)

    document = await service.create_document(
        TEST_USER_ID, TEST_SESSION_ID, cast(UploadFile, file)
    )

    assert document.filename == DocumentService.DEFAULT_FILENAME
    assert document.content_type == DocumentService.DEFAULT_CONTENT_TYPE


@pytest.mark.asyncio
async def test_create_document_session_not_owned() -> None:
    """Test that creating a document for a non-owned session raises an error."""
    documents = FakeDocumentRepository()
    sessions = FakeChatSessionService()
    storage = FakeDocumentStorage()
    sessions.owners[TEST_SESSION_ID] = TEST_USER_ID
    service = build_service(documents, sessions, storage)

    with pytest.raises(ChatSessionNotFoundError):
        await service.create_document(
            TEST_USER_ID_2, TEST_SESSION_ID, cast(UploadFile, FakeUploadFile())
        )

    assert documents.created_document is None
    assert storage.uploaded == []


@pytest.mark.asyncio
async def test_list_documents_success() -> None:
    """Test successful documents list retrieval scoped to user and session."""
    documents = FakeDocumentRepository()
    sessions = FakeChatSessionService()
    storage = FakeDocumentStorage()
    store_document(documents, document_id=uuid4())
    store_document(documents, document_id=uuid4())
    store_document(documents, document_id=uuid4(), session_id=TEST_SESSION_ID_2)
    store_document(documents, document_id=uuid4(), user_id=TEST_USER_ID_2)
    service = build_service(documents, sessions, storage)

    result = await service.list_documents(TEST_USER_ID, TEST_SESSION_ID)

    assert len(result) == 2
    assert all(document.session_id == TEST_SESSION_ID for document in result)
    assert all(document.user_id == TEST_USER_ID for document in result)


@pytest.mark.asyncio
async def test_list_documents_empty() -> None:
    """Test that listing documents returns an empty list when none exist."""
    documents = FakeDocumentRepository()
    sessions = FakeChatSessionService()
    storage = FakeDocumentStorage()
    service = build_service(documents, sessions, storage)

    result = await service.list_documents(TEST_USER_ID, TEST_SESSION_ID)

    assert result == []


@pytest.mark.asyncio
async def test_get_document_success() -> None:
    """Test successful document retrieval by identifier."""
    documents = FakeDocumentRepository()
    sessions = FakeChatSessionService()
    storage = FakeDocumentStorage()
    store_document(documents)
    service = build_service(documents, sessions, storage)

    document = await service.get_document(
        TEST_USER_ID, TEST_SESSION_ID, TEST_DOCUMENT_ID
    )

    assert document.id == TEST_DOCUMENT_ID
    assert document.session_id == TEST_SESSION_ID


@pytest.mark.asyncio
async def test_get_document_not_found_by_id() -> None:
    """Test that retrieval raises an error when the document is not found."""
    documents = FakeDocumentRepository()
    sessions = FakeChatSessionService()
    storage = FakeDocumentStorage()
    service = build_service(documents, sessions, storage)

    with pytest.raises(DocumentNotFoundError):
        await service.get_document(TEST_USER_ID, TEST_SESSION_ID, uuid4())


@pytest.mark.asyncio
async def test_get_document_not_found_for_another_user() -> None:
    """Test that another user's document cannot be retrieved."""
    documents = FakeDocumentRepository()
    sessions = FakeChatSessionService()
    storage = FakeDocumentStorage()
    store_document(documents)
    service = build_service(documents, sessions, storage)

    with pytest.raises(DocumentNotFoundError):
        await service.get_document(TEST_USER_ID_2, TEST_SESSION_ID, TEST_DOCUMENT_ID)


@pytest.mark.asyncio
async def test_get_document_not_found_for_another_session() -> None:
    """Test that a document from another session cannot be retrieved."""
    documents = FakeDocumentRepository()
    sessions = FakeChatSessionService()
    storage = FakeDocumentStorage()
    store_document(documents)
    service = build_service(documents, sessions, storage)

    with pytest.raises(DocumentNotFoundError):
        await service.get_document(TEST_USER_ID, TEST_SESSION_ID_2, TEST_DOCUMENT_ID)


@pytest.mark.asyncio
async def test_get_document_download_url_success() -> None:
    """Test successful presigned download URL generation."""
    documents = FakeDocumentRepository()
    sessions = FakeChatSessionService()
    storage = FakeDocumentStorage()
    store_document(documents)
    service = build_service(documents, sessions, storage)

    url = await service.get_document_download_url(
        user_id=TEST_USER_ID,
        session_id=TEST_SESSION_ID,
        document_id=TEST_DOCUMENT_ID,
        expires_in_seconds=60,
    )

    assert url == TEST_DOWNLOAD_URL
    assert storage.presigned_calls == [
        {"object_name": TEST_OBJECT_NAME, "expires_in_seconds": 60}
    ]


@pytest.mark.asyncio
async def test_get_document_download_url_not_found() -> None:
    """Test that URL generation raises an error when the document is not found."""
    documents = FakeDocumentRepository()
    sessions = FakeChatSessionService()
    storage = FakeDocumentStorage()
    service = build_service(documents, sessions, storage)

    with pytest.raises(DocumentNotFoundError):
        await service.get_document_download_url(
            user_id=TEST_USER_ID,
            session_id=TEST_SESSION_ID,
            document_id=uuid4(),
        )

    assert storage.presigned_calls == []


@pytest.mark.asyncio
async def test_delete_document_success() -> None:
    """Test successful document deletion."""
    documents = FakeDocumentRepository()
    sessions = FakeChatSessionService()
    storage = FakeDocumentStorage()
    store_document(documents)
    service = build_service(documents, sessions, storage)

    await service.delete_document(TEST_USER_ID, TEST_SESSION_ID, TEST_DOCUMENT_ID)

    assert documents.documents[TEST_DOCUMENT_ID].deleted_at is not None
    assert storage.deleted == [TEST_OBJECT_NAME]


@pytest.mark.asyncio
async def test_delete_document_not_found() -> None:
    """Test that deletion raises an error when the document is not found."""
    documents = FakeDocumentRepository()
    sessions = FakeChatSessionService()
    storage = FakeDocumentStorage()
    service = build_service(documents, sessions, storage)

    with pytest.raises(DocumentNotFoundError):
        await service.delete_document(TEST_USER_ID, TEST_SESSION_ID, uuid4())

    assert storage.deleted == []


@pytest.mark.asyncio
async def test_delete_document_not_found_for_another_user() -> None:
    """Test that another user's document cannot be deleted."""
    documents = FakeDocumentRepository()
    sessions = FakeChatSessionService()
    storage = FakeDocumentStorage()
    store_document(documents)
    service = build_service(documents, sessions, storage)

    with pytest.raises(DocumentNotFoundError):
        await service.delete_document(TEST_USER_ID_2, TEST_SESSION_ID, TEST_DOCUMENT_ID)

    assert documents.documents[TEST_DOCUMENT_ID].deleted_at is None
    assert storage.deleted == []
