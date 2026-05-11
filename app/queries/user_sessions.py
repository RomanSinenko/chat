from datetime import datetime, UTC, timedelta
from hashlib import sha256
from secrets import token_urlsafe

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import UserSession


SESSION_TTL_DAYS = 30


# Превращает session token в hash для безопасного хранения в БД.
def hash_session_token(session_token: str) -> str:
    return sha256(session_token.encode('utf-8')).hexdigest()


# Создает новую сессию пользователя и возвращает plaintext token один раз.
async def create_user_session(session: AsyncSession, user_id: int) -> tuple[UserSession, str]:
    # Plaintext token нужен клиенту для Authorization header.
    # В БД он не сохраняется, чтобы утечка БД не раскрыла активные токены напрямую.
    session_token = token_urlsafe(32)
    token_hash = hash_session_token(session_token)

    user_session = UserSession(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=datetime.now(UTC) + timedelta(days=SESSION_TTL_DAYS)
    )

    session.add(user_session)
    await session.commit()
    await session.refresh(user_session)

    return user_session, session_token


# Отзывает все активные сессии пользователя.
async def revoke_active_user_sessions(session: AsyncSession, user_id: int):
    now = datetime.now(UTC)

    stmt = (
        select(UserSession)
        .where(UserSession.user_id == user_id)
        .where(UserSession.revoked_at.is_(None))
    )

    result = await session.execute(stmt)
    user_sessions = result.scalars().all()

    for user_session in user_sessions:
        user_session.revoked_at = now

    await session.commit()


# Ищет активную сессию по plaintext token.
async def get_active_user_session_by_token(session: AsyncSession, session_token: str):
    now = datetime.now(UTC)
    token_hash = hash_session_token(session_token)

    stmt = (
        select(UserSession)
        .where(UserSession.token_hash == token_hash)
        .where(UserSession.revoked_at.is_(None))
        .where(UserSession.expires_at > now)
    )

    result = await session.execute(stmt)
    user_session = result.scalar_one_or_none()

    if user_session is not None:
        # Обновляем время последнего использования, чтобы позже видеть активность сессий.
        user_session.last_used_at = now
        await session.commit()
        await session.refresh(user_session)

    return user_session


# Ищет активную сессию по id.
async def get_active_user_session_by_id(session: AsyncSession, session_id: int):
    now = datetime.now(UTC)

    stmt = (
        select(UserSession)
        .where(UserSession.id == session_id)
        .where(UserSession.revoked_at.is_(None))
        .where(UserSession.expires_at > now)
    )

    result = await session.execute(stmt)
    user_session = result.scalar_one_or_none()

    if user_session is not None:
        # Обновляем время последнего использования, чтобы позже видеть активность сессий.
        user_session.last_used_at = now
        await session.commit()
        await session.refresh(user_session)

    return user_session
