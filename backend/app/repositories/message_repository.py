"""
Message repository — data access layer for Message.

Transaction boundaries (commit/rollback/refresh) are owned by the service.
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Message

logger = logging.getLogger("theremia.repository.message")


async def list_by_conversation(
    db: AsyncSession,
    convo_id: str,
) -> list[Message]:
    """Return all messages for a conversation, ordered chronologically."""
    result = await db.execute(
        select(Message).where(Message.conversation_id == convo_id).order_by(Message.created_at)
    )
    return list(result.scalars().all())


async def get_history_rows(
    db: AsyncSession,
    convo_id: str,
) -> list[tuple[str, str]]:
    """
    Return (role, content) tuples for a conversation.

    Raw DB data — the service transforms to dicts for the RAG pipeline.
    """
    result = await db.execute(
        select(Message.role, Message.content)
        .where(Message.conversation_id == convo_id)
        .order_by(Message.created_at)
    )
    return [(str(row.role), str(row.content)) for row in result.all()]


def make_user_message(convo_id: str, content: str) -> Message:
    """Instantiate a user Message — does not persist."""
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
    """Instantiate an assistant Message — does not persist."""
    return Message(
        conversation_id=convo_id,
        role="assistant",
        content=content,
        sources=sources,
        tokens_used=tokens_used,
        cost_usd=cost_usd,
        model=model,
    )
