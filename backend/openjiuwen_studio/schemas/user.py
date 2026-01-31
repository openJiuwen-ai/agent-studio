from enum import Enum
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class RoleType(Enum):
    COMMON_USER = 0
    SUPER_USER = 1


class UserBase(BaseModel):
    user_id_str: str
    username: str = Field(..., min_length=3, max_length=50)
    user_unique_name: str
    avatar_url: Optional[str] = None
    role_type: RoleType


class UserInfo(UserBase):
    email: EmailStr
    locale: str
    description: Optional[str] = None
    user_create_time: int
    user_update_time: int


class UserTag(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    company: Optional[str] = None
    occupation: Optional[str] = None
    skills: Optional[list[str]] = []


class UserDBPd(UserInfo, UserTag):
    session_key: Optional[str] = None
    password: str
    is_active: bool
    

class UserResponse(UserInfo, UserTag):
    is_active: bool
    screen_name: str
    app_user_info: Optional[dict] = None

    class Config:
        from_attributes = True


class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=100)


class UserLogin(BaseModel):
    email: EmailStr
    password: str
    role_type: Optional[RoleType] = RoleType.COMMON_USER


class UserUpdate(UserTag):
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    user_unique_name: Optional[str] = Field(None, max_length=100)
    password: Optional[str] = Field(None, min_length=6, max_length=50)


class RefreshTokenRequest(BaseModel):
    refreshToken: str


class SendCodeRequest(BaseModel):
    email: EmailStr


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    code: str


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    code: str
    new_password: str
