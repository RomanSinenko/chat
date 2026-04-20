from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Message


async def create_message(session: AsyncSession, chat_id: int, user_id: int, message: str,):

    new_message = Message(chat_id=chat_id, user_id=user_id, message=message)

    session.add(new_message)
    await session.commit()
    await session.refresh(new_message)

    return new_message
