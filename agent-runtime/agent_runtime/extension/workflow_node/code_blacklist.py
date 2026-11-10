# Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.

"""CODE_BLACK_LIST 环境变量解析（agent_runtime / jiuwen FlowCode 共用）。"""

from __future__ import annotations

import json
import os

from openjiuwen.core.common.exception.codes import StatusCode
from openjiuwen.core.common.exception.errors import build_error
from openjiuwen.core.common.logging import workflow_logger


def load_code_blacklist() -> list:
    """解析 CODE_BLACK_LIST 环境变量。

    os.environ.get(key, default) 在变量存在但值为空串时仍返回 ""，
    直接 json.loads("") 会抛 Expecting value: line 1 column 1 (char 0)。
    未设置/空串/空白 → 无黑名单（容错）；非法 JSON/非 list → fail-closed 抛错，
    避免配置写错时静默关闭安全黑名单。list 内非 str 项丢弃。
    """
    raw = (os.environ.get("CODE_BLACK_LIST") or "").strip()
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        workflow_logger.error(
            "CODE_BLACK_LIST is not valid JSON, reject code execution: %r", raw
        )
        raise build_error(
            StatusCode.WORKFLOW_COMPONENT_EXECUTION_ERROR,
            comp="flow_code",
            ability="invoke",
            reason=f"CODE_BLACK_LIST is not valid JSON: {e}",
            workflow="n/a",
        ) from e
    if not isinstance(parsed, list):
        workflow_logger.error(
            "CODE_BLACK_LIST must be a JSON list, got %s: %r",
            type(parsed).__name__,
            raw,
        )
        raise build_error(
            StatusCode.WORKFLOW_COMPONENT_EXECUTION_ERROR,
            comp="flow_code",
            ability="invoke",
            reason=(
                "CODE_BLACK_LIST must be a JSON list, "
                f"got {type(parsed).__name__}"
            ),
            workflow="n/a",
        )
    return [kw for kw in parsed if isinstance(kw, str)]
