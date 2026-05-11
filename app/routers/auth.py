from uuid import uuid4

import phonenumbers

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.queries.user_phones import get_user_phone_by_phone, create_user_phone
from app.queries.users import create_user, get_user_by_id
from app.queries.user_sessions import create_user_session, revoke_active_user_sessions


router = APIRouter()


# Проверяет телефон через phonenumbers и приводит его к формату E.164.
# Если номер нельзя разобрать или он невалидный, возвращает None.
def normalize_phone(phone: str) -> str | None:
    try:
        parsed_phone = phonenumbers.parse(phone, None)
    except phonenumbers.NumberParseException:
        return None

    if not phonenumbers.is_valid_number(parsed_phone):
        return None

    return phonenumbers.format_number(
        parsed_phone,
        phonenumbers.PhoneNumberFormat.E164,
    )


# Генерирует временный username для нового пользователя.
# Пользователь позже сможет заменить его на свой публичный @username.
def generate_default_username() -> str:
    return f'user_{uuid4().hex[:8]}'

class DevLoginRequest(BaseModel):
    # Пока это dev-login без SMS, но телефон уже передаем через JSON body, а не query.
    phone: str


@router.post('/auth/dev-login')
async def dev_login_endpoint(
        request: DevLoginRequest,
        session: AsyncSession = Depends(get_db),
):
    normalized_phone = normalize_phone(request.phone)

    if normalized_phone is None:
        raise HTTPException(
            status_code=422,
            detail='Phone must be valid and include country code, for example +79991234567',
        )

    existing_phone = await get_user_phone_by_phone(session, normalized_phone)

    if existing_phone is not None:
        user = await get_user_by_id(session, existing_phone.user_id)

        if user is None:
            raise HTTPException(
                status_code=500,
                detail='Invalid account state',
            )

        # При повторном входе отзываем старые сессии этого пользователя.
        # Для MVP держим одну активную сессию на пользователя.
        await revoke_active_user_sessions(session, user.id)
        # Plaintext token вернется клиенту, а в БД сохранится только token_hash.
        user_session, session_token = await create_user_session(session, user.id)

        return {
            'user': {
                'id': user.id,
                'username': user.username,
                'display_name': user.display_name,
                'is_username_custom': user.is_username_custom,
                'phone_verified': existing_phone.phone_verified_at is not None,
            },
            'session_token': session_token,
            'created': False,
        }

    user = await create_user(
        session=session,
        username=generate_default_username(),
        display_name=None,
        is_username_custom=False,
    )

    user_phone = await create_user_phone(
        session=session,
        user_id=user.id,
        phone_e164=normalized_phone,
    )

    # Для нового пользователя сразу создаем сессию, чтобы клиент мог ходить
    # в защищенные HTTP-ручки и подключать WebSocket.
    user_session, session_token = await create_user_session(session, user.id)

    return {
        'user': {
            'id': user.id,
            'username': user.username,
            'display_name': user.display_name,
            'is_username_custom': user.is_username_custom,
            'phone_verified': user_phone.phone_verified_at is not None,
        },
        'session_token': session_token,
        'created': True,
    }
