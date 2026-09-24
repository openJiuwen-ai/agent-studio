# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""COM-05: Runtime 会话来源声明式匹配器（纯函数，无副作用）。

BaseHTTPMiddleware 先于 Router 执行，``scope["route"]``/``path_params`` 尚未
填充，因此用声明式路由模板表匹配 (method, path)，提取 ``conversation_id``
的权威来源。来源分三类：

- ``path``: URL 路径 ``{conversation_id}`` 段（8 条路由）；
- ``body``: 直接编排/组件执行/删除实例的请求体 ``conversationId``（3 条）；
- ``none``: 非会话接口（含 ``/v1/agents/chat/{short_code}`` 查询参数路由——
  按规划不纳入统一字段）。

对账测试（``test_conversation_source.py``）与本表双向绑定：新增会话路由
未登记时测试失败。

SYNC-01 P3.2：从旧分支 debug_log_20260818 移植（DEF-03/COM-05）。路由表已
R12 核验匹配 sync_01 真实路由（web_run/orchestration/app_run/conversation_variable_api）。
"""

from urllib.parse import unquote

# "METHOD /path/template" — path 段含 {conversation_id} 的权威来源路由
_PATH_ROUTES = (
    "POST /v1/{project_id}/workflows/{workflow_id}/conversations/{conversation_id}",
    "POST /v1/{project_id}/agents/{agent_id}/conversations/{conversation_id}",
    (
        "POST /v1/{project_id}/workflows/{workflow_id}/conversations/"
        "{conversation_id}/node_execute/{node_id}"
    ),
    "POST /v1/workflows/chat/{short_code}/conversations/{conversation_id}",
    "POST /v1/{project_id}/conversations/{conversation_id}/cancel",
    (
        "POST /v1/{project_id}/agents/{agent_id}/conversations/"
        "{conversation_id}/additional-questions"
    ),
    (
        "POST /v1/{project_id}/workflows/{workflow_id}/conversations/"
        "{conversation_id}/additional-questions"
    ),
    "GET /v1/{project_id}/agents/{agent_id}/conversations/{conversation_id}/variables",
    (
        "PUT /v1/{project_id}/agents/{agent_id}/conversations/"
        "{conversation_id}/variables/{var_id}"
    ),
)

# 请求体 conversationId 为权威来源的路由（含 DELETE——middleware 原只读
# POST/PUT/PATCH，DELETE 需单独纳入 body 来源清单）
_BODY_ROUTES = (
    "POST /v1/orchestration/ir/execute",
    "POST /v1/orchestration/ir/component/{component_id}/execute",
    "DELETE /v1/orchestration/ir/execute",
)

SOURCE_NONE = "none"
SOURCE_PATH = "path"
SOURCE_BODY = "body"


def _match_template(template: str, path: str) -> dict | None:
    """段级匹配 URL 与模板；``{param}`` 段提取并 URL 解码，字面段须相等。"""
    t_parts = template.strip("/").split("/")
    p_parts = path.strip("/").split("/")
    if len(t_parts) != len(p_parts):
        return None
    params = {}
    for t, p in zip(t_parts, p_parts, strict=False):
        if len(t) >= 2 and t.startswith("{") and t.endswith("}"):
            params[t[1:-1]] = unquote(p)
        elif t != p:
            return None
    return params


def resolve_conversation_source(method: str, path: str) -> tuple[str, str]:
    """匹配 (method, path) 返回 (来源, 提取值)。

    path 来源返回 ``(SOURCE_PATH, conversation_id)``；body 来源返回
    ``(SOURCE_BODY, "")``（值由调用方从已解析的请求体 JSON 读取）；
    其余返回 ``(SOURCE_NONE, "")``。
    """
    for entry in _PATH_ROUTES:
        m, _, tmpl = entry.partition(" ")
        if m != method:
            continue
        params = _match_template(tmpl, path)
        if params is not None:
            return SOURCE_PATH, params.get("conversation_id", "")
    for entry in _BODY_ROUTES:
        m, _, tmpl = entry.partition(" ")
        if m != method:
            continue
        if _match_template(tmpl, path) is not None:
            return SOURCE_BODY, ""
    return SOURCE_NONE, ""


def declared_route_entries() -> tuple[tuple[str, ...], tuple[str, ...]]:
    """导出声明清单（供对账测试与 app.routes 双向核对）。"""
    return _PATH_ROUTES, _BODY_ROUTES
