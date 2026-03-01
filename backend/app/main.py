from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db
from app.core.exceptions import setup_logging, register_exception_handlers
from app.core.security import register_security_middleware
from app.api.routes import documents, conversations, messages, health, auth

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="Theremia RAG API",
    description="Document Q&A powered by RAG",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

register_exception_handlers(app)
register_security_middleware(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
)

# Public routes
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])

# Protected routes (each route enforces auth internally)
app.include_router(documents.router, prefix="/api/v1/documents", tags=["documents"])
app.include_router(conversations.router, prefix="/api/v1/conversations", tags=["conversations"])
app.include_router(messages.router, prefix="/api/v1/conversations", tags=["messages"])
