import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.queries.users import search_users_by_username
from app.dependencies.auth import get_current_user_session
from app.models import UserSession


router = APIRouter()


USERNAME_MIN_LENGTH = 3
USERNAME_MAX_LENGTH = 32
DISPLAY_NAME_MIN_LENGTH = 3
DISPLAY_NAME_MAX_LENGTH = 50
USER_SEARCH_MIN_LENGTH = 3
USER_SEARCH_MAX_LENGTH = 32


def normalize_username(username: str) -> str:
    return username.strip().removeprefix('@').lower()

def is_valid_username(username: str) -> bool:
    return re.fullmatch(r'[a-z0-9_]+', username) is not None

def normalize_display_name(display_name: str) -> str:
    return ' '.join(display_name.strip().split())

def is_valid_display_name(display_name: str) -> bool:
    return re.fullmatch(r'[A-Za-zА-Яа-яЁё0-9.\- ]+', display_name) is not None

def normalize_search_query(query: str) -> str:
    return normalize_username(query)

def is_valid_search_query(query: str) -> bool:
    return is_valid_username(query)


# Рабочая ручка: ищет пользователя по точному публичному username.
@router.get('/users/search')
async def search_users_endpoint(
        query: str,
        session: AsyncSession = Depends(get_db),
        current_session: UserSession = Depends(get_current_user_session),
):

    normalized_query = normalize_search_query(query)

    if not normalized_query:
        raise HTTPException(status_code=422, detail='Query must not be empty')

    if len(normalized_query) < USER_SEARCH_MIN_LENGTH:
        return []

    if len(normalized_query) > USER_SEARCH_MAX_LENGTH:
        raise HTTPException(
            status_code=422,
            detail=f'Query must contain no more than {USER_SEARCH_MAX_LENGTH} characters',
        )

    if not is_valid_search_query(normalized_query):
        raise HTTPException(
            status_code=422,
            detail='Query contains invalid characters',
        )

    users = await search_users_by_username(
        session=session,
        query=normalized_query,
        # Не показываем текущего пользователя в результатах собственного поиска.
        exclude_user_id=current_session.user_id,
    )

    return [
        {
            'id': user.id,
            'username': user.username,
            'display_name': user.display_name,
            'is_username_custom': user.is_username_custom,
        }
        for user in users
    ]
