from fastapi import APIRouter
from app.core.config import settings

router = APIRouter()

@router.get("/health")
async def health():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "llm_configured": bool(settings.OPENAI_API_KEY),
    }
