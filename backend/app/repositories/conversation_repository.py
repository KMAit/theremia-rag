"""
Conversation repository — data access layer for Conversation.

Transaction boundaries (commit/rollback/refresh) are owned by the service.
"""

import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation, Message

logger = logging.getLogger("theremia.repository.conversation")


async def get_by_id(
    db: AsyncSession,
    convo_id: str,
    user_id: str,
) -> Conversation | None:
    """Fetch a conversation scoped to user — returns None if not found or not owned."""
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == convo_id,
            Conversation.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def list_by_user(
    db: AsyncSession,
    user_id: str,
) -> list[tuple[Conversation, int]]:
    """
    Return all conversations for a user with message counts.

    Returns list of (Conversation, message_count) tuples.
    """
    # ──fetch conversations ──────────────────────────────────────────
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .order_by(Conversation.updated_at.desc())
    )
    convos = list(result.scalars().all())

    if not convos:
        # skip GROUP BY — avoids IN () with empty list
        return []

    # ── one GROUP BY for all message counts ──────────────────────────
    convo_ids = [str(c.id) for c in convos]

    counts_result = await db.execute(
        select(
            Message.conversation_id,
            func.count(Message.id).label("msg_count"),
        )
        .where(Message.conversation_id.in_(convo_ids))
        .group_by(Message.conversation_id)
    )
    # default to 0 for conversations with no messages
    counts: dict[str, int] = {row.conversation_id: row.msg_count for row in counts_result.all()}

    # str() handles both UUID objects and plain strings
    return [(c, counts.get(str(c.id), 0)) for c in convos]


async def count_messages(
    db: AsyncSession,
    convo_id: str,
) -> int:
    """Message count for a single conversation — keeps SQLAlchemy imports out of the service."""

    result = await db.execute(
        select(func.count(Message.id)).where(Message.conversation_id == convo_id)
    )
    return result.scalar() or 0


async def create(
    db: AsyncSession,
    *,
    user_id: str,
    title: str,
    model: str,
    document_ids: list[str],
) -> Conversation:
    """Stage a new Conversation — does not commit. Returns ORM object for service refresh."""

    convo = Conversation(
        user_id=user_id,
        title=title,
        model=model,
        document_ids=document_ids,
    )
    db.add(convo)
    return convo


async def delete(
    db: AsyncSession,
    convo_id: str,
    user_id: str,
) -> Conversation | None:
    """
    Stage db.delete() and return the conversation — does not commit.

    The repo owns all DB ops (select, add, delete).
    The service owns the transaction boundary.
    Returns None if not found or not owned — service raises NotFoundError.
    """
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == convo_id,
            Conversation.user_id == user_id,
        )
    )
    convo = result.scalar_one_or_none()
    if convo is not None:
        await db.delete(convo)
    return convo
