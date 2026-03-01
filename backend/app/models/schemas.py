from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
import re


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

    @field_validator("title")
    @classmethod
    def sanitize_title(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return "New conversation"
        v = v.strip()
        v = re.sub(r"[\x00-\x1f\x7f]", "", v)   # retire les caractères de contrôle
        return v[:200] or "New conversation"

    @field_validator("model")
    @classmethod
    def validate_model(cls, v: Optional[str]) -> Optional[str]:
        allowed = {"gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"}
        if v and v not in allowed:
            raise ValueError(f"Model must be one of: {', '.join(sorted(allowed))}")
        return v


class ConversationUpdate(BaseModel):
    title: Optional[str] = None
    model: Optional[str] = None
    document_ids: Optional[List[str]] = None

    @field_validator("title")
    @classmethod
    def sanitize_title(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        v = re.sub(r"[\x00-\x1f\x7f]", "", v)
        return v[:200] or None

    @field_validator("model")
    @classmethod
    def validate_model(cls, v: Optional[str]) -> Optional[str]:
        allowed = {"gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"}
        if v and v not in allowed:
            raise ValueError(f"Model must be one of: {', '.join(sorted(allowed))}")
        return v

    @field_validator("document_ids")
    @classmethod
    def validate_doc_ids(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is None:
            return None
        if len(v) > 20:
            raise ValueError("Cannot attach more than 20 documents to a conversation.")
        return list(set(v))   # déduplique


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
    model: Optional[str] = None

    @field_validator("question")
    @classmethod
    def sanitize_question(cls, v: str) -> str:
        v = v.strip()
        # Retire les caractères de contrôle sauf newlines/tabs (légitimes dans une question)
        v = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", v)
        if not v:
            raise ValueError("Question cannot be empty.")
        return v

    @field_validator("model")
    @classmethod
    def validate_model(cls, v: Optional[str]) -> Optional[str]:
        allowed = {"gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"}
        if v and v not in allowed:
            raise ValueError(f"Model must be one of: {', '.join(sorted(allowed))}")
        return v


# ── Available Models ─────────────────────────────────────────────────────────

class ModelInfo(BaseModel):
    id: str
    name: str
    provider: str
    input_cost_per_1k: float
    output_cost_per_1k: float
    context_window: int
