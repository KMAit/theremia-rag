from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.conversation import Conversation, Message
from app.models.document import Document
from app.models.schemas import AskRequest, MessageResponse
from app.services.rag_service import query_documents

router = APIRouter()


@router.get("/{convo_id}/messages", response_model=list[MessageResponse])
async def get_messages(convo_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Conversation).where(Conversation.id == convo_id))
    if not result.scalar_one_or_none():
        raise HTTPException(404, "Conversation not found.")

    msgs = await db.execute(
        select(Message).where(Message.conversation_id == convo_id).order_by(Message.created_at)
    )
    return msgs.scalars().all()


@router.post("/{convo_id}/messages", response_model=MessageResponse, status_code=201)
async def ask_question(
    convo_id: str,
    payload: AskRequest,
    db: AsyncSession = Depends(get_db),
):
    # Load conversation
    result = await db.execute(select(Conversation).where(Conversation.id == convo_id))
    convo = result.scalar_one_or_none()
    if not convo:
        raise HTTPException(404, "Conversation not found.")

    # Save user message
    user_msg = Message(
        conversation_id=convo_id,
        role="user",
        content=payload.question,
    )
    db.add(user_msg)
    await db.flush()

    # Load attached documents' collection names
    doc_ids = convo.document_ids or []
    collection_names = []
    if doc_ids:
        docs_result = await db.execute(
            select(Document).where(Document.id.in_(doc_ids), Document.status == "ready")
        )
        docs = docs_result.scalars().all()
        collection_names = [d.collection_name for d in docs if d.collection_name]

    # Build chat history for context
    history_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == convo_id)
        .order_by(Message.created_at)
    )
    history = [{"role": m.role, "content": m.content} for m in history_result.scalars().all()]

    # Call RAG pipeline
    model = payload.model or convo.model
    rag_result = await query_documents(
        question=payload.question,
        document_ids=doc_ids,
        collection_names=collection_names,
        chat_history=history,
        model=model,
    )

    # Save assistant message
    assistant_msg = Message(
        conversation_id=convo_id,
        role="assistant",
        content=rag_result["answer"],
        sources=rag_result["sources"],
        tokens_used=rag_result["tokens_used"],
        cost_usd=rag_result["cost_usd"],
        model=model,
    )
    db.add(assistant_msg)

    # Update conversation stats
    convo.total_tokens = (convo.total_tokens or 0) + (rag_result["tokens_used"] or 0)
    convo.total_cost_usd = (convo.total_cost_usd or 0) + (rag_result["cost_usd"] or 0)

    # Auto-title conversation after first exchange
    if len(history) <= 1:
        convo.title = payload.question[:60] + ("..." if len(payload.question) > 60 else "")

    await db.commit()
    await db.refresh(assistant_msg)
    return assistant_msg
