import logging
import os
import re
import uuid

import aiofiles
from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import NotFoundError, ValidationError
from app.models.document import Document
from app.models.schemas import DocumentResponse
from app.models.user import User
from app.services.rag_service import delete_document_vectors, ingest_document

router = APIRouter()
logger = logging.getLogger("theremia.documents")

ALLOWED_CONTENT_TYPES = {"application/pdf"}
PDF_MAGIC_BYTES = b"%PDF"
MAX_FILENAME_LENGTH = 255
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)


def validate_pdf_content(content: bytes) -> None:
    if not content.startswith(PDF_MAGIC_BYTES):
        raise ValidationError("File does not appear to be a valid PDF (invalid magic bytes).")


def sanitize_filename(name: str) -> str:
    name = os.path.basename(name)
    name = re.sub(r"[^\w\s\-.]", "", name)
    name = name.strip(". ")
    return name[:MAX_FILENAME_LENGTH] or "document.pdf"


async def process_document(doc_id: str, file_path: str):
    from app.core.database import AsyncSessionLocal

    logger.info(f"Starting ingestion for document {doc_id}")
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Document).where(Document.id == doc_id))
        doc = result.scalar_one_or_none()
        if not doc:
            logger.error(f"Document {doc_id} not found during background ingestion")
            return
        try:
            info = await ingest_document(file_path, doc_id)
            doc.status = "ready"
            doc.page_count = info["page_count"]
            doc.chunk_count = info["chunk_count"]
            doc.collection_name = info["collection_name"]
            logger.info(f"Document {doc_id} ingested: {info['chunk_count']} chunks")
        except Exception as e:
            doc.status = "error"
            doc.error_message = str(e)
            logger.error(f"Ingestion failed for {doc_id}: {e}", exc_info=True)
        await db.commit()


@router.post("/", response_model=DocumentResponse, status_code=201)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise ValidationError("Only PDF files are supported.")

    content = await file.read()
    size = len(content)

    if size == 0:
        raise ValidationError("Uploaded file is empty.")
    if size > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
        raise ValidationError(f"File exceeds the {settings.MAX_FILE_SIZE_MB}MB size limit.")

    validate_pdf_content(content)
    safe_original_name = sanitize_filename(file.filename or "document.pdf")

    doc_id = str(uuid.uuid4())
    stored_name = f"{doc_id}.pdf"
    file_path = os.path.join(settings.UPLOAD_DIR, stored_name)

    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    doc = Document(
        id=doc_id,
        user_id=current_user.id,
        filename=stored_name,
        original_name=safe_original_name,
        size_bytes=size,
        status="processing",
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    background_tasks.add_task(process_document, doc_id, file_path)
    logger.info(f"User {current_user.id} uploaded '{safe_original_name}' as {doc_id}")
    return doc


@router.get("/", response_model=list[DocumentResponse])
async def list_documents(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Document)
        .where(Document.user_id == current_user.id)
        .order_by(Document.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Document).where(
            Document.id == doc_id,
            Document.user_id == current_user.id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise NotFoundError("Document")
    return doc


@router.delete("/{doc_id}", status_code=204)
async def delete_document(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Document).where(
            Document.id == doc_id,
            Document.user_id == current_user.id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise NotFoundError("Document")

    file_path = os.path.join(settings.UPLOAD_DIR, doc.filename)
    if os.path.exists(file_path):
        os.remove(file_path)

    if doc.collection_name:
        await delete_document_vectors(doc.collection_name)

    await db.delete(doc)
    await db.commit()
    logger.info(f"User {current_user.id} deleted document {doc_id}")
