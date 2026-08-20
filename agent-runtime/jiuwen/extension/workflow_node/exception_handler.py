# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

"""通过 CallbackFramework 注册异常恢复 handler。

不替换任何组件方法，不使用全局注册表，通过事件机制解耦恢复逻辑。
"""

from jiuwen.orchestration.flow.constant import (
    EXCEPTION_HANDLE_DEFAULT_OUTPUTS,
    EXCEPTION_HANDLE_ERROR_BRANCH,
    EXCEPTION_OUTPUT_RESULT,
    EXCEPTION_OUTPUT_RESULT_FAILED,
)
from openjiuwen.core.runner import Runner
from openjiuwen.core.runner.callback import AsyncCallbackFramework

# 不支持异常处理的组件类型
_NO_EXCEPTION_TYPES = frozenset({"jiuwen.loop", "jiuwen.exception"})
# 不支持 errorBranch 的组件类型
_NO_ERROR_BRANCH_TYPES = frozenset({"jiuwen.message", "jiuwen.card", "jiuwen.end"})

_HANDLER_REGISTERED = False


def _format_inner_exception(error) -> dict:
    """格式化异常信息为 isSuccess/errorBody 字典。"""
    from jiuwen.extension.workflow_node.utils import JiuWenBaseException

    if isinstance(error, JiuWenBaseException):
        error_body = {
            "errorMessage": error.message,
            "errorCode": error.error_code,
        }
    else:
        error_body = {
            "errorMessage": repr(error),
            "errorCode": -1,
        }
    return {
        "isSuccess": False,
        "errorBody": error_body,
    }


def _handle_default_outputs(error, exception_config, session) -> dict:
    """处理 defaultOutputs 恢复模式。

    等价于旧框架 BpmnWorkflow L962-968 的逻辑：
    1. 以组件输出 schema 为 base（保留所有预期输出字段）
    2. 合并用户配置的 defaultOutputs
    3. 追加异常信息
    """
    import copy

    base = copy.deepcopy(getattr(exception_config, "outputs_schema", {}) or {})
    default_outputs = exception_config.default_outputs

    def _merge_dicts(origin, default) -> dict:
        result = origin.copy()
        for key, value in default.items():
            if key in result:
                if isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = _merge_dicts(result[key], value)
                else:
                    result[key] = value
            else:
                # 保留 default 中 origin 没有的 key（MCP 等节点的 outputs_schema
                # 可能为空或结构与 default_outputs 不同）
                result[key] = value
        return result

    result = _merge_dicts(base, default_outputs)
    result.update(_format_inner_exception(error))
    return result


def _handle_error_branch(error) -> dict:
    """处理 errorBranch 恢复模式：返回 result='1' 标识异常路径。"""
    return {
        EXCEPTION_OUTPUT_RESULT: EXCEPTION_OUTPUT_RESULT_FAILED,
        "classificationId": -1,
        **_format_inner_exception(error),
    }


def register_error_recovery_handler():
    """注册全局异常恢复 handler 到 CallbackFramework。

    config 通过事件参数 exception_config 传入（来自 NodeSpec），不经全局查表。
    在工作流构建前调用一次即可（幂等）。
    """
    global _HANDLER_REGISTERED
    if _HANDLER_REGISTERED:
        return

    _fw: AsyncCallbackFramework = Runner.callback_framework
    if _fw is None:
        return

    @_fw.on("component_error_recovery", priority=100)
    async def handle_error_recovery(
        error, session, node_id, exception_config, **kwargs
    ):
        if exception_config is None:
            return None

        node_type = getattr(exception_config, "_node_type", "")
        if node_type in _NO_EXCEPTION_TYPES:
            return None

        ht = (exception_config.handle_type or "").lower()
        if ht == EXCEPTION_HANDLE_DEFAULT_OUTPUTS.lower():
            return _handle_default_outputs(error, exception_config, session)
        if ht == EXCEPTION_HANDLE_ERROR_BRANCH.lower():
            if node_type in _NO_ERROR_BRANCH_TYPES:
                return None
            return _handle_error_branch(error)
        return None

    _HANDLER_REGISTERED = True
