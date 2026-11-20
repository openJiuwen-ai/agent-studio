# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""日志装配最早阶段可用的工具。

本模块只依赖标准库与 request_context（contextvars），不导入 agent-core / jiuwen 的
业务模块。因此可以在进程启动的最早阶段导入：先给 stdlib LogRecord 补上
request_id / execution_id，再用完整格式装配日志——否则那些字段缺失会让日志格式化
失败，启动期日志也会先落到 agent-core 默认配置（console + file，./logs/）的文件里。
"""

import logging

from agent_runtime.context.request_context import _request_ctx

_record_factory_installed = False


def install_request_context_log_record_factory() -> None:
    """给 stdlib LogRecord 补上 trace_id / execution_id / request_id / conversation_id。

    幂等：重复调用不会叠加工厂。
    """
    global _record_factory_installed
    if _record_factory_installed:
        return

    previous_factory = logging.getLogRecordFactory()

    def record_factory(*args, **kwargs):
        record = previous_factory(*args, **kwargs)
        ctx = _request_ctx.get()
        if not hasattr(record, "trace_id"):
            record.trace_id = ctx.trace_id
        if not hasattr(record, "execution_id"):
            record.execution_id = ctx.execution_id
        if not hasattr(record, "request_id"):
            record.request_id = ctx.request_id
        if not hasattr(record, "conversation_id"):
            record.conversation_id = ctx.conversation_id
        return record

    logging.setLogRecordFactory(record_factory)
    _record_factory_installed = True
