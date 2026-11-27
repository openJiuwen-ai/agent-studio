# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Redis Provider 适配层启动装配（re-export 薄壳）。

实现已下沉至 common_utils.redis_provider_bootstrap（agent-builder 纳入 Provider
时移到两进程共享包），本模块保持 agent_runtime.serve.redis_bootstrap 既有
import 路径不变（server lifespan / 既有测试均经此处引用）。
"""

from common_utils.redis_provider_bootstrap import (  # noqa: F401 - re-export
    _SHARED_CONNECTION_FIELDS,
    build_provider_settings,
    init_redis_provider,
)

__all__ = [
    "build_provider_settings",
    "init_redis_provider",
    "_SHARED_CONNECTION_FIELDS",
]
