import logging
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.auth import get_current_user
from app.core.exceptions import NotFoundError
from app.models.conversation import Conversation, Message
from app.models.user import User
from app.models.schemas import ConversationCreate, ConversationUpdate, ConversationResponse
from app.services.rag_service import AVAILABLE_MODELS

router = APIRouter()
logger = logging.getLogger("theremia.conversations")


async def _get_owned_conversation(
    convo_id: str,
    current_user: User,
    db: AsyncSession,
) -> Conversation:
    """Helper : charge une conversation et vérifie l'ownership. Lève 404 sinon."""
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


async def _message_count(convo_id: str, db: AsyncSession) -> int:
    result = await db.execute(
        select(func.count(Message.id)).where(Message.conversation_id == convo_id)
    )
    return result.scalar() or 0


@router.get("/models")
async def get_available_models():
    return AVAILABLE_MODELS


@router.post("/", response_model=ConversationResponse, status_code=201)
async def create_conversation(
    payload: ConversationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    convo = Conversation(
        user_id=current_user.id,
        title=payload.title or "New conversation",
        model=payload.model or "gpt-4o-mini",
        document_ids=payload.document_ids or [],
    )
    db.add(convo)
    await db.commit()
    await db.refresh(convo)
    logger.info(f"User {current_user.id} created conversation {convo.id}")
    return {**convo.__dict__, "message_count": 0}


@router.get("/", response_model=list[ConversationResponse])
async def list_conversations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == current_user.id)
        .order_by(Conversation.updated_at.desc())
    )
    convos = result.scalars().all()
    return [
        {**c.__dict__, "message_count": await _message_count(c.id, db)}
        for c in convos
    ]


@router.get("/{convo_id}", response_model=ConversationResponse)
async def get_conversation(
    convo_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    convo = await _get_owned_conversation(convo_id, current_user, db)
    return {**convo.__dict__, "message_count": await _message_count(convo_id, db)}


@router.patch("/{convo_id}", response_model=ConversationResponse)
async def update_conversation(
    convo_id: str,
    payload: ConversationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    convo = await _get_owned_conversation(convo_id, current_user, db)

    if payload.title is not None:
        convo.title = payload.title
    if payload.model is not None:
        convo.model = payload.model
    if payload.document_ids is not None:
        convo.document_ids = payload.document_ids

    await db.commit()
    await db.refresh(convo)
    return {**convo.__dict__, "message_count": await _message_count(convo_id, db)}


@router.delete("/{convo_id}", status_code=204)
async def delete_conversation(
    convo_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    convo = await _get_owned_conversation(convo_id, current_user, db)
    await db.delete(convo)
    await db.commit()
    logger.info(f"User {current_user.id} deleted conversation {convo_id}")
