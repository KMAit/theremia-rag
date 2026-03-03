import re
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.core.config import settings

# ── Helpers ────────────────────────────────────────────────────────────────


def _allowed_models() -> set[str]:
    provider = (settings.LLM_PROVIDER or "openai").lower()

    if provider == "ollama":
        # En local, on accepte le modèle configuré dans l'env
        return {settings.OLLAMA_MODEL}

    # API contract public
    return {"gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"}


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
    page_count: int | None
    chunk_count: int | None
    status: str
    error_message: str | None
    created_at: datetime

    class Config:
        from_attributes = True


# ── Conversations ──────────────────────────────────────────────────────────


class ConversationCreate(BaseModel):
    title: str | None = "New conversation"
    model: str | None = None
    document_ids: list[str] | None = []

    @field_validator("title")
    @classmethod
    def sanitize_title(cls, v: str | None) -> str:
        if not v:
            return "New conversation"
        v = v.strip()
        v = re.sub(r"[\x00-\x1f\x7f]", "", v)
        return v[:200] or "New conversation"

    @field_validator("model")
    @classmethod
    def validate_model(cls, v: str | None) -> str | None:
        if v is None:
            return v

        allowed = _allowed_models()
        if v not in allowed:
            raise ValueError(f"Model must be one of: {', '.join(sorted(allowed))}")

        return v


class ConversationUpdate(BaseModel):
    title: str | None = None
    model: str | None = None
    document_ids: list[str] | None = None

    @field_validator("title")
    @classmethod
    def sanitize_title(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        v = re.sub(r"[\x00-\x1f\x7f]", "", v)
        return v[:200] or None

    @field_validator("model")
    @classmethod
    def validate_model(cls, v: str | None) -> str | None:
        if v is None:
            return None

        allowed = _allowed_models()
        if v not in allowed:
            raise ValueError(f"Model must be one of: {', '.join(sorted(allowed))}")

        return v

    @field_validator("document_ids")
    @classmethod
    def validate_doc_ids(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return None
        if len(v) > 20:
            raise ValueError("Cannot attach more than 20 documents to a conversation.")
        return list(set(v))


class ConversationResponse(BaseModel):
    id: str
    title: str
    model: str
    document_ids: list[str]
    total_tokens: int
    total_cost_usd: float
    created_at: datetime
    updated_at: datetime
    message_count: int | None = 0

    class Config:
        from_attributes = True


# ── Messages ────────────────────────────────────────────────────────────────


class SourceChunk(BaseModel):
    doc_id: str
    doc_name: str
    chunk: str
    score: float
    page: int | None = None


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    sources: list[SourceChunk] | None
    tokens_used: int | None
    cost_usd: float | None
    model: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=4000)
    model: str | None = None

    @field_validator("question")
    @classmethod
    def sanitize_question(cls, v: str) -> str:
        v = v.strip()
        v = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", v)
        if not v:
            raise ValueError("Question cannot be empty.")
        return v

    @field_validator("model")
    @classmethod
    def validate_model(cls, v: str | None) -> str | None:
        if v is None:
            return None

        allowed = _allowed_models()
        if v not in allowed:
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
