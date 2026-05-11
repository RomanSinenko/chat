import re

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.errors import api_error
from app.queries.users import (
    get_user_by_id,
    get_user_by_username,
    search_users_by_username,
    update_user_display_name,
    update_user_username,
)
from app.dependencies.auth import get_current_user_session
from app.models import UserSession


router = APIRouter()


USERNAME_MIN_LENGTH = 3
USERNAME_MAX_LENGTH = 32
DISPLAY_NAME_MIN_LENGTH = 3
DISPLAY_NAME_MAX_LENGTH = 50
USER_SEARCH_MIN_LENGTH = 3
USER_SEARCH_MAX_LENGTH = 32


class UpdateUsernameRequest(BaseModel):
    # Клиент может прислать username с @, но backend сохранит без @.
    username: str


class UpdateDisplayNameRequest(BaseModel):
    # None очищает display_name, строка устанавливает новое отображаемое имя.
    display_name: str | None


def normalize_username(username: str) -> str:
    return username.strip().removeprefix('@').lower()

def is_valid_username(username: str) -> bool:
    if re.fullmatch(r'[a-z0-9_\-!]+', username) is None:
        return False
    if re.fullmatch(r'[a-z0-9].*[a-z0-9]', username) is None:
        return False
    if '__' in username or '--' in username or '!!' in username:
        return False
    return True

def normalize_display_name(display_name: str) -> str:
    return ' '.join(display_name.strip().split())

def is_valid_display_name(display_name: str) -> bool:
    return re.fullmatch(r'[A-Za-zА-Яа-яЁё0-9._!\- ]+', display_name) is not None

def normalize_search_query(query: str) -> str:
    return normalize_username(query)

def is_valid_search_query(query: str) -> bool:
    return is_valid_username(query)


# Рабочая ручка: меняет публичный username текущего пользователя.
@router.patch('/users/me/username')
async def update_username_endpoint(
        request: UpdateUsernameRequest,
        session: AsyncSession = Depends(get_db),
        current_session: UserSession = Depends(get_current_user_session),
):
    user = await get_user_by_id(session, current_session.user_id)

    if user is None:
        raise api_error(
            status_code=404,
            code='user_not_found',
            message='User not found',
        )

    normalized_username = normalize_username(request.username)

    if len(normalized_username) < USERNAME_MIN_LENGTH:
        raise api_error(
            status_code=422,
            code='username_too_short',
            message=f'Username must contain at least {USERNAME_MIN_LENGTH} characters',
        )

    if len(normalized_username) > USERNAME_MAX_LENGTH:
        raise api_error(
            status_code=422,
            code='username_too_long',
            message=f'Username must contain no more than {USERNAME_MAX_LENGTH} characters',
        )

    if not is_valid_username(normalized_username):
        raise api_error(
            status_code=422,
            code='username_invalid_characters',
            message='Username contains invalid characters',
        )

    existing_user = await get_user_by_username(session, normalized_username)

    if existing_user is not None and existing_user.id != user.id:
        raise api_error(
            status_code=409,
            code='username_taken',
            message='Username is already taken',
        )

    updated_user = await update_user_username(
        session=session,
        user=user,
        username=normalized_username,
    )

    return {
        'id': updated_user.id,
        'username': updated_user.username,
        'display_name': updated_user.display_name,
        'is_username_custom': updated_user.is_username_custom,
    }


# Рабочая ручка: ищет пользователя по точному публичному username.
@router.get('/users/search')
async def search_users_endpoint(
        query: str,
        session: AsyncSession = Depends(get_db),
        current_session: UserSession = Depends(get_current_user_session),
):

    normalized_query = normalize_search_query(query)

    if not normalized_query:
        raise api_error(
            status_code=422,
            code='search_query_empty',
            message='Query must not be empty',
        )

    if len(normalized_query) < USER_SEARCH_MIN_LENGTH:
        return []

    if len(normalized_query) > USER_SEARCH_MAX_LENGTH:
        raise api_error(
            status_code=422,
            code='search_query_too_long',
            message=f'Query must contain no more than {USER_SEARCH_MAX_LENGTH} characters',
        )

    if not is_valid_search_query(normalized_query):
        raise api_error(
            status_code=422,
            code='search_query_invalid_characters',
            message='Query contains invalid characters',
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


# Рабочая ручка: меняет или очищает display_name текущего пользователя.
@router.patch('/users/me/display-name')
async def update_display_name_endpoint(
        request: UpdateDisplayNameRequest,
        session: AsyncSession = Depends(get_db),
        current_session: UserSession = Depends(get_current_user_session),
):
    user = await get_user_by_id(session, current_session.user_id)

    if user is None:
        raise api_error(
            status_code=404,
            code='user_not_found',
            message='User not found',
        )

    if request.display_name is None:
        updated_user = await update_user_display_name(
            session=session,
            user=user,
            display_name=None,
        )

        return {
            'id': updated_user.id,
            'username': updated_user.username,
            'display_name': updated_user.display_name,
            'is_username_custom': updated_user.is_username_custom,
        }

    normalized_display_name = normalize_display_name(request.display_name)

    if len(normalized_display_name) < DISPLAY_NAME_MIN_LENGTH:
        raise api_error(
            status_code=422,
            code='display_name_too_short',
            message=f'Display name must contain at least {DISPLAY_NAME_MIN_LENGTH} characters',
        )

    if len(normalized_display_name) > DISPLAY_NAME_MAX_LENGTH:
        raise api_error(
            status_code=422,
            code='display_name_too_long',
            message=f'Display name must contain no more than {DISPLAY_NAME_MAX_LENGTH} characters',
        )

    if not is_valid_display_name(normalized_display_name):
        raise api_error(
            status_code=422,
            code='display_name_invalid_characters',
            message='Display name contains invalid characters',
        )

    updated_user = await update_user_display_name(
        session=session,
        user=user,
        display_name=normalized_display_name,
    )

    return {
        'id': updated_user.id,
        'username': updated_user.username,
        'display_name': updated_user.display_name,
        'is_username_custom': updated_user.is_username_custom,
    }

