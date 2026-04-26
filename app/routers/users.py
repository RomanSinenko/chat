import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.queries.users import create_user, search_users_by_name, get_user_by_name


router = APIRouter()


USER_NAME_MIN_LENGTH = 3
USER_NAME_MAX_LENGTH = 30
USER_SEARCH_MIN_LENGTH = 2
USER_SEARCH_MAX_LENGTH = 30


def normalize_user_name(user_name: str) -> str:
    return ' '.join(user_name.strip().split())

def is_valid_user_name(user_name: str) -> bool:
    return re.fullmatch(r'[A-Za-zА-Яа-яЁё0-9._\- ]+', user_name) is not None

def normalize_search_query(query: str) -> str:
    return  ' '.join(query.strip().split())

def is_valid_search_query(query: str) -> bool:
    return re.fullmatch(r'[A-Za-zА-Яа-яЁё0-9.\- ]+', query) is not None


# Рабочая ручка: создаёт пользователя.
@router.post('/users/{user_name}')
async def create_user_endpoint(
        user_name: str,
        session: AsyncSession = Depends(get_db),
):
    normalized_user_name = normalize_user_name(user_name)

    if len(normalized_user_name) < USER_NAME_MIN_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f'User name must contain at least {USER_NAME_MIN_LENGTH} characters',
        )

    if len(normalized_user_name) > USER_NAME_MAX_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f'User name must contain no more than {USER_NAME_MAX_LENGTH} characters',
        )

    if not is_valid_user_name(normalized_user_name):
        raise HTTPException(
            status_code=400,
            detail='User name contains invalid  characters',
        )

    existing_user = await get_user_by_name(session, normalized_user_name)

    if existing_user is not None:
        raise HTTPException(
            status_code=409,
            detail='User name is already taken'
        )

    user = await create_user(session, normalized_user_name)

    return {
        'id': user.id,
        'user_name': user.user_name,
    }


# Рабоча ручка: ищет пользователя по части имени.
@router.get('/users/search')
async def search_users_endpoint(
        query: str,
        limit: int = 20,
        session: AsyncSession = Depends(get_db),
):
    normalized_query = normalize_search_query(query)

    if not normalized_query:
        raise HTTPException(status_code=400, detail='Query must not be empty')

    if len(normalized_query) < USER_SEARCH_MIN_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f'Query must contain at least {USER_SEARCH_MIN_LENGTH} characters',
        )

    if len(normalized_query) > USER_SEARCH_MAX_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f'Query must contain no more than {USER_SEARCH_MAX_LENGTH} characters',
        )

    if not is_valid_search_query(normalized_query):
        raise HTTPException(
            status_code=400,
            detail='Query contains invalid characters',
        )

    users = await search_users_by_name(
        session=session,
        query=normalized_query,
        limit=limit,
    )

    return [
        {
            'id': user.id,
            'user_name': user.user_name,
        }
        for user in users
    ]

