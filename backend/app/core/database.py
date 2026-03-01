from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings


engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def init_db():
    """
    Ne crée plus les tables directement.
    Le schéma est géré par Alembic (alembic upgrade head).
    Cette fonction reste pour d'éventuelles initialisations futures.
    """
    # Importer les modèles pour que SQLAlchemy les connaisse (utile pour les tests)
    from app.models import document, conversation, user  # noqa


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
