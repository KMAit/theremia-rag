"""
Document service.

Validates and stores uploaded PDFs, persists DB metadata, and runs ingestion
in a background task using a dedicated DB session.
"""


import logging
import os
import re
import uuid

import aiofiles
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import NotFoundError, ValidationError
from app.repositories import document_repository
from app.services import rag_service

logger = logging.getLogger("theremia.service.document")

ALLOWED_CONTENT_TYPES: frozenset[str] = frozenset({"application/pdf"})
PDF_MAGIC_BYTES = b"%PDF"
MAX_FILENAME_LENGTH = 255


def _validate_pdf_bytes(content: bytes) -> None:
    if not content.startswith(PDF_MAGIC_BYTES):
        raise ValidationError("File does not appear to be a valid PDF.")


def _sanitize_filename(name: str) -> str:
    name = os.path.basename(name)
    name = re.sub(r"[^\w\s\-.]", "", name)
    name = name.strip(". ")
    return name[:MAX_FILENAME_LENGTH] or "document.pdf"


def _serialize(doc) -> dict:
    return {
        "id": str(doc.id),
        "user_id": str(doc.user_id),
        "filename": str(doc.filename),
        "original_name": str(doc.original_name),
        "size_bytes": int(doc.size_bytes),
        "page_count": int(doc.page_count) if doc.page_count is not None else None,
        "chunk_count": int(doc.chunk_count) if doc.chunk_count is not None else None,
        "status": str(doc.status),
        "error_message": str(doc.error_message) if doc.error_message else None,
        "created_at": doc.created_at,
    }


async def process_document_background(doc_id: str, file_path: str) -> None:
    from app.core.database import AsyncSessionLocal

    logger.info("Starting background ingestion for document %s", doc_id)

    async with AsyncSessionLocal() as db:
        try:
            result = await rag_service.ingest_document(file_path, doc_id)

            doc = await document_repository.stage_ingestion_success(
                db,
                doc_id,
                page_count=result["page_count"],
                chunk_count=result["chunk_count"],
                collection_name=result["collection_name"],
            )
            if doc is None:
                logger.error("Document %s not found after ingestion", doc_id)
                return

            await db.commit()
            logger.info("Document %s ingested chunks=%d", doc_id, result["chunk_count"])

        except Exception as exc:
            await db.rollback()
            logger.error("Ingestion failed doc=%s: %s", doc_id, exc, exc_info=True)

            doc = await document_repository.stage_ingestion_failure(
                db,
                doc_id,
                error_message=str(exc),
            )
            if doc is not None:
                await db.commit()


async def upload_document(
    db: AsyncSession,
    *,
    user_id: str,
    filename: str,
    content_type: str | None,
    content: bytes,
) -> tuple[dict, str]:
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise ValidationError("Only PDF files are supported.")

    size = len(content)
    if size == 0:
        raise ValidationError("Uploaded file is empty.")
    if size > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
        raise ValidationError(f"File exceeds the {settings.MAX_FILE_SIZE_MB}MB size limit.")

    _validate_pdf_bytes(content)

    safe_name = _sanitize_filename(filename)
    doc_id = str(uuid.uuid4())
    stored_name = f"{doc_id}.pdf"
    file_path = os.path.join(settings.UPLOAD_DIR, stored_name)

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    doc = document_repository.make_document(
        doc_id=doc_id,
        user_id=user_id,
        filename=stored_name,
        original_name=safe_name,
        size_bytes=size,
    )
    db.add(doc)

    try:
        await db.commit()
        await db.refresh(doc)
    except Exception:
        await db.rollback()
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass
        raise

    logger.info("User %s uploaded '%s' as document %s", user_id, safe_name, doc_id)
    return _serialize(doc), file_path


async def list_documents(
    db: AsyncSession,
    *,
    user_id: str,
) -> list[dict]:
    docs = await document_repository.list_by_user(db, user_id)
    return [_serialize(d) for d in docs]


async def get_document(
    db: AsyncSession,
    *,
    doc_id: str,
    user_id: str,
) -> dict:
    doc = await document_repository.get_by_id(db, doc_id, user_id)
    if doc is None:
        raise NotFoundError("Document")
    return _serialize(doc)


async def delete_document(
    db: AsyncSession,
    *,
    doc_id: str,
    user_id: str,
) -> None:
    doc = await document_repository.delete(db, doc_id, user_id)
    if doc is None:
        raise NotFoundError("Document")

    filename = str(doc.filename)
    collection_name = str(doc.collection_name) if getattr(doc, "collection_name", None) else None

    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    file_path = os.path.join(settings.UPLOAD_DIR, filename)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            logger.debug("Removed file %s", file_path)
        except OSError as exc:
            logger.warning("Could not remove file %s: %s", file_path, exc)

    if collection_name:
        await rag_service.delete_document_vectors(collection_name)

    logger.info("User %s deleted document %s", user_id, doc_id)
