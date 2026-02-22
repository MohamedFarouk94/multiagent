from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from datetime import datetime


class UserBase(BaseModel):
    username: str = Field(..., examples=["john_doe"])


class UserLogin(UserBase):
    password: str = Field(..., examples=["s3cr3tpassword"])


class UserCreate(UserLogin):
    email: EmailStr = Field(..., examples=["john@example.com"])


class UserResponse(UserBase):
    id: int
    email: EmailStr

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str = Field(..., description="JWT bearer token to use in the Authorization header")
    token_type: str = Field(..., examples=["bearer"])


class AgentCreate(BaseModel):
    name: str = Field(..., examples=["Geography Expert"])
    system_prompt: str = Field(
        ...,
        description="Instructions that define the agent's persona and behaviour",
        examples=["You are an expert in world geography, capitals, and borders."]
    )


class AgentSimple(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class AgentDetail(BaseModel):
    id: int
    name: str
    system_prompt: str
    chats: List["ChatSimple"]

    class Config:
        from_attributes = True


class ChatSimple(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class ChatCreate(BaseModel):
    agent_id: int = Field(..., description="ID of the agent this chat session belongs to")
    name: Optional[str] = Field(
        None,
        description="Display name for the chat. Auto-generated from timestamp if omitted.",
        examples=["My first chat"]
    )


class MessageResponse(BaseModel):
    id: int
    sent_at: datetime
    sender: str = Field(..., description='"user" or "agent"', examples=["agent"])
    is_audio: bool = Field(..., description="True if the message content is an audio file")
    text: str = Field(..., description="Message text. Empty string when is_audio is True.")


class AudioUploadResponse(BaseModel):
    message_id: int = Field(..., description="ID of the created audio message. Pass this to /send/ as the `audio` field.")


class SendRequest(BaseModel):
    chat_id: int
    text: Optional[str] = Field("", description="Plain text content. Required when not sending audio.")
    audio: Optional[int] = Field(
        None,
        description="message_id returned by /upload-audio/. Provide this instead of text to send a voice message."
    )