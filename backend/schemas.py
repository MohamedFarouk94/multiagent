from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime

# -------------------------
# User Schemas
# -------------------------

class UserBase(BaseModel):
    username: str


class UserLogin(UserBase):
    password: str


class UserCreate(UserLogin):
    email: EmailStr


class UserResponse(UserBase):
    id: int
    email: EmailStr

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str

# -------------------------
# Agent Schemas
# -------------------------

class AgentCreate(BaseModel):
    name: str
    system_prompt: str


class AgentSimple(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class ChatSimple(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class AgentDetail(BaseModel):
    id: int
    name: str
    system_prompt: str
    chats: List[ChatSimple]

    class Config:
        from_attributes = True


# -------------------------
# Chat Schemas
# -------------------------

class ChatCreate(BaseModel):
    agent_id: int
    name: Optional[str] = None


class MessageResponse(BaseModel):
    id: int
    sent_at: datetime
    sender: str
    is_audio: bool
    text: str


class SendRequest(BaseModel):
    chat_id: int
    text: Optional[str] = ""
    audio: Optional[int] = None
