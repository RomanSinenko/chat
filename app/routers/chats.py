from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.queries.users import get_user_by_id
from app.queries.chats import (
    create_chat,
    get_chat_by_id,
    get_private_chat_between_users,
    get_chat_meta_by_id,
)
from app.queries.messages import get_message_by_chat_id
from app.queries.chat_members import add_chat_member, get_chat_members, get_chat_member
from app.services.peer_presentation import get_peer_display_name


router = APIRouter()


# Рабочая ручка: возвращает мета-информацию о чате для экрана открытия чата.
@router.get('/chats/{chat_id}')
async def get_chat_meta_endpoint(
        chat_id: int,
        user_id: int,
        session: AsyncSession = Depends(get_db)
):
    chat = await get_chat_meta_by_id(session, chat_id)

    if chat is None:
        raise HTTPException(status_code=404, detail='Chat not found')

    chat_member = await get_chat_member(session, chat_id, user_id)

    if chat_member is None:
        raise HTTPException(status_code=403, detail='User is not a member of this chat')

    members = await get_chat_members(session, chat.id)
    display_name = chat.title

    if chat.chat_type == 'private':
        peer_member = next((member for member in members if member.user_id != user_id), None)

        if peer_member is None:
            display_name = 'Saved Message'
        else:
            peer_user = await get_user_by_id(session, peer_member.user_id)

            if peer_user is not None:
                display_name = get_peer_display_name(peer_user)

    if not display_name:
        display_name = f'Chat {chat.id}'

    return {
        'id': chat.id,
        'chat_type': chat.chat_type,
        'title': chat.title,
        'display_name': display_name,
        'members_count': len(members),
        'created_at': chat.created_at,
        'last_message_at': chat.last_message_at,
    }


# Рабочая ручка: возвращает историю сообщений по chat_id.
@router.get('/chats/{chat_id}/messages')
async def get_chat_message_endpoint(
        chat_id: int,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
        session: AsyncSession = Depends(get_db),
):
    chat = await get_chat_by_id(session, chat_id)
    if chat is None:
        raise HTTPException(status_code=404, detail='Chat not found')

    chat_member = await get_chat_member(session, chat_id, user_id)
    if chat_member is None:
        raise HTTPException(status_code=403, detail='User is not a member of this chat')

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


# Рабочая ручка: находит существующий личный чат между двумя пользователями или создает новый.
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
            'peer_user_id': peer_user_id,
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
        'peer_user_id': peer_user_id,
        'created_at': chat.created_at,
        'created': True,
    }
