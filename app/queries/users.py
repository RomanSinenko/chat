from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User


# Создает пользователя с username и отображаемым именем.
async def create_user(
        session: AsyncSession,
        username: str,
        display_name: str,
        is_username_custom: bool = False,
):
    user = User(
        username=username,
        display_name=display_name,
        is_username_custom=is_username_custom,
    )

    session.add(user)
    await session.commit()
    await session.refresh(user)

    return user


# Возвращает пользователя по внутреннему id.
async def get_user_by_id(session: AsyncSession, user_id: int):
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)

    return result.scalar_one_or_none()

# Ищет пользователей только по публичному username.
async def search_users_by_username(
        session: AsyncSession,
        query: str,
        limit: int = 20,
):
    stmt = (
        select(User)
        .where(User.username.ilike(f'%{query}%'))
        .order_by(User.id)
        .limit(limit)
    )
    result = await session.execute(stmt)

    return result.scalars().all()


# Ищет пользователя по username без учета регистра.
async def get_user_by_username(session: AsyncSession, username: str):
    stmt = (
        select(User)
        .where(func.lower(User.username) == username.lower())
    )
    result = await session.execute(stmt)

    return result.scalar_one_or_none()
