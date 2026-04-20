from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.queries.users import create_user
from app.queries.chats import create_chat
from app.queries.messages import create_message


router = APIRouter()

# Рабочая ручка текущего этапа: вручную создаёт пользователя для тестов и локальной проверки БД.
@router.post('/users/{user_name}')
async def create_user_endpoint(user_name: str, session: AsyncSession = Depends(get_db),):
    user = await create_user(session, user_name)

    return {
        'id': user.id,
        'user_name': user.user_name,
    }


# Временная ручка текущего этапа: вручную создаёт чат для локальной проверки message flow.
@router.post('/chats')
async def create_chat_endpoint(session: AsyncSession = Depends(get_db),):
    chat = await create_chat(session)

    return {
        'id': chat.id,
    }


# Debug-ручка текущего этапа: позволяет вручную создать сообщение в БД без WebSocket.
@router.post('/messages/{chat_id}/{user_id}/{message}')
async def create_message_endpoint(
        chat_id: int,
        user_id: int,
        message: str,
        session: AsyncSession = Depends(get_db),
):
    new_message = await create_message(
        session=session,
        chat_id=chat_id,
        user_id=user_id,
        message=message,
    )

    return {
        'id': new_message.id,
        'chat_id': new_message.chat_id,
        'user_id': new_message.user_id,
        'message': new_message.message,
    }
