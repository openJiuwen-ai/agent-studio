# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""COM-05 §3.5: Builder 未处理异常的共享日志与错误响应（无 app 依赖）。

供 ``establish_inbound_context`` 在 try 内、token 仍有效时捕获下游未处理异常
后调用：此时 ``_request_ctx`` 与 agent-core trace 仍是本请求值，LogRecord 工厂
注入的固定外层 ``request_id/trace_id`` 正确；若任由异常传播到外层 handler，
finally 已 reset，固定字段会变空。

SYNC-01 P5-R3b（2026-09-22）：旧分支 COM-05 此函数用 COM-03 error_factory
（from_internal/build_json_response → canonical8 五字段 openjiuwen.13100004）。
sync_01 P3.2 时 COM-03 error_contract 尚未迁入，故用裸 JSONResponse 格式延后
（规划 L148 S3）。P5-R3b 已迁入 error_contract/，本函数升级为 canonical8
五字段；机制（token 有效期内收口 + 固定字段正确）不变，仅响应契约格式
从裸 ``{error:{code,message,trace_id}}`` 升级为 canonical8。

server_fastapi 的 generic Exception handler 保留为 Middleware 自身建立失败或
reset 编程错误的最后兜底，不再承担正常路由未处理异常的关联日志。
"""

from starlette.requests import Request

from agent_builder.common.error_contract import factory as error_factory
from agent_builder.common.logging.base import logger


def build_unhandled_error_response(request: Request, exc: Exception):
    """token 有效期内记录未处理异常并构建 COM-03 标准错误响应。

    只读取 request.state 上已选定的关联 ID（不重新生成、不再次 set
    ContextVar）；响应体为 ``openjiuwen.13100004``（INTERNAL_ERROR, 500）
    标准五字段 + X-Request-Id Header。

    SYNC-01 P5-R3b（2026-09-22）：旧分支 COM-03 此函数用 error_factory
    （from_internal/build_json_response → canonical8 五字段）。sync_01 P3.2
    时 COM-03 error_contract 尚未迁入，故此处用裸 JSONResponse 格式延后。
    P5-R3b 已迁入 error_contract/，本函数升级为 canonical8 五字段；机制
    （token 有效期内收口 + 固定字段正确）不变，仅响应契约格式升级。
    """
    trace_id = getattr(request.state, "trace_id", "")
    req_id = getattr(request.state, "request_id", "")
    # LOG014 抑制说明：本函数只由 establish_inbound_context 的 except 分支调用
    # （token 有效期内收口未处理异常），exc_info 取到的始终是正在处理的当前异常。
    logger.error(
        f"Unhandled exception: type={type(exc).__name__}, "
        f"trace_id={trace_id}, request_id={req_id}",
        exc_info=True,  # noqa: LOG014 — 见上方抑制说明（仅 except 内调用）
    )
    language = request.headers.get("x-language", "zh-cn") if request else "zh-cn"
    descriptor = error_factory.from_internal(exc, req_id or None)
    return error_factory.build_json_response(descriptor, language)
