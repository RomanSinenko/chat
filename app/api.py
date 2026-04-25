from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.queries.users import create_user, get_user_by_id
from app.queries.chats import create_chat, get_chat_by_id, get_private_chat_between_users
from app.queries.messages import create_message, get_message_by_chat_id
from app.queries.chat_members import add_chat_member


router = APIRouter()


# Рабочая ручка: вручную создаёт пользователя для тестов и локальной проверки БД.
@router.post('/users/{user_name}')
async def create_user_endpoint(
        user_name: str,
        session: AsyncSession = Depends(get_db),
):
    user = await create_user(session, user_name)

    return {
        'id': user.id,
        'user_name': user.user_name,
    }


# Временная ручка: вручную создаёт чат для локальной проверки message flow.
@router.post('/chats/{chat_type}')
async def create_chat_endpoint(
        chat_type: str,
        session: AsyncSession = Depends(get_db),
):
    chat = await create_chat(session=session, chat_type=chat_type)

    return {
        'id': chat.id,
        'chat_type': chat.chat_type,
        'title': chat.title,
        'created_at': chat.created_at,
    }


# Debug ручка: позволяет вручную создать сообщение в БД без WebSocket.
@router.post('/messages/{chat_id}/{sender_id}/{text}')
async def create_message_endpoint(
        chat_id: int,
        sender_id: int,
        text: str,
        session: AsyncSession = Depends(get_db),
):
    new_message = await create_message(
        session=session,
        chat_id=chat_id,
        sender_id=sender_id,
        text=text,
    )

    return {
        'id': new_message.id,
        'chat_id': new_message.chat_id,
        'sender_id': new_message.sender_id,
        'text': new_message.text,
        'message_type': new_message.message_type,
        'created_at': new_message.created_at,
    }


# Рабочая ручка: возвращает историю сообщений по chat_id
@router.get('/chats/{chat_id}/messages')
async def get_chat_message_endpoint(
        chat_id: int,
        limit: int = 50,
        offset: int = 0,
        session: AsyncSession = Depends(get_db),
):
    chat = await get_chat_by_id(session, chat_id)

    if chat is None:
        raise HTTPException(status_code=404, detail='Chat not found')

    messages = await get_message_by_chat_id(
        session=session,
        chat_id=chat_id,
        limit=limit,
        offset=offset,
    )

    return [
        {
            'id': message.id,
            'chat_id': message.chat_id,
            'sender_id': message.sender_id,
            'text': message.text,
            'message_type': message.message_type,
            'created_at': message.created_at,
        }
        for message in messages
    ]


# Рабочая ручка: находит существующий личный чат между двумя пользователями или создает новый
@router.post('/private-chats/{user_id}/{peer_user_id}')
async def get_or_create_private_chat_endpoint(
        user_id: int,
        peer_user_id: int,
        session: AsyncSession = Depends(get_db)
):
    user = await get_user_by_id(session, user_id)
    peer_user = await get_user_by_id(session, peer_user_id)

    if user is None:
        raise HTTPException(status_code=404, detail=f'User with id {user_id} not found')

    if peer_user is None:
        raise HTTPException(status_code=404, detail=f'Peer_user with id {peer_user_id} not found')

    existing_chat = await get_private_chat_between_users(session, user_id, peer_user_id)

    if existing_chat is not None:
        return {
            'id': existing_chat.id,
            'chat_type': existing_chat.chat_type,
            'title': existing_chat.title,
            'created_at': existing_chat.created_at,
            'created': False,
        }

    chat = await create_chat(
        session=session,
        chat_type='private',
    )

    await add_chat_member(session, chat.id, user_id)

    if user_id != peer_user_id:
        await add_chat_member(session, chat.id, peer_user_id)

    return {
        'id': chat.id,
        'chat_type': chat.chat_type,
        'title': chat.title,
        'created_at': chat.created_at,
        'created': True,
    }
