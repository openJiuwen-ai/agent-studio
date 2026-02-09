from fastapi import APIRouter, Depends, status, BackgroundTasks, Request
from fastapi.security.oauth2 import OAuth2PasswordRequestForm
from openjiuwen_studio.core.manager.email_manager.email_utils import EmailUtils
from openjiuwen_studio.core.manager.login_manager.auth_service import AuthService
from openjiuwen_studio.core.manager.login_manager.session_auth import oauth2_scheme
from openjiuwen_studio.schemas.common import ResponseModel
from openjiuwen_studio.core.common.language_thread_context import get_highest_priority_language
from openjiuwen_studio.schemas.user import (
    SendCodeRequest,
    RegisterRequest,
    ResetPasswordRequest,
    RefreshTokenRequest
)




auth_router = APIRouter()


@auth_router.post("/send-code", response_model=ResponseModel[dict])
async def send_code(req: SendCodeRequest, background_tasks: BackgroundTasks):
    """发送注册验证码"""
    code = await AuthService.get_registration_code(req.email)
    background_tasks.add_task(EmailUtils.send_verification_code, req.email, code)

    return ResponseModel(code=200, message="验证码已发送", data={})


@auth_router.post("/register", response_model=ResponseModel[dict])
async def register(req: RegisterRequest, request: Request):
    """用户注册"""
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
    result = await AuthService.register_user(req, language)

    return ResponseModel(
        code=status.HTTP_200_OK,
        message="注册成功",
        data=result
    )


@auth_router.post("/send-reset-code", response_model=ResponseModel[dict])
async def send_reset_code(req: SendCodeRequest, background_tasks: BackgroundTasks):
    """发送重置密码验证码"""
    code = await AuthService.get_reset_code(req.email)
    background_tasks.add_task(EmailUtils.send_reset_code, req.email, code)
 
    return ResponseModel(code=200, message="重置验证码已发送", data={})


@auth_router.post("/reset-password", response_model=ResponseModel[dict])
async def reset_password(req: ResetPasswordRequest):
    """重置密码"""
    await AuthService.reset_password(req)

    return ResponseModel(
        code=200,
        message="密码修改成功，请使用新密码重新登录",
        data={}
    )


@auth_router.get("/verify_access_token", response_model=ResponseModel[dict])
async def verify_access_token(token: str = Depends(oauth2_scheme)):
    result = await AuthService.verify_access_token(token)
    return ResponseModel(
        code=200,
        message="token 校验成功",
        data=result
    )


@auth_router.post("/login", response_model=ResponseModel[dict])
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """需要密码的登录"""
    result = await AuthService.login_user(form_data)
    return ResponseModel(code=200, message="登录成功", data=result)


@auth_router.post("/logout", response_model=ResponseModel[dict])
async def logout(request: Request):
    """用户登出接口，删除access token和refresh token（置空session_key和refresh_token）"""
    access_token = None
    # 获取access token
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        access_token = auth_header.split(" ", 1)[1]
    if not access_token:
        return ResponseModel(code=400, message="缺少token", data={})
    await AuthService.logout_service(access_token)
    return ResponseModel(code=200, message="退出成功", data={})


@auth_router.post("/refresh", response_model=ResponseModel[dict])
async def refresh_token(request: RefreshTokenRequest):
    """Refresh access token endpoint"""
    result = await AuthService.refresh_access_token_service(request.refreshToken)
    return ResponseModel(code=200, message="刷新成功", data=result)
