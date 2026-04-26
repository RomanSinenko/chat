from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ChatMember

# Создаём связь между пользователем и чатом: фиксируем, что пользователь состоит в чате.
async def add_chat_member(
        session: AsyncSession,
        chat_id: int,
        user_id: int,
        role: str = 'member',
):
    chat_member = ChatMember(
        chat_id=chat_id,
        user_id=user_id,
        role=role,
    )

    session.add(chat_member)
    await session.commit()
    await session.refresh(chat_member)

    return chat_member


# Ищем запись membership, чтобы понять, состоит ли пользователь в конкретном чате.
async def get_chat_member(
        session: AsyncSession,
        chat_id: int,
        user_id: int,
):
    stmt = select(ChatMember).where(
        ChatMember.chat_id == chat_id,
        ChatMember.user_id == user_id,
    )
    result = await  session.execute(stmt)

    return result.scalar_one_or_none()


# Возвращаем всех участников конкретного чата.
async def get_chat_members(
        session: AsyncSession,
        chat_id: int,
):
    stmt = (
        select(ChatMember)
        .where(ChatMember.chat_id == chat_id)
        .order_by(ChatMember.id)
    )
    result = await session.execute(stmt)

    return result.scalars().all()

