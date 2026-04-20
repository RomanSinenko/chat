import os

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql+asyncpg://postgres@localhost:5432/chat_db',)

# Engine отвечает за подключение SQLAlchemy к PostgreSQL.
engine = create_async_engine(
    DATABASE_URL,
    echo = True
)

# Фабрика сессий: через неё создаём отдельную AsyncSession для каждой операции с БД.
AsyncSessionLocal = async_sessionmaker(
    bind = engine,
    class_ = AsyncSession,
    expire_on_commit = False
)


class Base(DeclarativeBase):
    pass


async def init_db():
    # Импорт внутри функции нужен, чтобы SQLAlchemy увидел модели
    # и при этом не возник циклический импорт.
    from app import models

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    # Даём endpoint-ам отдельную сессию БД и потом корректно её закрываем.
    async with AsyncSessionLocal() as session:
        yield session
