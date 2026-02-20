from pydantic import BaseModel, EmailStr


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
