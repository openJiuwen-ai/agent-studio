# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""环境变量加载工具。

逻辑已下沉至共享包 ``common_utils.env_variables_loader``（agent_runtime 与 agent_builder
共用同一实现，避免两份加载逻辑漂移）。本模块 re-export 保持历史 import 路径
``agent_runtime.common.env_variables_loader`` 向后兼容（app_run 等仍按此路径 import）。

env_vars 由工作流试运行入口（``app_run._execute_workflow_run`` / ``_execute_agent_run``）
按 ``environment_id`` 从 Redis 加载，写入 ``_request_ctx.env_variables``，供
``StudioModelClient`` 解析 apiUrl 中的 ``${_env.plugin_url_params.VAR}`` 占位符（跨环境
迁移的字面量 apiUrl），亦供 openjiuwen ``get_by_schema`` 解析 IR 模板字段里的同名占位符。
"""

from common_utils.env_variables_loader import (  # noqa: F401
    load_environment_variables,
    _SECRET_ENV_KEYS_KEY,
)

__all__ = ["load_environment_variables", "_SECRET_ENV_KEYS_KEY"]
