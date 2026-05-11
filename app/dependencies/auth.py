from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import UserSession
from app.queries.user_sessions import get_active_user_session_by_token


# Достает plaintext session token из HTTP header Authorization.
# Ожидаемый формат: Authorization: Bearer <session_token>.
# Hash из БД сюда передавать нельзя: backend сам захеширует plaintext token.
def extract_bearer_token(authorization: str | None) -> str:
    if authorization is None or not authorization.startswith('Bearer '):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Authorization Bearer token is required',
        )

    session_token = authorization.removeprefix('Bearer ').strip()

    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Authorization Bearer token is required',
        )

    return session_token


# Общая dependency для защищенных HTTP-ручек.
# Если токен валидный, возвращает активную UserSession.
# Если токена нет, он просрочен или отозван, FastAPI вернет 401.
async def get_current_user_session(
        authorization: str | None = Header(default=None),
        session: AsyncSession = Depends(get_db),
) -> UserSession:
    session_token = extract_bearer_token(authorization)
    user_session = await get_active_user_session_by_token(session, session_token)

    if user_session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid or expired session token',
        )

    return user_session
