# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""COM-03 §7.2 第 2 点：Runtime 未处理异常的共享日志与标准错误响应（无 app 依赖）。

供 ``RequestContextMiddleware`` 在 try 内、token 仍有效时捕获下游未处理
异常后调用：此时 ``_request_ctx`` 与 agent-core trace 仍是本请求值，
LogRecord 工厂注入的固定外层 ``request_id/trace_id/execution_id/
conversation_id`` 正确；若任由异常传播到外层 ServerErrorMiddleware 的
handler，finally 已 reset，固定字段会变空。

COM-03：从 COM-05 兼容 ``{error:{code,message}}`` 构建器改为调用
error_contract factory/builder，输出 ``openjiuwen.12100004`` 标准五字段；
仍保持在 token reset 前记录最终责任日志。

SYNC-01 P5-R3 落地（2026-09-21）：旧分支 COM-03 此函数用 error_factory
（from_internal/build_json_response → openjiuwen.12100004 canonical8）。
sync_01 P3.2 时 COM-03 error_contract 尚未迁入，故此处用裸 JSONResponse
格式延后（规划 L148 S3）。P5-R3 已迁入 error_contract/（Step 0）+ 本函数，
升级为 canonical8 五字段。机制（token 有效期内收口 + 固定字段正确）不变，
仅响应契约格式从裸格式升级为 canonical8；OTel/IR 缓存等 sync_01 新业务在
middleware 层（本函数无 app 依赖，不受影响）。

server.py 的 generic Exception handler 保留为 Middleware 自身建立失败或
reset 编程错误的最后兜底，不再承担正常路由未处理异常的关联日志。
"""

import logging

from starlette.requests import Request

from agent_runtime.error_contract import factory as error_factory

logger = logging.getLogger(__name__)


def build_unhandled_error_response(request: Request, exc: Exception):
    """token 有效期内记录未处理异常并构建 COM-03 标准错误响应。

    只读取 request.state 上已选定的关联 ID（不重新生成、不再次 set
    ContextVar）；响应体为 ``openjiuwen.12100004``（INTERNAL_ERROR, 500）
    标准五字段 + X-Request-Id Header。
    """
    exec_id = getattr(request.state, "execution_id", "unknown")
    req_id = getattr(request.state, "request_id", "unknown")
    # LOG014 抑制说明：本函数只由 RequestContextMiddleware 的 ``except``
    # 分支调用（token 有效期内收口未处理异常），exc_info 取到的始终是
    # 正在处理的当前异常，不会误取调用线程上下文中的无关异常。
    logger.error(
        f"Unhandled exception: {type(exc).__name__}: {exc}, "
        f"execution_id={exec_id}, request_id={req_id}",
        exc_info=True,  # noqa: LOG014 — 见上方抑制说明（仅 except 内调用）
    )
    language = request.headers.get("x-language", "zh-cn") if request else "zh-cn"
    # P5-R3 Phase 3 决策 A: from_plugin_exception(105015→12100006, 其余→12100004)
    descriptor = error_factory.from_plugin_exception(exc, req_id)
    return error_factory.build_json_response(descriptor, language)
