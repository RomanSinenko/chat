from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.queries.users import get_user_by_id
from app.queries.chats import get_chats_by_user_id
from app.queries.messages import get_last_message_by_chat_id
from app.queries.chat_members import get_chat_members
from app.services.peer_presentation import get_peer_display_name


router = APIRouter()


# Рабочая ручка: возвращает список чатов пользователя.
@router.get('/users/{user_id}/chats')
async def get_user_chats_endpoint(
        user_id: int,
        session: AsyncSession = Depends(get_db),
):
    user = await get_user_by_id(session, user_id)

    if user is None:
        raise HTTPException(status_code=404, detail=f'User with id {user_id} not found')

    chats = await get_chats_by_user_id(session, user_id)
    response = []

    for chat in chats:
        members = await get_chat_members(session, chat.id)
        last_message = await get_last_message_by_chat_id(session, chat.id)

        display_name = chat.title
        peer_user_id = None

        if chat.chat_type == 'private':
            peer_member = next((member for member in members if member.user_id != user_id), None)

            if peer_member is None:
                display_name = 'Saved Messages'
            else:
                peer_user_id = peer_member.user_id
                peer_user = await get_user_by_id(session, peer_member.user_id)

                if peer_user is not None:
                    display_name = get_peer_display_name(peer_user)

        if not display_name:
            display_name = f'Chat {chat.id}'

        response.append(
            {
                'id': chat.id,
                'chat_type': chat.chat_type,
                'title': chat.title,
                'display_name': display_name,
                'peer_user_id': peer_user_id,
                'members_count': len(members),
                'created_at': chat.created_at,
                'last_message': None if last_message is None else {
                    'id': last_message.id,
                    'sender_id': last_message.sender_id,
                    'text': last_message.text,
                    'message_type': last_message.message_type,
                    'created_at': last_message.created_at,
                }
            }
        )

    return response