"""
Conversation HTTP endpoints.

This module defines the REST contract for conversation management.
All business rules and persistence logic are delegated to the service layer.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.schemas import ConversationCreate, ConversationResponse, ConversationUpdate
from app.models.user import User
from app.services import conversation_service

router = APIRouter()
logger = logging.getLogger("theremia.routes.conversations")


@router.get("/models")
async def get_available_models():
    return await conversation_service.get_available_models()


@router.post("/", response_model=ConversationResponse, status_code=201)
async def create_conversation(
    payload: ConversationCreate,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await conversation_service.create_conversation(
        db,
        user_id=str(current_user.id),
        title=payload.title,
        model=payload.model,
        document_ids=list(payload.document_ids or []),
    )


@router.get("/", response_model=list[ConversationResponse])
async def list_conversations(
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await conversation_service.list_conversations(
        db,
        user_id=str(current_user.id),
    )


@router.get("/{convo_id}", response_model=ConversationResponse)
async def get_conversation(
    convo_id: str,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await conversation_service.get_conversation(
        db,
        convo_id=convo_id,
        user_id=str(current_user.id),
    )


@router.patch("/{convo_id}", response_model=ConversationResponse)
async def update_conversation(
    convo_id: str,
    payload: ConversationUpdate,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await conversation_service.update_conversation(
        db,
        convo_id=convo_id,
        user_id=str(current_user.id),
        title=payload.title,
        model=payload.model,
        document_ids=list(payload.document_ids) if payload.document_ids is not None else None,
    )


@router.delete("/{convo_id}", status_code=204)
async def delete_conversation(
    convo_id: str,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await conversation_service.delete_conversation(
        db,
        convo_id=convo_id,
        user_id=str(current_user.id),
    )
