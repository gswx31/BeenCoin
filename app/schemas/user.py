from pydantic import BaseModel, validator
from typing import Optional

class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str

    @validator('password')
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v

class UserLogin(UserBase):
    password: str

class UserOut(UserBase):
    id: int
    created_at: str
