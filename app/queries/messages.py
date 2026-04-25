from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Message


async def create_message(
        session: AsyncSession,
        chat_id: int,
        sender_id: int,
        text: str,
        message_type: str = 'text'
):

    new_message = Message(
        chat_id=chat_id, sender_id=sender_id, text=text, message_type=message_type)

    session.add(new_message)
    await session.commit()
    await session.refresh(new_message)

    return new_message


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

