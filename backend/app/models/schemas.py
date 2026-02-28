from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime


# ── Documents ──────────────────────────────────────────────────────────────

class DocumentBase(BaseModel):
    filename: str
    original_name: str
    size_bytes: int

class DocumentCreate(DocumentBase):
    pass

class DocumentResponse(BaseModel):
    id: str
    filename: str
    original_name: str
    size_bytes: int
    page_count: Optional[int]
    chunk_count: Optional[int]
    status: str
    error_message: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Conversations ──────────────────────────────────────────────────────────

class ConversationCreate(BaseModel):
    title: Optional[str] = "New conversation"
    model: Optional[str] = "gpt-4o-mini"
    document_ids: Optional[List[str]] = []

class ConversationUpdate(BaseModel):
    title: Optional[str] = None
    model: Optional[str] = None
    document_ids: Optional[List[str]] = None

class ConversationResponse(BaseModel):
    id: str
    title: str
    model: str
    document_ids: List[str]
    total_tokens: int
    total_cost_usd: float
    created_at: datetime
    updated_at: datetime
    message_count: Optional[int] = 0

    class Config:
        from_attributes = True


# ── Messages ────────────────────────────────────────────────────────────────

class SourceChunk(BaseModel):
    doc_id: str
    doc_name: str
    chunk: str
    score: float
    page: Optional[int] = None

class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    sources: Optional[List[SourceChunk]]
    tokens_used: Optional[int]
    cost_usd: Optional[float]
    model: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=4000)
    model: Optional[str] = None  # override conversation model


# ── Available Models ─────────────────────────────────────────────────────────

class ModelInfo(BaseModel):
    id: str
    name: str
    provider: str
    input_cost_per_1k: float
    output_cost_per_1k: float
    context_window: int
