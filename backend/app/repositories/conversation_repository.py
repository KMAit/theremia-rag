"""
Conversation Repository — data access layer for Conversation model.

RULES ENFORCED HERE:
- No commit(), rollback(), or refresh() — that's the service's job.
- No business logic — only data access primitives.
- No lazy-loaded relationships — all selects are explicit.

N+1 FIX FOR list_by_user:
Instead of one COUNT query per conversation (N+1), we use:
  Query 1: fetch all conversations for the user
  Query 2: one GROUP BY query to count messages for all conversation IDs at once
  Merge: O(1) dict lookup per conversation
This keeps the total at exactly 2 queries regardless of conversation count.
"""

from __future__ import annotations

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
    """
    Fetch a single conversation scoped to a user.

    WHY user_id IN EVERY READ?
    Defense in depth — ownership is enforced at the DB level, not just
    in the service. Even if a caller forgets to check, the wrong user
    simply gets None instead of another user's data.
    """
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
    Return all conversations for a user with their message counts.

    Returns list of (Conversation, message_count) tuples.
    The service unpacks these — the route sees nothing of this internals.

    EDGE CASE: if no conversations exist, we return [] immediately
    and skip the GROUP BY query entirely (no IN () with empty list).
    """
    # ── Query 1: fetch conversations ──────────────────────────────────────────
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .order_by(Conversation.updated_at.desc())
    )
    convos = list(result.scalars().all())

    if not convos:
        return []

    # ── Query 2: one GROUP BY for all message counts ──────────────────────────
    # SELECT conversation_id, COUNT(id) FROM messages
    # WHERE conversation_id IN (...) GROUP BY conversation_id
    convo_ids = [str(c.id) for c in convos]

    counts_result = await db.execute(
        select(
            Message.conversation_id,
            func.count(Message.id).label("msg_count"),
        )
        .where(Message.conversation_id.in_(convo_ids))
        .group_by(Message.conversation_id)
    )
    # Build a dict for O(1) merge — conversations with no messages won't
    # appear in the result, so we default to 0.
    counts: dict[str, int] = {row.conversation_id: row.msg_count for row in counts_result.all()}

    # ── Merge ─────────────────────────────────────────────────────────────────
    # str(c.id) handles both UUID objects and plain strings safely.
    return [(c, counts.get(str(c.id), 0)) for c in convos]


async def count_messages(
    db: AsyncSession,
    convo_id: str,
) -> int:
    """
    COUNT messages for a single conversation.

    Used by get_conversation and update_conversation in the service.
    Lives here so the service never imports SQLAlchemy func/select.
    """
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
    """
    Instantiate and stage a new Conversation — does NOT commit.

    The service calls db.commit() + db.refresh().
    We return the ORM object so the service can refresh it after commit.
    """
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
    Load, stage db.delete(), and return the conversation — does NOT commit.

    WHY db.delete() IN THE REPO?
    The repo owns all DB operations on Conversation (select, add, delete).
    The service owns the transaction boundary (commit/rollback).
    This avoids the double-delete risk of repo returning ORM + service
    calling db.delete() independently.

    Returns None if not found or not owned by user — service raises NotFoundError.
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
