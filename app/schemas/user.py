# app/schemas/user.py

from pydantic import BaseModel, field_validator


class UserBase(BaseModel):
    username: str


class UserCreate(UserBase):
    password: str

    @field_validator("username")
    @classmethod
    def username_validation(cls, v):
        if not v or len(v) < 3:
            raise ValueError("아이디는 3자 이상이어야 합니다.")
        if len(v) > 20:
            raise ValueError("아이디는 20자 이하여야 합니다.")
        if not v.isalnum():
            raise ValueError("아이디는 영문자와 숫자만 사용 가능합니다.")
        return v

    @field_validator("password")
    @classmethod
    def password_strength(cls, v):
        if not v or len(v) < 8:
            raise ValueError("비밀번호는 8자 이상이어야 합니다.")
        if len(v) > 50:
            raise ValueError("비밀번호는 50자 이하여야 합니다.")
        return v


class UserLogin(UserBase):
    password: str


class UserOut(UserBase):
    id: str  # UUID
    created_at: str

    class Config:
        from_attributes = True
