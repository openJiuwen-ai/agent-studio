#  Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.

from jiuwen.orchestration.common.runtime_env import (
    REQUEST_TIMEOUT_MCP,
    REQUEST_TIMEOUT_WORKFLOW,
)
from jiuwen.orchestration.flow.base_workflow import Node
from jiuwen.orchestration.flow.constant import ENVIRONMENT_VARIABLES
from jiuwen.orchestration.flow.enum import NodeType
from jiuwen.orchestration.flow.mcp_timeout import parse_mcp_time_out_seconds
from jiuwen.orchestration.flow.runtime_context import RuntimeContext

MS_P_S = 1000


def rewrite_timeout(runtime: RuntimeContext, invokable: Node, timeout: float) -> float:
    """
    Rewrite the timeout value based on the node type and environment variables.

    Args:
        runtime (RuntimeContext): The runtime context containing environment variables.
        invokable (Node): The node for which the timeout is being set.
        timeout (float): The default timeout value in seconds.

    Returns:
        float: The rewritten timeout value in seconds. If conditions are not met, the default timeout is returned.
    """

    # 如果节点类型不是 MCP 或 SUB_WORKFLOW，直接返回默认超时时间
    if invokable.type not in {NodeType.MCP.value, NodeType.SUB_WORKFLOW.value}:
        return timeout

    # MCP 节点：即使 env 为 None，也要应用 MCP_TIME_OUT_SECONDS 兜底上限
    if invokable.type == NodeType.MCP.value:
        env = runtime.get(ENVIRONMENT_VARIABLES)
        if env is None:
            return _get_mcp_timeout({}, REQUEST_TIMEOUT_MCP, timeout)
        return _get_mcp_timeout(env, REQUEST_TIMEOUT_MCP, timeout)

    # SUB_WORKFLOW 节点
    env = runtime.get(ENVIRONMENT_VARIABLES)
    if env is None:
        return timeout
    return _get_timeout(env, REQUEST_TIMEOUT_WORKFLOW, timeout)


def _get_timeout(env: dict, key: str, timeout: float) -> float:
    val = env.get(key)
    if val is None or not isinstance(val, int):
        return timeout

    # 返回转换后的超时时间（毫秒转秒）
    new_timeout = val / MS_P_S
    return max(new_timeout, timeout)


def _get_mcp_timeout(env: dict, key: str, timeout: float) -> float:
    """MCP 节点超时：节点配置超时与环境变量超时取小，再以 MCP_TIME_OUT_SECONDS 兜底取小。

    Args:
        env: 环境变量字典。
        key: 环境变量中保存请求超时的键。
        timeout: 节点 exception_config 配置的超时时间（秒）。

    Returns:
        最终超时时间（秒）。三者取小：节点超时、keep-alive 超时、MCP_TIME_OUT_SECONDS 兜底。
    """
    # MCP_TIME_OUT_SECONDS 作为兜底上限
    mcp_cap = parse_mcp_time_out_seconds()

    candidates = [mcp_cap]

    # 节点配置超时（正值才参与取小）
    if timeout > 0:
        candidates.append(timeout)

    # keep-alive 超时（毫秒转秒，正值才参与取小）
    val = env.get(key)
    if val is not None and isinstance(val, int) and val > 0:
        candidates.append(val / MS_P_S)

    return min(candidates)
