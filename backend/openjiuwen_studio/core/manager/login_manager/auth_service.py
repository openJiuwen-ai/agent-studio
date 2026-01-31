from datetime import timedelta

import jwt
from fastapi import HTTPException, status
from fastapi.security.oauth2 import OAuth2PasswordRequestForm
from jose import JWTError
from openjiuwen.core.common.logging import logger

from openjiuwen_studio.core.config import settings
from openjiuwen_studio.core.manager.login_manager import session_auth
from openjiuwen_studio.core.manager.login_manager.user import create_user_db
from openjiuwen_studio.core.manager.login_manager.security_manager import SecurityManager
from openjiuwen_studio.core.manager.repositories.user_repository import user_repository
from openjiuwen_studio.core.manager.model_manager.utils import SecurityUtils
from openjiuwen_studio.core.manager.login_manager.pre_installed import pre_install
from openjiuwen_studio.routers.auth import create_space_db
from openjiuwen_studio.routers.users import create_user_response
from openjiuwen_studio.schemas.user import RoleType, UserDBPd
from openjiuwen_studio.core.manager.login_manager.session_auth import (create_access_token,
                                                                       verify_refresh_token_strict,
                                                                       create_refresh_token)
from openjiuwen_studio.schemas.common import ResponseModel

security_utils = SecurityUtils()


class AuthService:
    """用户注册Service"""
    @staticmethod
    async def get_registration_code(email: str):
        """获取注册验证码"""
        if user_repository.find_user_tbl(email=email)["code"] == status.HTTP_200_OK:
            raise HTTPException(status_code=400, detail="该邮箱已注册")
        
        if SecurityManager.rate_limit(email, action_type="reg"):
            raise HTTPException(status_code=429, detail="操作过于频繁，请 60 秒后再试")
            
        return SecurityManager.generate_and_save_code(email, action_type="reg")

    @staticmethod
    async def register_user(req):
        """用户正式注册流程"""
        email = req.email
        if not SecurityManager.verify_code(email, req.code, action_type="reg"):
            raise HTTPException(status_code=400, detail="验证码错误或已失效")

        if user_repository.find_user_tbl(email=email)["code"] == status.HTTP_200_OK:
            raise HTTPException(status_code=400, detail="该邮箱已注册")

        try:
            user_db = create_user_db(email, req.password, RoleType.COMMON_USER)

            access_token = session_auth.create_access_token(
                data={"sub": user_db.email},
                expires_delta=timedelta(minutes=settings.new_access_token_expire_minutes)
            )
            refresh_token = session_auth.create_refresh_token(data={"sub": user_db.email})
            encrypted_access_token = security_utils.encrypt_api_key(access_token)
            encrypted_refresh_token = security_utils.encrypt_api_key(refresh_token)
            ret = user_repository.create_user_tbl(
                user_info={
                    **user_db.dict(),
                    "role_type": user_db.role_type.value,
                    "session_key": encrypted_access_token,
                }
            )
            user_repository.update_refresh_token(user_db.email, encrypted_refresh_token)
            space_pd = create_space_db(user_db)
            ret = user_repository.create_space_tbl(
                {**space_pd.dict(), "role_type": space_pd.role_type.value}
            )
            if ret["code"] != status.HTTP_200_OK:
                raise HTTPException(status_code=500, detail="Failed to sign up")

            pre_install(space_pd.space_id)

            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "user": create_user_response(user_db, False).dict()
            }
        except Exception as e:
            logger.error(f"Reg Service Error: {str(e)}")
            raise HTTPException(status_code=500, detail="注册流程异常") from e

    @staticmethod
    async def login_user(form_data: OAuth2PasswordRequestForm):
        """统一登录逻辑"""
        username = form_data.username
        password = form_data.password
        # 1. 校验用户名是否存在
        ret = user_repository.get_user_tbl(username)
        if ret.get("code") != status.HTTP_200_OK:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User does not exist",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user_data = ret.get("data")
        user = UserDBPd(**user_data)

        # 2. 检查用户是否被锁定
        lock_info = SecurityManager.get_lock_info(username)
        if lock_info["is_locked"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is locked due to too many failed login attempts. Please try again later.",
            )

        # 3. 校验密码
        if not session_auth.verify_password(password, user):
            # 记录失败次数
            SecurityManager.record_login_failure(username)
            remain = max(0, 5 - (lock_info["current_fail_count"] + 1))
            raise HTTPException(status_code=401, detail=f"密码错误，还剩 {remain} 次尝试机会")

        # 密码正确，清除错误计数和锁定
        SecurityManager.clear_auth_status(username)

        try:
            # 生成token并返回
            access_token = session_auth.create_access_token(
                data={"sub": user.email},
                expires_delta=timedelta(minutes=settings.access_token_expire_minutes)
            )
            refresh_token = session_auth.create_refresh_token(data={"sub": user.email})
            encrypted_access_token = security_utils.encrypt_api_key(access_token)
            encrypted_refresh_token = security_utils.encrypt_api_key(refresh_token)
            # 存储 access_token 和 refresh_token
            user_repository.update_session_key(user.email, encrypted_access_token)
            user_repository.update_refresh_token(user.email, encrypted_refresh_token)

            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "user": create_user_response(user, False).dict()
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Login process failed: {str(e)}")
            raise HTTPException(status_code=500, detail="Login process failed") from e

    @staticmethod
    async def refresh_access_token_service(refresh_token: str):
        try:
            # Update session key in database with new access token and refresh token
            payload = verify_refresh_token_strict(refresh_token)

            if not payload:
                raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

            # 生成新的 access token 和 refresh token
            new_access_token = create_access_token(data=payload)
            new_refresh_token = create_refresh_token(data=payload)

            if not new_access_token or not new_refresh_token:
                raise HTTPException(status_code=401, detail="Invalid or expired refresh token")


            if payload and payload.get("sub"):
                encrypted_new_access_token = security_utils.encrypt_api_key(new_access_token)
                encrypted_new_refresh_token = security_utils.encrypt_api_key(new_refresh_token)
                user_repository.update_session_key(payload["sub"], encrypted_new_access_token)
                user_repository.update_refresh_token(payload["sub"], encrypted_new_refresh_token)

            return {
                    "access_token": new_access_token,
                    "refresh_token": new_refresh_token,
                    "token_type": "bearer"
                }
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail="Failed to refresh token") from e

    @staticmethod
    async def logout_service(access_token: str):
        """登出服务：删除access token和refresh token（置空session_key和refresh_token）"""
        try:
            payload = jwt.decode(access_token, settings.secret_key, algorithms=[settings.algorithm])
            email = payload.get("sub")
        except Exception:
            email = None
        if email:
            user_repository.update_session_key(email, None)
            user_repository.update_refresh_token(email, None)
        return True


    @staticmethod
    async def get_reset_code(email: str):
        """获取重置密码验证码"""
        try:
            if user_repository.find_user_tbl(email=email)["code"] != status.HTTP_200_OK:
                raise HTTPException(status_code=400, detail="该邮箱未注册")
            
            if SecurityManager.rate_limit(email, action_type="reset"):
                raise HTTPException(status_code=429, detail="操作过于频繁，请 60 秒后再试")
                
            return SecurityManager.generate_and_save_code(email, action_type="reset")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Get Reset Code Error: {str(e)}")
            raise HTTPException(status_code=500, detail="获取验证码失败") from e

    @staticmethod
    async def reset_password(req):
        """找回/重置密码"""
        if not SecurityManager.verify_code(req.email, req.code, action_type="reset"):
            raise HTTPException(status_code=400, detail="验证码错误或已失效")

        hashed_pwd = session_auth.hash_password(req.new_password)
        user_repository.update_user_password(req.email, hashed_pwd)
        user_repository.update_session_key(req.email, "")
        SecurityManager.clear_auth_status(req.email)

    @staticmethod
    async def verify_access_token(token: str):
        """
        校验 AccessToken 有效性（核心逻辑）
        :param token: 待校验的 AccessToken
        :return: 解析后的用户数据（包含 sub 等字段）
        :raise: 校验失败时抛出对应异常
        """
        try:
            # 基础校验：解析 Token（自动校验 格式、签名、过期时间 exp）
            payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])

            # 提取核心用户标识
            user_id: str = payload.get("sub")
            if user_id is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token: Missing user identifier."
                )

            # 校验用户是否是否在锁定中
            lock_info = SecurityManager.get_lock_info(user_id)
            if lock_info["is_locked"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Invalid token: User locked.",
                )

            # 校验token是否还生效
            ret = user_repository.get_user_tbl(email=user_id)
            if ret.get("code") != status.HTTP_200_OK:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid user."
                )
            user = ret.get("data")
            access_token = user.get("session_key")

            if not access_token or security_utils.decrypt_api_key(access_token) != token:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token"
                )

            # 校验通过，返回解析后的用户数据
            return {
                "valid": True,
                "expiresAt": payload.get("exp")
            }

        except JWTError as e:
            if "expired" in str(e).lower():
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has expired: Please log in again."
                ) from e
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Invalid Token: Format error or signature verification failure（{str(e)}）"
                ) from e