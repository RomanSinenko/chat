from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Chat


async def create_chat(session:AsyncSession, chat_type: str, title: str | None = None):
    chat = Chat(chat_type=chat_type, title=title)

    session.add(chat)
    await session.commit()
    await session.refresh(chat)

    return chat


async def get_chat_by_id(session: AsyncSession, chat_id: int):
    stmt = select(Chat).where(Chat.id == chat_id)
    result = await session.execute(stmt)

    return result.scalar_one_or_none()
