"""
Data access layer for Document.

This module provides persistence primitives for the Document model.
Transaction boundaries (commit/rollback/refresh) are handled by the service layer.
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document

logger = logging.getLogger("theremia.repository.document")


async def get_by_id(
    db: AsyncSession,
    doc_id: str,
    user_id: str,
) -> Document | None:
    """Fetch a document scoped to a user."""
    result = await db.execute(
        select(Document).where(
            Document.id == doc_id,
            Document.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def get_by_id_unscoped(
    db: AsyncSession,
    doc_id: str,
) -> Document | None:
    """
    Fetch a document without user scoping.

    Intended for internal/background use where no request-scoped user is available.
    """
    result = await db.execute(select(Document).where(Document.id == doc_id))
    return result.scalar_one_or_none()


async def get_ready_by_ids(
    db: AsyncSession,
    doc_ids: list[str],
    user_id: str,
) -> list[Document]:
    """
    Return ready documents by id, scoped to user.

    Returns an empty list if no ids are provided.
    """
    if not doc_ids:
        return []

    result = await db.execute(
        select(Document).where(
            Document.id.in_(doc_ids),
            Document.user_id == user_id,
            Document.status == "ready",
        )
    )
    return list(result.scalars().all())


async def list_by_user(
    db: AsyncSession,
    user_id: str,
) -> list[Document]:
    """Return all documents owned by a user, newest first."""
    result = await db.execute(
        select(Document).where(Document.user_id == user_id).order_by(Document.created_at.desc())
    )
    return list(result.scalars().all())


def make_document(
    *,
    doc_id: str,
    user_id: str,
    filename: str,
    original_name: str,
    size_bytes: int,
) -> Document:
    """Instantiate a Document in processing status (not persisted)."""
    return Document(
        id=doc_id,
        user_id=user_id,
        filename=filename,
        original_name=original_name,
        size_bytes=size_bytes,
        status="processing",
    )


async def delete(
    db: AsyncSession,
    doc_id: str,
    user_id: str,
) -> Document | None:
    """
    Stage deletion for a document scoped to user (no commit).

    Returns the Document so the service can read filename/collection_name after staging.
    """
    result = await db.execute(
        select(Document).where(
            Document.id == doc_id,
            Document.user_id == user_id,
        )
    )
    doc = result.scalar_one_or_none()
    if doc is not None:
        await db.delete(doc)
    return doc


async def stage_ingestion_success(
    db: AsyncSession,
    doc_id: str,
    *,
    page_count: int,
    chunk_count: int,
    collection_name: str,
) -> Document | None:
    """Stage ingestion success fields (no commit)."""
    doc = await get_by_id_unscoped(db, doc_id)
    if doc is None:
        return None

    doc.status = "ready"
    doc.page_count = page_count
    doc.chunk_count = chunk_count
    doc.collection_name = collection_name
    doc.error_message = None
    return doc


async def stage_ingestion_failure(
    db: AsyncSession,
    doc_id: str,
    *,
    error_message: str,
) -> Document | None:
    """Stage ingestion failure fields (no commit)."""
    doc = await get_by_id_unscoped(db, doc_id)
    if doc is None:
        return None

    doc.status = "error"
    doc.error_message = error_message
    return doc
