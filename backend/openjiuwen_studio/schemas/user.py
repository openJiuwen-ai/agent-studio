from enum import Enum
from typing import Optional

import re

from pydantic import BaseModel, EmailStr, Field, field_validator


_PASSWORD_MIN_LENGTH = 6
_PASSWORD_MAX_LENGTH = 20
_PASSWORD_SPECIAL_PATTERN = re.compile(r"[^\w]")
_PASSWORD_DIGIT_PATTERN = re.compile(r"\d")
_PASSWORD_LOWER_PATTERN = re.compile(r"[a-z]")
_PASSWORD_UPPER_PATTERN = re.compile(r"[A-Z]")
_PASSWORD_MIN_CLASSES = 2


def _validate_password_strength(password: str) -> str:
    if len(password) < _PASSWORD_MIN_LENGTH:
        raise ValueError("密码长度至少 6 位")
    if len(password) > _PASSWORD_MAX_LENGTH:
        raise ValueError("密码长度不能超过 20 位")
    classes = [
        bool(_PASSWORD_DIGIT_PATTERN.search(password)),
        bool(_PASSWORD_LOWER_PATTERN.search(password)),
        bool(_PASSWORD_UPPER_PATTERN.search(password)),
        bool(_PASSWORD_SPECIAL_PATTERN.search(password)),
    ]
    if sum(classes) < _PASSWORD_MIN_CLASSES:
        raise ValueError("密码需包含数字/小写/大写/特殊字符中至少 2 种")
    return password


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
    refresh_token: Optional[str] = None


class UserResponse(UserInfo, UserTag):
    is_active: bool
    screen_name: str
    app_user_info: Optional[dict] = None

    class Config:
        from_attributes = True


class UserCreate(UserBase):
    password: str = Field(..., min_length=_PASSWORD_MIN_LENGTH, max_length=_PASSWORD_MAX_LENGTH)

    @field_validator("password")
    def validate_password_strength(cls, v: str) -> str:
        return _validate_password_strength(v)


class UserLogin(BaseModel):
    email: EmailStr
    password: str
    role_type: Optional[RoleType] = RoleType.COMMON_USER


class UserUpdate(UserTag):
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    user_unique_name: Optional[str] = Field(None, max_length=100)
    password: Optional[str] = Field(None, min_length=_PASSWORD_MIN_LENGTH, max_length=_PASSWORD_MAX_LENGTH)

    @field_validator("password")
    def validate_password_strength(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return _validate_password_strength(v)


class RefreshTokenRequest(BaseModel):
    refreshToken: str


class SendCodeRequest(BaseModel):
    email: EmailStr


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    code: str

    @field_validator("password")
    def validate_password_strength(cls, v: str) -> str:
        return _validate_password_strength(v)


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    code: str
    new_password: str

    @field_validator("new_password")
    def validate_password_strength(cls, v: str) -> str:
        return _validate_password_strength(v)
