# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""COM-05: Runtime 会话来源声明式 matcher 测试（SYNC-01 P3.2 从旧分支移植）。

覆盖：8 条路径来源路由、3 条请求体来源路由、非会话留空、URL 解码、
以及与 FastAPI 实际注册路由（app.routes）的双向对账——新增会话路由
未登记时对账测试失败（规划 §3.4.5）。路由表已 R12 核验匹配 sync_01 真实
路由（web_run/orchestration/app_run/conversation_variable_api）。
"""

import pytest
from agent_runtime.context.conversation_source import (
    SOURCE_BODY,
    SOURCE_NONE,
    SOURCE_PATH,
    declared_route_entries,
    resolve_conversation_source,
)

# ------------------------------ 矩阵逐条 ------------------------------


@pytest.mark.parametrize(
    ("method", "path", "expected_cid"),
    [
        (
            "POST",
            "/v1/proj1/workflows/wf1/conversations/conv-1",
            "conv-1",
        ),
        (
            "POST",
            "/v1/proj1/agents/ag1/conversations/conv-2",
            "conv-2",
        ),
        (
            "POST",
            "/v1/proj1/workflows/wf1/conversations/conv-3/node_execute/node-9",
            "conv-3",
        ),
        (
            "POST",
            "/v1/workflows/chat/short1/conversations/conv-4",
            "conv-4",
        ),
        (
            "POST",
            "/v1/proj1/agents/ag1/conversations/conv-5/additional-questions",
            "conv-5",
        ),
        (
            "POST",
            "/v1/proj1/workflows/wf1/conversations/conv-6/additional-questions",
            "conv-6",
        ),
        (
            "GET",
            "/v1/proj1/agents/ag1/conversations/conv-7/variables",
            "conv-7",
        ),
        (
            "PUT",
            "/v1/proj1/agents/ag1/conversations/conv-8/variables/var-1",
            "conv-8",
        ),
    ],
)
def test_path_source_routes(method, path, expected_cid):
    source, cid = resolve_conversation_source(method, path)
    assert source == SOURCE_PATH
    assert cid == expected_cid


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("POST", "/v1/orchestration/ir/execute"),
        ("POST", "/v1/orchestration/ir/component/comp-1/execute"),
        ("DELETE", "/v1/orchestration/ir/execute"),
    ],
)
def test_body_source_routes(method, path):
    source, cid = resolve_conversation_source(method, path)
    assert source == SOURCE_BODY
    assert cid == ""  # body 来源的值由调用方从已解析 JSON 读取


# ------------------------------ 非会话与特殊路由 ------------------------------


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/v1/health"),
        ("POST", "/v1/inner-tools/document/create"),
        ("POST", "/v1/proj1/releases"),
        ("POST", "/v1/agents/chat/short1"),  # 查询参数路由：统一字段留空
        ("POST", "/internal/v1/kb/search"),
        ("GET", "/v1/proj1/agents/ag1/conversations/conv-x"),  # 未登记的 GET
    ],
)
def test_non_conversation_routes_return_none(method, path):
    source, cid = resolve_conversation_source(method, path)
    assert source == SOURCE_NONE
    assert cid == ""


def test_url_decoded_path_conversation_id():
    source, cid = resolve_conversation_source(
        "POST", "/v1/p/workflows/wf/conversations/conv%20with%20space"
    )
    assert source == SOURCE_PATH
    assert cid == "conv with space"


def test_segment_count_mismatch_returns_none():
    # 多一段或少一段都不匹配（防宽泛误识别）
    assert (
        resolve_conversation_source("POST", "/v1/p/wf/conversations/c/extra/seg")[0]
        == SOURCE_NONE
    )
    assert resolve_conversation_source("POST", "/v1/p/wf/conversations")[0] == (
        SOURCE_NONE
    )


# ------------------------------ app.routes 对账 ------------------------------


def _all_registered_routes():
    """提取 FastAPI app 实际注册的全部 (method, path) 模板。"""
    from agent_runtime.serve.server import app
    from fastapi.routing import APIRoute

    entries = set()
    for wrapper in app.routes:
        orig = getattr(wrapper, "original_router", None)
        if orig is None:
            # 直接 APIRoute（未经 router 包裹）—— sync_01 兜底
            if isinstance(wrapper, APIRoute):
                for m in wrapper.methods or ():
                    if m in ("GET", "POST", "PUT", "DELETE", "PATCH"):
                        entries.add((m, wrapper.path))
            continue
        for r in getattr(orig, "routes", []):
            if isinstance(r, APIRoute):
                for m in r.methods or ():
                    if m in ("GET", "POST", "PUT", "DELETE", "PATCH"):
                        entries.add((m, r.path))
    return entries


def test_reconciliation_every_conversation_path_route_is_declared():
    """app.routes 中每条路径含 {conversation_id} 的路由都在声明清单内。"""
    declared_path, _ = declared_route_entries()
    declared = {e for e in declared_path}
    registered = _all_registered_routes()
    for method, path in registered:
        if "{conversation_id}" in path:
            entry = f"{method} {path}"
            assert entry in declared, (
                f"路由 {entry} 含会话路径参数但未在 conversation_source 声明，"
                "请登记来源（规划 §3.4.5）"
            )


def test_reconciliation_every_declared_route_is_registered():
    """声明清单中每条路由都在 app.routes 中真实注册。"""
    declared_path, declared_body = declared_route_entries()
    registered = _all_registered_routes()
    for entry in (*declared_path, *declared_body):
        method, _, path = entry.partition(" ")
        assert (method, path) in registered, (
            f"声明路由 {entry} 未在 app.routes 中注册——清单与实际路由漂移"
        )


def test_reconciliation_no_body_route_leaks_conversation_path_param():
    """body 来源路由的模板不含 {conversation_id} 段。"""
    _, declared_body = declared_route_entries()
    for entry in declared_body:
        _, _, path = entry.partition(" ")
        assert "{conversation_id}" not in path
