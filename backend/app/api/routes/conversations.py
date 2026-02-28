from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.models.conversation import Conversation, Message
from app.models.schemas import ConversationCreate, ConversationUpdate, ConversationResponse
from app.services.rag_service import AVAILABLE_MODELS

router = APIRouter()


@router.get("/models")
async def get_available_models():
    return AVAILABLE_MODELS


@router.post("/", response_model=ConversationResponse, status_code=201)
async def create_conversation(
    payload: ConversationCreate,
    db: AsyncSession = Depends(get_db),
):
    convo = Conversation(
        title=payload.title or "New conversation",
        model=payload.model or "gpt-4o-mini",
        document_ids=payload.document_ids or [],
    )
    db.add(convo)
    await db.commit()
    await db.refresh(convo)
    return {**convo.__dict__, "message_count": 0}


@router.get("/", response_model=list[ConversationResponse])
async def list_conversations(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Conversation).order_by(Conversation.updated_at.desc())
    )
    convos = result.scalars().all()

    out = []
    for c in convos:
        count_result = await db.execute(
            select(func.count(Message.id)).where(Message.conversation_id == c.id)
        )
        count = count_result.scalar()
        out.append({**c.__dict__, "message_count": count})
    return out


@router.get("/{convo_id}", response_model=ConversationResponse)
async def get_conversation(convo_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Conversation).where(Conversation.id == convo_id))
    convo = result.scalar_one_or_none()
    if not convo:
        raise HTTPException(404, "Conversation not found.")
    count_result = await db.execute(
        select(func.count(Message.id)).where(Message.conversation_id == convo_id)
    )
    count = count_result.scalar()
    return {**convo.__dict__, "message_count": count}


@router.patch("/{convo_id}", response_model=ConversationResponse)
async def update_conversation(
    convo_id: str,
    payload: ConversationUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Conversation).where(Conversation.id == convo_id))
    convo = result.scalar_one_or_none()
    if not convo:
        raise HTTPException(404, "Conversation not found.")

    if payload.title is not None:
        convo.title = payload.title
    if payload.model is not None:
        convo.model = payload.model
    if payload.document_ids is not None:
        convo.document_ids = payload.document_ids

    await db.commit()
    await db.refresh(convo)
    count_result = await db.execute(
        select(func.count(Message.id)).where(Message.conversation_id == convo_id)
    )
    count = count_result.scalar()
    return {**convo.__dict__, "message_count": count}


@router.delete("/{convo_id}", status_code=204)
async def delete_conversation(convo_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Conversation).where(Conversation.id == convo_id))
    convo = result.scalar_one_or_none()
    if not convo:
        raise HTTPException(404, "Conversation not found.")
    await db.delete(convo)
    await db.commit()
