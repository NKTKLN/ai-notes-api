"""Documents API router.

This module defines API endpoints for uploading, reading, downloading,
listing, and deleting chat session documents.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile, status
from loguru import logger

from ai_notes_api.api.v1.dependencies import (
    get_current_user,
    get_document_processinng_job_service,
    get_document_service,
)
from ai_notes_api.db.models import User
from ai_notes_api.schemas import (
    DocumentDownloadUrlResponse,
    DocumentListResponse,
    DocumentResponseSchema,
    ErrorResponseSchema,
    StatusResponseSchema,
)
from ai_notes_api.services import DocumentProcessingJobService, DocumentService
from ai_notes_api.workers.tasks.processing import run_document_processing_job

router = APIRouter(
    prefix="/chat/sessions/{session_id}/documents",
    tags=["Documents"],
)


DOCUMENT_DOWNLOAD_URL_EXPIRES = 60


@router.post(
    "",
    summary="Upload document to chat session",
    description="Upload a document and attach it to a chat session.",
    response_model=DocumentResponseSchema,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {
            "model": ErrorResponseSchema,
            "description": "Invalid authentication credentials",
        },
        404: {
            "model": ErrorResponseSchema,
            "description": "Session not found",
        },
    },
)
async def upload_document(
    session_id: UUID,
    file: Annotated[UploadFile, File(...)],
    user: Annotated[User, Depends(get_current_user)],
    document_service: Annotated[DocumentService, Depends(get_document_service)],
    job_service: Annotated[
        DocumentProcessingJobService, Depends(get_document_processinng_job_service)
    ],
) -> DocumentResponseSchema:
    """Upload a document to a chat session.

    Args:
        session_id (UUID): Unique chat session identifier.
        file (UploadFile): Uploaded document file.
        user (User): Current authenticated user.
        document_service (DocumentService): Document service dependency used to
            create the document.
        job_service (DocumentProcessingJobService): Processing job service
            dependency used to enqueue document processing.

    Returns:
        DocumentResponseSchema: Created document data.

    Raises:
        ChatSessionNotFoundError: If no chat session with the given identifier exists.
    """
    logger.info(
        "Document upload requested: session_id={}, filename={}",
        session_id,
        file.filename,
    )

    document = await document_service.create_document(user.id, session_id, file)

    processing_job = await job_service.create_job(document.id)

    run_document_processing_job.delay(str(processing_job.id))

    return DocumentResponseSchema.model_validate(document)


@router.get(
    "",
    summary="List chat session documents",
    description="Return all documents attached to a chat session.",
    response_model=DocumentListResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {
            "model": ErrorResponseSchema,
            "description": "Invalid authentication credentials",
        },
    },
)
async def list_documents(
    session_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[DocumentService, Depends(get_document_service)],
) -> DocumentListResponse:
    """Return documents attached to a chat session.

    Args:
        session_id (UUID): Unique chat session identifier.
        user (User): Current authenticated user.
        service (DocumentService): Document service dependency used to retrieve
            documents.

    Returns:
        DocumentListResponse: List of documents attached to the chat session.
    """
    logger.info("Documents list requested: session_id={}", session_id)

    documents = await service.list_documents(user.id, session_id)

    return DocumentListResponse(
        items=[
            DocumentResponseSchema.model_validate(document) for document in documents
        ],
        total=len(documents),
    )


@router.get(
    "/{document_id}",
    summary="Get document by ID",
    description="Return document metadata by its unique identifier.",
    response_model=DocumentResponseSchema,
    status_code=status.HTTP_200_OK,
    responses={
        401: {
            "model": ErrorResponseSchema,
            "description": "Invalid authentication credentials",
        },
        404: {
            "model": ErrorResponseSchema,
            "description": "Document not found",
        },
    },
)
async def get_document(
    session_id: UUID,
    document_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[DocumentService, Depends(get_document_service)],
) -> DocumentResponseSchema:
    """Return document metadata by its identifier.

    Args:
        session_id (UUID): Unique chat session identifier.
        document_id (UUID): Unique document identifier.
        user (User): Current authenticated user.
        service (DocumentService): Document service dependency used to retrieve
            the document.

    Returns:
        DocumentResponseSchema: Document data.

    Raises:
        DocumentNotFoundError: If no document with the given identifier exists.
    """
    logger.info(
        "Document retrieval requested: session_id={}, document_id={}",
        session_id,
        document_id,
    )

    document = await service.get_document(user.id, session_id, document_id)

    return DocumentResponseSchema.model_validate(document)


@router.get(
    "/{document_id}/download",
    summary="Download document by ID",
    description="Return a presigned URL to download a document by its identifier.",
    response_model=DocumentDownloadUrlResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {
            "model": ErrorResponseSchema,
            "description": "Invalid authentication credentials",
        },
        404: {
            "model": ErrorResponseSchema,
            "description": "Document not found",
        },
    },
)
async def download_document(
    session_id: UUID,
    document_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[DocumentService, Depends(get_document_service)],
) -> DocumentDownloadUrlResponse:
    """Return a presigned URL to download a document by its identifier.

    Args:
        session_id (UUID): Unique chat session identifier.
        document_id (UUID): Unique document identifier.
        user (User): Current authenticated user.
        service (DocumentService): Document service dependency used to generate
            the presigned download URL.

    Returns:
        DocumentDownloadUrlResponse: Presigned download URL and its expiration.

    Raises:
        DocumentNotFoundError: If no document with the given identifier exists.
    """
    logger.info(
        "Document download requested: session_id={}, document_id={}",
        session_id,
        document_id,
    )

    url = await service.get_document_download_url(
        user_id=user.id,
        session_id=session_id,
        document_id=document_id,
        expires_in_seconds=DOCUMENT_DOWNLOAD_URL_EXPIRES,
    )

    return DocumentDownloadUrlResponse(
        url=url, expires_in_seconds=DOCUMENT_DOWNLOAD_URL_EXPIRES
    )


@router.delete(
    "/{document_id}",
    summary="Delete document by ID",
    description="Delete a document from a chat session by its unique identifier.",
    response_model=StatusResponseSchema,
    status_code=status.HTTP_200_OK,
    responses={
        401: {
            "model": ErrorResponseSchema,
            "description": "Invalid authentication credentials",
        },
        404: {
            "model": ErrorResponseSchema,
            "description": "Document not found",
        },
    },
)
async def delete_document(
    session_id: UUID,
    document_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[DocumentService, Depends(get_document_service)],
) -> StatusResponseSchema:
    """Delete a document by its identifier.

    Args:
        session_id (UUID): Unique chat session identifier.
        document_id (UUID): Unique document identifier to delete.
        user (User): Current authenticated user.
        service (DocumentService): Document service dependency used to delete
            the document.

    Returns:
        StatusResponseSchema: Response status.

    Raises:
        DocumentNotFoundError: If no document with the given identifier exists.
    """
    logger.info(
        "Document deletion requested: session_id={}, document_id={}",
        session_id,
        document_id,
    )

    await service.delete_document(user.id, session_id, document_id)

    return StatusResponseSchema(status="deleted")
