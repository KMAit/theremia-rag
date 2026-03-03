"""
Message Repository — data access layer for Message model.

RULES ENFORCED HERE:
- No commit(), rollback(), or refresh() — that's the service's job.
- No business logic — only data access primitives.
- No lazy-loaded relationships returned — all selects are explicit.
- No RAG-specific formatting — the service owns that transformation.
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Message

logger = logging.getLogger("theremia.repository.message")


async def list_by_conversation(
    db: AsyncSession,
    convo_id: str,
) -> list[Message]:
    """
    Return all messages for a conversation, ordered chronologically.
    No relationship traversal — explicit SELECT only.
    """
    result = await db.execute(
        select(Message).where(Message.conversation_id == convo_id).order_by(Message.created_at)
    )
    return list(result.scalars().all())


async def get_history_rows(
    db: AsyncSession,
    convo_id: str,
) -> list[tuple[str, str]]:
    """
    Return (role, content) tuples for all messages in a conversation.

    WHY TUPLES AND NOT DICTS?
    The repo returns raw DB data. It's the service's responsibility to
    transform (role, content) into {"role": ..., "content": ...} for
    the RAG pipeline. This way the repo has zero knowledge of RAG's
    expected format — it only knows what's in the DB.
    """
    result = await db.execute(
        select(Message.role, Message.content)
        .where(Message.conversation_id == convo_id)
        .order_by(Message.created_at)
    )
    return [(str(row.role), str(row.content)) for row in result.all()]


def make_user_message(convo_id: str, content: str) -> Message:
    """
    Instantiate (but do not persist) a user Message ORM object.

    WHY A FACTORY FUNCTION?
    Centralises Message construction. If we add a new required field later
    (e.g. ip_address for audit), we change it in one place.
    The service calls db.add() — the repo never does.
    """
    return Message(
        conversation_id=convo_id,
        role="user",
        content=content,
    )


def make_assistant_message(
    convo_id: str,
    *,
    content: str,
    sources: list[dict],
    tokens_used: int,
    cost_usd: float,
    model: str,
) -> Message:
    """Instantiate (but do not persist) an assistant Message ORM object."""
    return Message(
        conversation_id=convo_id,
        role="assistant",
        content=content,
        sources=sources,
        tokens_used=tokens_used,
        cost_usd=cost_usd,
        model=model,
    )
