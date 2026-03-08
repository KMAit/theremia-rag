"""
Message HTTP endpoints.

Exposes conversation message retrieval and question submission.
All orchestration and persistence logic lives in the service layer.
"""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.schemas import AskRequest, MessageResponse
from app.models.user import User
from app.services import message_service

router = APIRouter()
logger = logging.getLogger("theremia.routes.messages")


@router.get("/{convo_id}/messages", response_model=list[MessageResponse])
async def get_messages(
    convo_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    messages = await message_service.get_messages(
        db,
        convo_id=convo_id,
        user_id=str(current_user.id),
    )
    return messages


@router.post("/{convo_id}/messages", response_model=MessageResponse, status_code=201)
async def ask_question(
    convo_id: str,
    payload: AskRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    assistant_msg = await message_service.ask_question(
        db,
        convo_id=convo_id,
        user_id=str(current_user.id),
        question=payload.question,
        model_override=payload.model,
    )
    return assistant_msg
