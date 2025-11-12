# app/schemas/user.py - 완성된 코드
from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str
    email: str

    @field_validator('username')
    @classmethod
    def username_validation(cls, v):
        if not v or len(v) < 3:
            raise ValueError('아이디는 3자 이상이어야 합니다.')
        if len(v) > 20:
            raise ValueError('아이디는 20자 이하여야 합니다.')
        if not v.isalnum():
            raise ValueError('아이디는 영문자와 숫자만 사용 가능합니다.')
        return v

    @field_validator('password')
    @classmethod
    def password_strength(cls, v):
        if not v or len(v) < 8:
            raise ValueError('비밀번호는 8자 이상이어야 합니다.')
        if len(v) > 50:
            raise ValueError('비밀번호는 50자 이하여야 합니다.')
        return v

    @field_validator('email')
    @classmethod
    def email_validation(cls, v):
        if not v or '@' not in v:
            raise ValueError('유효한 이메일 주소를 입력해주세요.')
        return v

class UserLogin(UserBase):
    password: str

class UserOut(UserBase):
    id: str
    created_at: str
    
    class Config:
        from_attributes = True

class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    created_at: datetime
    is_active: bool = True
    
    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse