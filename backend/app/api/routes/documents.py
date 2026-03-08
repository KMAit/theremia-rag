"""
Document HTTP endpoints.

Handles request/response mapping and delegates document lifecycle
operations to the service layer.
Background ingestion is scheduled from here.
"""

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile, status

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.schemas import DocumentResponse
from app.models.user import User
from app.services import document_service

router = APIRouter()
logger = logging.getLogger("theremia.routes.documents")


@router.post("/", response_model=DocumentResponse, status_code=201)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Accepts a PDF upload, persists metadata, and schedules background ingestion.
    Returns 201 immediately — document becomes queryable once status reaches 'ready'.
    """

    # Read bytes here — UploadFile is a FastAPI/HTTP concept,
    # not something the service should depend on.
    content = await file.read()

    doc, file_path = await document_service.upload_document(
        db,
        user_id=str(current_user.id),
        filename=file.filename or "document.pdf",
        content_type=file.content_type,
        content=content,
    )

    # BackgroundTasks is a FastAPI concept — stays in the route.
    # The function it calls (process_document_background) is pure service logic.
    background_tasks.add_task(
        document_service.process_document_background,
        doc["id"],
        file_path,
    )

    return doc


@router.get("/", response_model=list[DocumentResponse])
async def list_documents(
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await document_service.list_documents(db, user_id=str(current_user.id))


@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document(
    doc_id: str,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await document_service.get_document(db, doc_id=doc_id, user_id=str(current_user.id))


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    doc_id: str,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await document_service.delete_document(db, doc_id=doc_id, user_id=str(current_user.id))
