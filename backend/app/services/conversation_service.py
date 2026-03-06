"""
Conversation service.

Orchestrates repository calls and owns transaction boundaries.
Returns plain dicts to keep the HTTP layer ORM-free.
"""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.repositories import conversation_repository
from app.services import rag_service

logger = logging.getLogger("theremia.service.conversation")

_DEFAULT_MODEL = "gpt-4o-mini"


def _serialize(convo, message_count: int = 0) -> dict:
    return {
        "id": str(convo.id),
        "user_id": str(convo.user_id),
        "title": str(convo.title),
        "model": str(convo.model),
        "document_ids": list(convo.document_ids or []),
        "total_tokens": int(convo.total_tokens or 0),
        "total_cost_usd": float(convo.total_cost_usd or 0.0),
        "message_count": int(message_count),
        "created_at": convo.created_at,
        "updated_at": convo.updated_at,
    }


async def get_available_models() -> list[dict]:
    return rag_service.get_available_models_for_current_provider()


async def create_conversation(
    db: AsyncSession,
    *,
    user_id: str,
    title: str | None,
    model: str | None,
    document_ids: list[str] | None,
) -> dict:
    convo = await conversation_repository.create(
        db,
        user_id=user_id,
        title=title or "New conversation",
        model=model or _DEFAULT_MODEL,
        document_ids=document_ids or [],
    )

    try:
        await db.commit()
        await db.refresh(convo)
    except Exception:
        await db.rollback()
        raise

    logger.info("User %s created conversation %s", user_id, convo.id)
    return _serialize(convo, message_count=0)


async def list_conversations(
    db: AsyncSession,
    *,
    user_id: str,
) -> list[dict]:
    pairs = await conversation_repository.list_by_user(db, user_id)
    return [_serialize(convo, count) for convo, count in pairs]


async def get_conversation(
    db: AsyncSession,
    *,
    convo_id: str,
    user_id: str,
) -> dict:
    convo = await conversation_repository.get_by_id(db, convo_id, user_id)
    if convo is None:
        raise NotFoundError("Conversation")

    count = await conversation_repository.count_messages(db, convo_id)
    return _serialize(convo, count)


async def update_conversation(
    db: AsyncSession,
    *,
    convo_id: str,
    user_id: str,
    title: str | None = None,
    model: str | None = None,
    document_ids: list[str] | None = None,
) -> dict:
    convo = await conversation_repository.get_by_id(db, convo_id, user_id)
    if convo is None:
        raise NotFoundError("Conversation")

    if title is not None:
        convo.title = title
    if model is not None:
        convo.model = model
    if document_ids is not None:
        convo.document_ids = document_ids

    try:
        await db.commit()
        await db.refresh(convo)
    except Exception:
        await db.rollback()
        raise

    count = await conversation_repository.count_messages(db, convo_id)
    return _serialize(convo, count)


async def delete_conversation(
    db: AsyncSession,
    *,
    convo_id: str,
    user_id: str,
) -> None:
    convo = await conversation_repository.delete(db, convo_id, user_id)
    if convo is None:
        raise NotFoundError("Conversation")

    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    logger.info("User %s deleted conversation %s", user_id, convo_id)
