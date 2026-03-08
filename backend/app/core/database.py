from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

engine = create_async_engine(settings.async_database_url, echo=settings.DEBUG)
engine = create_async_engine(settings.async_database_url, echo=settings.DEBUG)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def init_db():
    """
    No longer creates tables directly.
    Schema is managed by Alembic (alembic upgrade head).
    Keeps model imports so SQLAlchemy registers them in Base.metadata —
    required for tests that use Base.metadata.create_all().
    """
    # Import models so SQLAlchemy registers them in Base.metadata
    from app.models import document, conversation, user  # noqa


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
