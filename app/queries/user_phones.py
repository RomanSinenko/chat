from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import UserPhone


# Возвращает запись с телефоном по номеру в формате E.164.
async def get_user_phone_by_phone(
        session: AsyncSession,
        phone_e164: str,
):
    stmt = select(UserPhone).where(UserPhone.phone_e164 == phone_e164)
    result = await session.execute(stmt)

    return result.scalar_one_or_none()


# Создает связь между пользователем и его номером телефона.
async def create_user_phone(
        session: AsyncSession,
        user_id: int,
        phone_e164: str,
):
    user_phone = UserPhone(
        user_id=user_id,
        phone_e164=phone_e164,
        phone_verified_at=None,
        is_primary=True,
    )

    session.add(user_phone)
    await session.commit()
    await session.refresh(user_phone)

    return user_phone
