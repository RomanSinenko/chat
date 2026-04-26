from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User


# Создания пользователя в БД
async def create_user(session: AsyncSession, user_name: str):
    user = User(user_name=user_name)

    session.add(user)
    await session.commit()
    await session.refresh(user)

    return user

async def get_user_by_id(session: AsyncSession, user_id: int):
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)

    return result.scalar_one_or_none()


# Поиск пользователя по части user_name в БД
async def search_users_by_name(
        session: AsyncSession,
        query: str,
        limit: int = 20,
):
    stmt = (
        select(User)
        .where(User.user_name.ilike(f'%{query}%'))
        .order_by(User.id)
        .limit(limit)
    )
    result  = await session.execute(stmt)

    return result.scalars().all()

# Ищем пользователей по-точному user_name, что бы не создавать дубликаты.
async def get_user_by_name(session: AsyncSession, user_name: str):
    stmt = (
        select(User)
        .where(func.lower(User.user_name) == user_name.lower())
    )
    result = await session.execute(stmt)

    return result.scalar_one_or_none()