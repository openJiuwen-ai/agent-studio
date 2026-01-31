import random
import secrets
import string

import jwt
from fastapi import HTTPException, Depends, status

from openjiuwen.core.common.logging import logger
from openjiuwen_studio.core.config import settings
from openjiuwen_studio.core.database import milliseconds
from openjiuwen_studio.core.manager.login_manager.session_auth import hash_password, oauth2_scheme
from openjiuwen_studio.core.manager.repositories.user_repository import user_repository
from openjiuwen_studio.schemas.space import SpaceDBPd
from openjiuwen_studio.schemas.user import UserDBPd, UserResponse, RoleType


def create_user_response(user_db: UserDBPd, include_session_key: bool) -> UserResponse:
    user_info_dict = user_db.model_dump(exclude={'password'})
    if not include_session_key:
        user_info_dict.pop('session_key', None)

    user_response = UserResponse(
        **user_info_dict,
        screen_name=user_db.username,
    )
    return user_response


def create_user_db(email: str, password: str, role_type: RoleType) -> UserDBPd:
    user_id = ''.join(secrets.choice(string.digits) for _ in range(8))
    name = email.split('@')[0]
    user_unique_name = email
    user_create_time = milliseconds()
    user_db = {
        "user_id_str": user_id,
        "username": name,
        "user_unique_name": user_unique_name,
        "email": email,
        "description": "",
        "avata_url": "",
        "role_type": role_type,
        "locale": "zh-CN",
        "password": hash_password(password),
        "user_create_time": user_create_time,
        "user_update_time": user_create_time,
        "is_active": True
    }
    user = UserDBPd(**user_db)
    return user


def create_space_db(user_db: UserDBPd) -> SpaceDBPd:
    """创建空间数据对象"""
    space_id = ''.join(random.sample(string.digits, 8))
    user_id_str = user_db.user_id_str
    creator_id_str = user_id_str
    spacename = "Personal Space"
    description = "This is your personal space"
    role_type = user_db.role_type
    current_time = milliseconds()

    space_db = {
        "space_id": space_id,
        "user_id_str": user_id_str,
        "creator_id_str": creator_id_str,
        "spacename": spacename,
        "description": description,
        "role_type": role_type,
        "space_create_time": current_time,
        "space_update_time": current_time,
    }
    space = SpaceDBPd(**space_db)
    return space


def verify_current_user(current_user: dict, user_id: str) -> dict:
    ret = current_user.get("code")
    if ret != status.HTTP_200_OK:
        raise HTTPException(status_code=ret, detail=current_user.get("message", "DB error"))
    # Users can only view their own profile, superusers can view any
    user_db = current_user.get("data")
    if user_db is None:
        raise HTTPException(status_code=400, detail="User data not found")
    if user_db["role_type"] != RoleType.SUPER_USER and user_db["user_id_str"] != user_id:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return user_db


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """Get current user from JWT token"""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials") from e

    ret = user_repository.get_user_tbl(email)
    if ret['code'] != status.HTTP_200_OK:
        return ret
    user = ret.get("data")
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    # 如果启用新认证系统，进行 session_key 验证
    if settings.enable_new_auth:
        db_session_key = user.get("session_key")
        # 检查是否为空 (处理登出、重置密码后的情况)
        if not db_session_key:
            raise HTTPException(status_code=401, detail="Session expired")
    user_db = UserDBPd(**user)

    return {"code": status.HTTP_200_OK,
            "message": "Get dl successfully.",
            "data": user_db.model_dump()}


def get_user_id(current_user: dict) -> str:
    """Get current user id from JWT token"""
    try:
        ret = current_user.get("code")
        if ret != status.HTTP_200_OK:
            raise HTTPException(status_code=ret, detail=current_user.get("message", "get user error"))

        user_db = current_user.get("data")
        if user_db is None:
            raise HTTPException(status_code=400, detail="User data not found")
        return user_db["user_id_str"]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error") from e
