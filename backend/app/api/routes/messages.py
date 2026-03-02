import logging

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.core.exceptions import NotFoundError, RAGError
from app.models.conversation import Conversation, Message
from app.models.document import Document
from app.models.schemas import AskRequest, MessageResponse
from app.models.user import User
from app.services.rag_service import query_documents

router = APIRouter()
logger = logging.getLogger("theremia.messages")


async def _get_owned_conversation(
    convo_id: str,
    current_user: User,
    db: AsyncSession,
) -> Conversation:
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == convo_id,
            Conversation.user_id == current_user.id,
        )
    )
    convo = result.scalar_one_or_none()
    if not convo:
        raise NotFoundError("Conversation")
    return convo


@router.get("/{convo_id}/messages", response_model=list[MessageResponse])
async def get_messages(
    convo_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_owned_conversation(convo_id, current_user, db)

    result = await db.execute(
        select(Message).where(Message.conversation_id == convo_id).order_by(Message.created_at)
    )
    return result.scalars().all()


@router.post("/{convo_id}/messages", response_model=MessageResponse, status_code=201)
async def ask_question(
    convo_id: str,
    payload: AskRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    convo = await _get_owned_conversation(convo_id, current_user, db)

    # Charger uniquement les documents appartenant à cet utilisateur
    doc_ids = convo.document_ids or []
    collection_names = []
    if doc_ids:
        docs_result = await db.execute(
            select(Document).where(
                Document.id.in_(doc_ids),
                Document.user_id == current_user.id,
                Document.status == "ready",
            )
        )
        docs = docs_result.scalars().all()
        collection_names = [d.collection_name for d in docs if d.collection_name]

    history_result = await db.execute(
        select(Message).where(Message.conversation_id == convo_id).order_by(Message.created_at)
    )
    history = [{"role": m.role, "content": m.content} for m in history_result.scalars().all()]

    model = payload.model or convo.model
    logger.info(
        f"RAG query — user={current_user.id} convo={convo_id} "
        f"model={model} docs={len(collection_names)}"
    )

    try:
        rag_result = await query_documents(
            question=payload.question,
            document_ids=doc_ids,
            collection_names=collection_names,
            chat_history=history,
            model=model,
        )
    except Exception as e:
        logger.error(f"RAG failed — convo={convo_id}: {e}", exc_info=True)
        raise RAGError(f"Failed to generate answer: {e!s}") from e

    user_msg = Message(
        conversation_id=convo_id,
        role="user",
        content=payload.question,
    )
    assistant_msg = Message(
        conversation_id=convo_id,
        role="assistant",
        content=rag_result["answer"],
        sources=rag_result["sources"],
        tokens_used=rag_result["tokens_used"],
        cost_usd=rag_result["cost_usd"],
        model=model,
    )
    db.add(user_msg)
    db.add(assistant_msg)

    convo.total_tokens = (convo.total_tokens or 0) + (rag_result["tokens_used"] or 0)
    convo.total_cost_usd = (convo.total_cost_usd or 0) + (rag_result["cost_usd"] or 0)

    if len(history) == 0:
        convo.title = payload.question[:60] + ("..." if len(payload.question) > 60 else "")

    await db.commit()
    await db.refresh(assistant_msg)
    return assistant_msg
