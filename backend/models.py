from sqlalchemy import Column, Integer, String, Boolean, Text, ForeignKey, DateTime, UniqueConstraint
from .database import Base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    
    agents = relationship(
        "Agent",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True
    )


class Agent(Base):
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False)
    system_prompt = Column(Text, nullable=False)

    # Ensure agent name is unique per user (not globally)
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_user_agent_name"),
    )

    user = relationship("User", back_populates="agents")
    chats = relationship(
        "Chat",
        back_populates="agent",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="desc(Chat.last_message_at)"
    )


class Chat(Base):
    __tablename__ = "chats"

    id = Column(Integer, primary_key=True, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    name = Column(String, nullable=False)

    agent_id = Column(Integer, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    last_message_at = Column(DateTime(timezone=True), index=True)

    agent = relationship("Agent", back_populates="chats")
    messages = relationship(
        "Message",
        back_populates="chat",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Message.sent_at"
    )


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)

    sent_at = Column(DateTime(timezone=True), server_default=func.now())

    chat_id = Column(Integer, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False, index=True)

    is_agent = Column(Boolean, nullable=False)

    is_audio = Column(Boolean, nullable=False)

    text = Column(Text, nullable=False)

    chat = relationship("Chat", back_populates="messages")
