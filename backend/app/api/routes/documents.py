import os
import uuid
import aiofiles
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_db
from app.models.document import Document
from app.models.schemas import DocumentResponse
from app.services.rag_service import ingest_document, delete_document_vectors

router = APIRouter()

ALLOWED_TYPES = {"application/pdf"}
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)


async def process_document(doc_id: str, file_path: str, db_session_factory):
    """Background task: ingest document into vector store."""
    from app.core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Document).where(Document.id == doc_id))
        doc = result.scalar_one_or_none()
        if not doc:
            return
        try:
            info = await ingest_document(file_path, doc_id)
            doc.status = "ready"
            doc.page_count = info["page_count"]
            doc.chunk_count = info["chunk_count"]
            doc.collection_name = info["collection_name"]
        except Exception as e:
            doc.status = "error"
            doc.error_message = str(e)
        await db.commit()


@router.post("/", response_model=DocumentResponse, status_code=201)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=415, detail="Only PDF files are supported.")

    content = await file.read()
    size = len(content)

    if size > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File exceeds {settings.MAX_FILE_SIZE_MB}MB limit.")

    doc_id = str(uuid.uuid4())
    safe_name = f"{doc_id}.pdf"
    file_path = os.path.join(settings.UPLOAD_DIR, safe_name)

    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    doc = Document(
        id=doc_id,
        filename=safe_name,
        original_name=file.filename,
        size_bytes=size,
        status="processing",
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    background_tasks.add_task(process_document, doc_id, file_path, None)

    return doc


@router.get("/", response_model=list[DocumentResponse])
async def list_documents(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).order_by(Document.created_at.desc()))
    return result.scalars().all()


@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document(doc_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    return doc


@router.delete("/{doc_id}", status_code=204)
async def delete_document(doc_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    # Delete file
    file_path = os.path.join(settings.UPLOAD_DIR, doc.filename)
    if os.path.exists(file_path):
        os.remove(file_path)

    # Delete vectors
    if doc.collection_name:
        await delete_document_vectors(doc.collection_name)

    await db.delete(doc)
    await db.commit()
