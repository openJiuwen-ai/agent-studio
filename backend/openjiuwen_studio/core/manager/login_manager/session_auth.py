import hashlib
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import jwt
from fastapi import status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from openjiuwen.core.common.logging import logger
from pydantic import BaseModel, EmailStr

from openjiuwen_studio.core.config import settings
from openjiuwen_studio.core.manager.repositories.user_repository import user_repository
from openjiuwen_studio.schemas.user import (RoleType, UserDBPd, UserInfo, UserLogin,
                              UserResponse)
from openjiuwen_studio.core.manager.model_manager.utils import SecurityUtils

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="v1/auth/login")


def hash_password(plain_password: str):
    return hashlib.sha256(plain_password.encode()).hexdigest()


def verify_password(plain_password: str, user_db: UserDBPd) -> bool:
    # 查找用户
    if hash_password(plain_password) == user_db.password:
        return True
    return False


def authenticate_user(email: str, password: str):
    """Authenticate user with username and password"""
    ret = user_repository.get_user_tbl(email)
    if ret.get("code") != status.HTTP_200_OK:
        logger.info(ret)
        return False
    user = ret.get("data")
    user_db = UserDBPd(**user)

    if not verify_password(password, user_db):
        return False
    return user_db


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = (datetime.now(timezone.utc) + expires_delta).replace(tzinfo=None)
    else:
        if settings.enable_new_auth:
            # 新密码体系：短期 access token
            expire = (
                datetime.now(timezone.utc)
                + timedelta(minutes=settings.new_access_token_expire_minutes)
            ).replace(tzinfo=None)
        else:
            # 单机部署：超长 access token
            expire = (
                datetime.now(timezone.utc)
                + timedelta(minutes=settings.access_token_expire_minutes)
            ).replace(tzinfo=None)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT refresh token"""
    to_encode = data.copy()
    if expires_delta:
        expire = (datetime.now(timezone.utc) + expires_delta).replace(tzinfo=None)
    else:
        # 新密码体系：短期 refresh token
        if settings.enable_new_auth:
            expire = (
                datetime.now(timezone.utc) 
                + timedelta(days=settings.new_refresh_token_expire_days)
            ).replace(tzinfo=None)
        else:
            # 单机部署：超长 refresh token
            expire = (
                datetime.now(timezone.utc) 
                + timedelta(days=settings.refresh_token_expire_days)
            ).replace(tzinfo=None)

    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


def verify_refresh_token(token: str):
    """Verify refresh token and return payload"""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])

        # Check if it's a refresh token
        if payload.get("type") != "refresh":
            return None

        # Check if token is expired
        if datetime.now(timezone.utc).replace(tzinfo=None) > datetime.fromtimestamp(payload.get("exp")):
            return None

        return payload
    except jwt.PyJWTError:
        return None


def verify_refresh_token_strict(token: str):
    """Verify refresh token, check DB consistency (签名+类型+数据库一致性)"""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])

        # Check if it's a refresh token
        if payload.get("type") != "refresh":
            return None

        # Check if token is expired
        if datetime.now(timezone.utc).replace(tzinfo=None) > datetime.fromtimestamp(payload.get("exp")):
            return None

        # 校验数据库中 refresh_token 是否一致
        email = payload.get("sub")
        if not email:
            return None
        ret = user_repository.get_user_tbl(email)
        if ret.get("code") != status.HTTP_200_OK:
            return None
        user = ret.get("data")
        user_db = UserDBPd(**user)
        db_refresh_token = user_db.refresh_token
        if not db_refresh_token:
            return None
        security_util = SecurityUtils()
        decrpyted_db_refresh_token = security_util.decrypt_api_key(db_refresh_token)
        if not decrpyted_db_refresh_token or decrpyted_db_refresh_token != token:
            return None
        return payload
    except jwt.PyJWTError:
        return None


def refresh_access_token(refresh_token: str, expires_delta: Optional[timedelta] = None):
    """Create new access token using refresh token"""
    payload = verify_refresh_token(refresh_token)
    if not payload:
        return None

    # Get user email from payload
    email = payload.get("sub")
    if not email:
        return None

    # Verify user exists and is active
    ret = user_repository.get_user_tbl(email)
    if ret.get("code") != status.HTTP_200_OK:
        return None

    user = ret.get("data")
    user_db = UserDBPd(**user)

    if not user_db.is_active:
        return None

    # Create new access token
    new_access_token = create_access_token(data={"sub": user_db.email}, expires_delta=expires_delta)
    return new_access_token
