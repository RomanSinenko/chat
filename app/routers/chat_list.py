from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import api_error
from app.db import get_db
from app.queries.users import get_user_by_id
from app.queries.chats import get_chats_by_user_id
from app.queries.messages import get_last_message_by_chat_id
from app.queries.chat_members import get_chat_members
from app.services.peer_presentation import get_peer_display_name
from app.dependencies.auth import get_current_user_session
from app.models import UserSession



router = APIRouter()


# Рабочая ручка: возвращает список чатов пользователя.
@router.get('/users/me/chats')
async def get_user_chats_endpoint(
        session: AsyncSession = Depends(get_db),
        current_session: UserSession = Depends(get_current_user_session),
):
    # Список чатов возвращаем для пользователя из активной сессии.
    # Клиент больше не передает user_id в URL.
    user_id = current_session.user_id
    user = await get_user_by_id(session, user_id)

    if user is None:
        raise api_error(
            status_code=404,
            code='user_not_found',
            message='User not found',
        )

    chats = await get_chats_by_user_id(session, user_id)
    response = []

    for chat in chats:
        members = await get_chat_members(session, chat.id)
        last_message = await get_last_message_by_chat_id(session, chat.id)

        if chat.chat_type == 'private' and last_message is None:
            continue

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

