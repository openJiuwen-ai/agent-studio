# -*- coding: utf-8 -*-
"""customer_header — 客户 Header 改写规则引擎共享层

无宿主依赖的公共模块，由 model_service、agent_runtime、agent_builder 共用。
不得定义在 agent_runtime 后由 model_service 反向导入。
"""

from customer_header.context import ExecutionHeaderContext
from customer_header.engine import HeaderProjectionEngine, resolve_outbound_headers
from customer_header.profile import (
    CustomerHeaderProfile,
    get_profile,
    set_profile,
)
from customer_header.target import InternalTarget
from customer_header.types import HeaderProvenance, HeaderValue

__all__ = [
    "ExecutionHeaderContext",
    "HeaderProjectionEngine",
    "HeaderProvenance",
    "HeaderValue",
    "CustomerHeaderProfile",
    "InternalTarget",
    "get_profile",
    "set_profile",
    "resolve_outbound_headers",
]
