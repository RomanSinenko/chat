from datetime import datetime

from sqlalchemy import String, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)


class Chat(Base):
    __tablename__ = 'chats'

    id: Mapped[int] = mapped_column(primary_key=True)
    chat_type: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class Message(Base):
    __tablename__ = 'messages'

    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey('chats.id'), nullable=False)
    sender_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)
    text: Mapped[str] = mapped_column(String, nullable=False)
    message_type: Mapped[str] = mapped_column(String(20), default='text', nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class ChatMember(Base):
    __tablename__ = 'chat_members'

    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey('chats.id'), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default='member', nullable=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
