from datetime import datetime, UTC

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User


# Создает пользователя с username и опциональным отображаемым именем.
async def create_user(
        session: AsyncSession,
        username: str,
        display_name: str | None,
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


# Ищет только точное совпадение публичного custom username.
async def search_users_by_username(
        session: AsyncSession,
        query: str,
        exclude_user_id: int | None = None,
):

    stmt = (
        select(User)
        .where(
            func.lower(User.username) == query.lower(),
            User.is_username_custom.is_(True),
        )
    )

    if exclude_user_id is not None:
        stmt = stmt.where(User.id != exclude_user_id)

    stmt = stmt.limit(1)

    result = await session.execute(stmt)

    user = result.scalar_one_or_none()

    if user is None:
        return []

    return [user]


# Ищет пользователя по username без учета регистра.
async def get_user_by_username(session: AsyncSession, username: str):
    stmt = (
        select(User)
        .where(func.lower(User.username) == username.lower())
    )
    result = await session.execute(stmt)

    return result.scalar_one_or_none()


# Обновляет публичный username пользователя.
# После смены username считаем, что пользователь выбрал его сам.
async def update_user_username(
        session: AsyncSession,
        user: User,
        username: str,
):
    user.username = username
    user.is_username_custom = True
    user.updated_at = datetime.now(UTC)

    await session.commit()
    await session.refresh(user)

    return user


# Обновляет отображаемое имя пользователя.
# display_name может быть строкой или None, если пользователь очистил имя.
async def update_user_display_name(
        session: AsyncSession,
        user: User,
        display_name: str | None,
):
    user.display_name = display_name
    user.updated_at = datetime.now(UTC)

    await session.commit()
    await session.refresh(user)

    return user

