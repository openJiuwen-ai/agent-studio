#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

"""
请求级上下文 — 透传 HTTP 请求头和请求级参数到深层调用栈

使用 contextvars 实现协程安全的请求作用域存储。

改造：
- customer_headers: 客户 header 分仓（cust-*，不含 x-auth-token）
- platform_headers: 平台 header 分仓（X-Auth-Token 等）
- headers: 兼容字段，不含 customer_headers（防扩散到非目标调用）
"""

from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RequestContext:
    """请求级上下文 — 所有需要透传到深层的参数集中管理"""

    headers: dict = field(default_factory=dict)
    user_id: str = ""
    project_id: str = ""
    conversation_id: str = ""
    trace_id: str = ""
    execution_id: str = ""
    request_id: str = ""
    secret_env_keys: list = field(default_factory=list)
    # 当前节点引用了加密环境变量的字段名集合（由 on_* 入口设置，供模板渲染层读取）
    current_secret_field_names: dict = field(default_factory=dict)
    # 已加载的环境变量（load_environment_variables 产出；由请求入口写入，供
    # StudioModelClient 解析 apiUrl 中的 ${_env.plugin_url_params.VAR} 占位符）
    env_variables: dict = field(default_factory=dict)
    # 请求级全局变量（react 执行器写入：请求 inputs + 入参变量默认值；
    # 供 MCP wrapper 解析 input_parameters 的 {{inputs.*}} 动态凭证绑定。
    # 工作流链路不经此通道（FlowMcp 走 kwargs 独立通道），互不重叠）
    global_variables: dict = field(default_factory=dict)
    # 请求级记忆变量（react 执行器写入：IR metadata.memoryVariables 的
    # value/default_value 合并；供 MCP wrapper 解析 {{memory.*}} 绑定。
    # 旧编排链走 ContextEngine+global_variables，不经此通道）
    memory_variables: dict = field(default_factory=dict)
    # 请求级 MCP 动态凭证绑定模板（react 执行器写入：本次运行 agent 的 IR
    # configs.mcps[].inputParameters，按 server_id 键控。resource_mgr 的 MCP
    # client 按 server_id 进程级缓存且首个注册者的配置生效——跨 agent 共享
    # 的 client 其绑定模板可能来自别的 agent 的 IR，须以请求级为准）
    mcp_input_parameters: dict = field(default_factory=dict)
    # 内容审核引擎实例（由请求入口设置，供审核节点读取）
    moderation_engine: Any = None

    # ── 新增：客户 Header 分仓 ──
    # 客户 header（cust-userid、cust-token），白名单捕获，不含 x-auth-token
    customer_headers: dict = field(default_factory=dict)
    # 平台 header（X-Auth-Token 等），独立分仓
    platform_headers: dict = field(default_factory=dict)
    # 请求内 IR 加载 memo；仅由 HTTP 请求中间件初始化，避免跨请求复用。
    ir_load_cache: dict[str, Any] | None = None


_request_ctx: ContextVar[RequestContext] = ContextVar(
    "request_ctx", default=RequestContext()
)


# D-02（SYNC-01 P3.4）：W3C traceparent 第三方注入已移除（老分支无此函数；
# 模型/插件/MCP 出站不传播平台关联 Header）。若未来恢复第三方 W3C 传播，
# 须按 D-02 另行提出协议变更并经用户确认，不得静默恢复。

# B07：第三方发送边界保留的关联 Header 名（小写；匹配大小写不敏感）。
# 含预置/钩子重引入的伪造值——最终发送前一律剥离；认证/客户 Header 不动。
_RESERVED_CORRELATION_HEADERS = frozenset(
    {"x-request-id", "x-execution-id", "traceparent"}
)


def strip_correlation_headers(headers: dict) -> None:
    """D-02/B07：在最终第三方发送边界剥离平台保留关联 Header（原地，大小写不敏感）。

    模型/插件/MCP 出站 headers 在发送前调用；业务鉴权（X-Auth-*/Authorization）
    与已授权客户 Header（cust-*）不受影响。内部 Runtime/Builder 目标不适用本函数
    （P4 按"仅带白名单且覆盖伪造值"另验）。
    """
    for key in [k for k in headers if str(k).lower() in _RESERVED_CORRELATION_HEADERS]:
        headers.pop(key, None)


def set_request_global_variables(variables: dict) -> None:
    """写入请求级全局变量（react 执行器调用）。

    就地持有调用方 dict 引用（后续默认值合并对读取方可见）；
    非 dict 值忽略（保持现状）。
    """
    if isinstance(variables, dict):
        _request_ctx.get().global_variables = variables


def set_request_memory_variables(variables: dict) -> None:
    """写入请求级记忆变量（react 执行器调用）。

    值序=value > default_value（IR metadata.memoryVariables 合并产物）；
    非 dict 值忽略（保持现状）。
    """
    if isinstance(variables, dict):
        _request_ctx.get().memory_variables = variables


def get_request_memory_variables() -> dict:
    """请求级记忆变量（MCP {{memory.*}} 绑定值源）。

    未写入或非 dict 时返回空 dict——调用方按"未提供值"跳过绑定。
    """
    variables = getattr(_request_ctx.get(), "memory_variables", None)
    return variables if isinstance(variables, dict) else {}


def set_request_mcp_input_parameters(parameters: dict) -> None:
    """写入请求级 MCP 绑定模板（react 执行器调用，按 server_id 键控）。"""
    if isinstance(parameters, dict):
        _request_ctx.get().mcp_input_parameters = parameters


def get_request_mcp_input_parameters() -> dict:
    """请求级 MCP 绑定模板（react 执行器按本次 agent 的 IR 提供）。

    未写入或非 dict 时返回空 dict——wrapper 回退 client 自身配置。
    """
    parameters = getattr(_request_ctx.get(), "mcp_input_parameters", None)
    return parameters if isinstance(parameters, dict) else {}


def get_request_global_variables() -> dict:
    """请求级全局变量（react 执行器写入；MCP 动态凭证绑定值源）。

    未写入或非 dict 时返回空 dict——调用方按"未提供值"跳过绑定，
    不抛错不降级到其他来源。
    """
    variables = getattr(_request_ctx.get(), "global_variables", None)
    return variables if isinstance(variables, dict) else {}
