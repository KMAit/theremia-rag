"""
Service d'authentification.
Isolé des routes — ne connaît pas FastAPI Request/Response.
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import create_access_token, hash_password, verify_password
from app.core.exceptions import AppError
from app.models.user import User

logger = logging.getLogger("theremia.auth")


class AuthError(AppError):
    def __init__(self, message: str):
        super().__init__(message, status_code=401)


class ConflictError(AppError):
    def __init__(self, message: str):
        super().__init__(message, status_code=409)


async def register_user(
    db: AsyncSession,
    email: str,
    password: str,
    full_name: str | None = None,
) -> User:
    # Vérifier unicité email
    result = await db.execute(select(User).where(User.email == email.lower()))
    if result.scalar_one_or_none():
        raise ConflictError("An account with this email already exists.")

    user = User(
        email=email.lower().strip(),
        hashed_password=hash_password(password),
        full_name=full_name,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    logger.info(f"New user registered: {user.email} ({user.id})")
    return user


async def login_user(
    db: AsyncSession,
    email: str,
    password: str,
) -> tuple[User, str]:
    result = await db.execute(select(User).where(User.email == email.lower()))
    user = result.scalar_one_or_none()

    # Même message volontairement vague — ne pas révéler si l'email existe
    if not user or not verify_password(password, user.hashed_password):
        raise AuthError("Invalid email or password.")

    if not user.is_active:
        raise AuthError("Account is disabled.")

    token = create_access_token(user.id)
    logger.info(f"User logged in: {user.email} ({user.id})")
    return user, token
