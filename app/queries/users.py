from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User


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
