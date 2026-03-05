#!/usr/bin/python3.10
# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

import functools
import inspect
import json
import logging

from starlette.responses import StreamingResponse, JSONResponse

logger = logging.getLogger(__name__)

# 业务异常类型，其消息可安全返回给客户端
SAFE_EXCEPTION_TYPES = (ValueError, PermissionError)


def _is_safe_exception(exc: Exception) -> bool:
    """判断异常消息是否可以安全返回给客户端（业务异常或已知安全类型）"""
    return hasattr(exc, "status_code") or isinstance(exc, SAFE_EXCEPTION_TYPES)


def _get_safe_message(exc: Exception) -> str:
    """获取可安全返回给客户端的错误消息，内部异常仅记录日志并返回通用提示"""
    if _is_safe_exception(exc):
        return str(exc)
    logger.exception("Unhandled internal exception: %s", exc)
    return "Internal server error"


def handle_exceptions(response_model=JSONResponse):
    """
    通用异常装饰器
    - 同步函数的response_model不能是StreamingResponse，推荐使用默认数据类型或不传
    - 若被装饰函数返回类型是 StreamingResponse → 用 SSE 错误帧
    - 否则用 response_model 或 JSONResponse
    """
    def decorator(func):
        is_stream = inspect.signature(func).return_annotation is StreamingResponse
        if inspect.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                try:
                    result = await func(*args, **kwargs)
                    # 如果是StreamingResponse，需要处理生成器内部异常
                    if isinstance(result, StreamingResponse):
                        # 创建一个包装器来捕获生成器异常
                        async def error_catching_generator(original_gen):
                            try:
                                async for chunk in original_gen:
                                    yield chunk
                            except Exception as e:
                                # 将异常转换为SSE错误帧，不向客户端泄露内部异常详情
                                code = getattr(e, "code", getattr(e, "status_code", 500))
                                msg = _get_safe_message(e)
                                error_data = {
                                    "error": True,
                                    "code": code,
                                    "message": msg
                                }
                                yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"

                        # 包装原始body_iterator
                        wrapped_gen = error_catching_generator(result.body_iterator)

                        # 返回新的StreamingResponse
                        return StreamingResponse(
                            wrapped_gen,
                            media_type=result.media_type,
                            headers=result.headers,
                            status_code=result.status_code
                        )

                    return result
                except Exception as e:
                    return _build_error(e, is_stream, response_model)
            return async_wrapper

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                return _build_error(e, is_stream, response_model)
        return sync_wrapper
    return decorator


def _build_error(exc, is_stream: bool, response_model):
    code = getattr(exc, "status_code", 500)
    msg = _get_safe_message(exc)

    if is_stream:
        # SSE 错误帧
        data = f"data: {json.dumps({'code': code, 'msg': msg})}\n\n"
        return StreamingResponse(iter([data]), media_type="text/event-stream")

    # 普通 JSON
    if response_model is JSONResponse:
        return JSONResponse(status_code=code, content={"code": code, "msg": msg})

    # 检查response_model是否有code和msg字段（用于错误响应）
    try:
        # 尝试创建带有code和msg字段的响应
        return response_model(code=code, msg=msg)
    except (TypeError, ValueError):
        # 如果失败，说明这不是一个错误响应模型，返回标准JSON错误
        return JSONResponse(status_code=code, content={"code": code, "msg": msg})
