#  Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
"""MCP 超时解析工具，仅依赖 os/math/constant，避免循环导入。"""

import math
import os

from jiuwen.orchestration.flow.constant import DEFAULT_MCP_TIME_OUT_SECONDS


def parse_mcp_time_out_seconds() -> float:
    """读取 MCP_TIME_OUT_SECONDS 环境变量，缺失/非数字/非正值/非有限值时回退到默认值。"""
    raw = os.getenv("MCP_TIME_OUT_SECONDS")
    if raw is None:
        return DEFAULT_MCP_TIME_OUT_SECONDS
    try:
        value = float(raw)
    except ValueError:
        return DEFAULT_MCP_TIME_OUT_SECONDS
    if value <= 0 or not math.isfinite(value):
        return DEFAULT_MCP_TIME_OUT_SECONDS
    return value
