import random
import string
from typing import Any, Dict
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security.oauth2 import OAuth2PasswordRequestForm
from openjiuwen.core.common.logging import logger

from openjiuwen_studio.core.config import settings
from openjiuwen_studio.core.common.language_thread_context import get_highest_priority_language
from openjiuwen_studio.core.database import milliseconds
from openjiuwen_studio.core.manager.login_manager.pre_installed import pre_install
from openjiuwen_studio.core.manager.login_manager.session_auth import *
from openjiuwen_studio.core.manager.login_manager.session_auth import (create_access_token,
                                                         create_refresh_token,
                                                         refresh_access_token,
                                                         verify_refresh_token)
from openjiuwen_studio.core.manager.login_manager.user import create_user_db
from openjiuwen_studio.core.manager.repositories.user_repository import user_repository
from openjiuwen_studio.core.manager.model_manager.utils import SecurityUtils
from openjiuwen_studio.core.manager.login_manager.user import get_user_email
from openjiuwen_studio.core.manager.login_manager.security_manager import SecurityManager
from openjiuwen_studio.routers.users import create_user_response, get_current_user

from openjiuwen_studio.schemas.common import ResponseModel
from openjiuwen_studio.schemas.space import SpaceDBPd
from openjiuwen_studio.schemas.user import RefreshTokenRequest, RoleType, UserDBPd

auth_router = APIRouter()
security_utils = SecurityUtils()


def create_space_db(user_db: UserDBPd) -> SpaceDBPd:
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


@auth_router.post("/login")
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    """
    登录接口：如果用户名存在则直接登录，不存在则自动注册
    不需要密码验证
    """
    try:
        SecurityManager.login_rate_limit(request.client.host)
        username = form_data.username
        logger.info(f"username: {username}")

        # 检查用户是否存在并获取用户数据
        ret = user_repository.get_user_tbl(email=username)
        logger.info(f"ret: {ret}")

        accept_language = request.headers.get("accept-language", "")
        language = "zh"
        
        langs = get_highest_priority_language(accept_language)
        if langs:
            primary = langs[0]
            if primary.startswith("en"):
                language = "en"
            elif primary.startswith("zh"):
                language = "zh"
            else:
                language = "zh"

        # 如果用户不存在，则调用register流程
        if ret["code"] != status.HTTP_200_OK:
            # 用户不存在，自动注册
            return await register_internal(username, language, request.client.host)

        # 用户存在，直接登录（不需要密码验证）
        user_data = ret.get("data")
        if not user_data:
            # 如果data为空，也当作用户不存在处理
            return await register_internal(username, language, request.client.host)

        logger.info(f"user_data: {user_data}")

        user_db = UserDBPd(**user_data)

        # Create access token
        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
        access_token = create_access_token(
            data={"sub": user_db.email},
            expires_delta=access_token_expires
        )

        # Create refresh token
        refresh_token_ = create_refresh_token(data={"sub": user_db.email})

        # Update session key in database
        encrypted_access_token = security_utils.encrypt_api_key(access_token)
        user_repository.update_session_key(user_db.email, encrypted_access_token)

        user_response = create_user_response(user_db, False)
        return {
            "access_token": access_token,
            "refresh_token": refresh_token_,
            "token_type": "bearer",
            "user": user_response.dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login process failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Login process failed")


async def register_internal(username: str, language: str = "zh", host: str = ""):
    """
    内部注册函数：创建新用户和空间
    不需要密码，使用空密码或默认密码
    """
    try:
        SecurityManager.register_rate_limit(host)
        # 检查用户是否已存在（双重检查）
        ret = user_repository.find_user_tbl(email=username)
        if ret["code"] == status.HTTP_500_INTERNAL_SERVER_ERROR:
            raise HTTPException(status_code=ret["code"], detail="DB ERROR：failed to find user")
        if ret["code"] == status.HTTP_200_OK:
            # 用户已存在，直接登录
            user_data = ret["data"]
            user_db = UserDBPd(**user_data)

            # Create access token
            access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
            access_token = create_access_token(
                data={"sub": user_db.email},
                expires_delta=access_token_expires
            )

            # Create refresh token
            refresh_token_ = create_refresh_token(data={"sub": user_db.email})

            # Update session key in database
            encrypted_access_token = security_utils.encrypt_api_key(access_token)
            user_repository.update_session_key(user_db.email, encrypted_access_token)

            user_response = create_user_response(user_db, False)
            return {
                "access_token": access_token,
                "refresh_token": refresh_token_,
                "token_type": "bearer",
                "user": user_response.dict()
            }

        # 创建新用户（不需要密码，使用空字符串作为默认密码）
        default_password = ""
        user_db = create_user_db(username, default_password, RoleType.COMMON_USER, locale=language)

        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
        access_token = create_access_token(
            data={"sub": user_db.email},
            expires_delta=access_token_expires
        )
        refresh_token = create_refresh_token(data={"sub": user_db.email})
        encrypted_access_token = security_utils.encrypt_api_key(access_token)

        # 插 user 时直接带 session_key
        ret = user_repository.create_user_tbl(
            user_info={
                **user_db.dict(),
                "role_type": user_db.role_type.value,
                "session_key": encrypted_access_token,
            }
        )
        if ret["code"] != status.HTTP_200_OK:
            raise HTTPException(status_code=500, detail="Failed to sign up")

        space_db = create_space_db(user_db)
        ret = user_repository.create_space_tbl(
            space_db={**space_db.dict(), "role_type": space_db.role_type.value}
        )
        if ret["code"] != status.HTTP_200_OK:
            raise HTTPException(status_code=500, detail="Failed to sign up")

        pre_install(space_db.space_id, language)

        user_response = create_user_response(user_db, False)
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": user_response.dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration process failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@auth_router.post("/register", response_model=ResponseModel[dict])
async def register(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    """
    注册接口：创建新用户和空间（不需要密码）
    为了兼容性保留此接口，但实际逻辑已合并到login接口
    """
    try:
        username = form_data.username
        accept_language = request.headers.get("accept-language", "")
        language = "zh"
        
        langs = get_highest_priority_language(accept_language)
        if langs:
            primary = langs[0]
            if primary.startswith("en"):
                language = "en"
            elif primary.startswith("zh"):
                language = "zh"
            else:
                language = "zh"
        result = await register_internal(username, language)

        # 转换为ResponseModel格式以保持兼容性
        return ResponseModel(
            code=status.HTTP_200_OK,
            message="User registered successfully",
            data=result
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration process failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@auth_router.post("/logout", response_model=ResponseModel[dict])
async def logout(current_user: Dict[str, Any] = Depends(get_current_user)):
    """User logout endpoint"""
    # 清空用户的session_key
    user_repository.update_session_key(get_user_email(current_user), '')
    # In a real application, you might want to blacklist the token
    return ResponseModel(
        code=status.HTTP_200_OK,
        message="Logged out successfully",
        data={}
    )


@auth_router.post("/refresh", response_model=ResponseModel[dict])
async def refresh_token(request: RefreshTokenRequest):
    """Refresh access token endpoint"""
    try:
        new_access_token = refresh_access_token(request.refreshToken)

        if not new_access_token:
            raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

        # Update session key in database with new access token
        # Extract email from refresh token payload
        payload = verify_refresh_token(request.refreshToken)
        if payload and payload.get("sub"):
            encrypted_new_access_token = security_utils.encrypt_api_key(new_access_token)
            user_repository.update_session_key(payload["sub"], encrypted_new_access_token)

        return ResponseModel(
            code=status.HTTP_200_OK,
            message="Token refreshed successfully",
            data={
                "token": new_access_token,
                "token_type": "bearer"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to refresh token") from e
