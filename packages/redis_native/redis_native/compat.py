# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""过渡期兼容：从 SPI 客户端取 redis-py 原生视图（Q3；Phase 4 收口移除）。

仅 builtin native provider 的客户端暴露 ``native_client()``；duck-typed
探测（getattr），不 import 具体实现类型——redis_native 对其他 Provider 的
客户端保持零类型耦合。
"""

from __future__ import annotations

from typing import Any

from redis_spi.exceptions import RedisConfigError


def as_native_client(client: Any) -> Any:
    """取客户端背后的真实 redis-py 客户端。

    供 common_utils.redis_manager 过渡委托与 agent-core 既有注入点使用。
    其他 Provider 抛 RedisConfigError（自描述：仅 native 支持）。
    """
    getter = getattr(client, "native_client", None)
    if callable(getter):
        return getter()
    raise RedisConfigError(
        f"Provider 客户端 {type(client).__name__} 不暴露 redis-py 原生视图"
        "（仅 builtin native provider 支持；本函数为过渡期兼容 API，"
        "Phase 4 业务全量迁移后移除）"
    )
