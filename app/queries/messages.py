from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Chat, Message

# Создаем сообщение в чате
async def create_message(
        session: AsyncSession,
        chat_id: int,
        sender_id: int,
        text: str,
        message_type: str = 'text'
):

    new_message = Message(
        chat_id=chat_id,
        sender_id=sender_id,
        text=text,
        message_type=message_type,
    )

    session.add(new_message)
    await session.flush()

    chat = await session.get(Chat, chat_id)
    if chat is not None:
        chat.last_message_at = new_message.created_at

    await session.commit()
    await session.refresh(new_message)

    return new_message


# Возвращаем сообщение по chat_id
async def get_message_by_chat_id(
        session: AsyncSession,
        chat_id: int,
        limit: int = 50,
        offset: int = 0,
):
    stmt = (
        select(Message)
        .where(Message.chat_id == chat_id)
        .order_by(Message.id)
        .limit(limit)
        .offset(offset)
    )

    result = await session.execute(stmt)
    return result.scalars().all()


# Возвращаем последнее сообщение чата
async def get_last_message_by_chat_id(
        session: AsyncSession,
        chat_id: int,
):
    stmt = (
        select(Message)
        .where(Message.chat_id == chat_id)
        .order_by(Message.created_at.desc())
        .limit(1)
    )

    result = await session.execute(stmt)
    return result.scalar_one_or_none()

