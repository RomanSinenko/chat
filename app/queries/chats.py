from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Chat, ChatMember
from app.queries.chat_members import get_chat_members


# Создает чат
async def create_chat(session:AsyncSession, chat_type: str, title: str | None = None):
    chat = Chat(chat_type=chat_type, title=title)

    session.add(chat)
    await session.commit()
    await session.refresh(chat)

    return chat


# Возвращает чат под chat_id
async def get_chat_by_id(session: AsyncSession, chat_id: int):
    stmt = (
        select(Chat).
        where(Chat.id == chat_id)
    )
    result = await session.execute(stmt)

    return result.scalar_one_or_none()


# Возвращает private-chat, в которых уже состоят конкретные пользователи
async def get_private_chats_by_user_id(
        session: AsyncSession,
        user_id: int,
):
    stmt = (
        select(Chat)
        .join(ChatMember, ChatMember.chat_id == Chat.id)
        .where(Chat.chat_type == 'private',
               ChatMember.user_id == user_id,
               )
        .order_by(Chat.id)
    )
    result = await session.execute(stmt)

    return result.scalars().all()


# Ищет уже существующий личный чат между двумя пользователями
async def get_private_chat_between_users(
        session: AsyncSession,
        user_id: int,
        peer_user_id: int,
):
    private_chats = await get_private_chats_by_user_id(session, user_id)

    for chat in private_chats:
        members = await  get_chat_members(session, chat.id)
        member_ids = {member.user_id for member in members}

        if member_ids == {user_id, peer_user_id}:
            return chat

    return None
