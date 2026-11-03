# Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
"""SUT-01 CD-018 (B2) §6.2: 路由全集快照校验。

加载 fixtures/b2_route_inventory.json，对照 live Flask url_map + FastAPI app.routes：
- 公开 Flask 路由（prompt/mmapo）不得丢失/被未经登记改动；
- 每个公开 Flask 路由的直连路径须被 dispatcher 覆盖（normalize → /flask 前缀）；
- /static 归 auto-static，dispatcher 不接管；
- FastAPI 公开路由集合稳定。

路由增删会令本测试失败 → 提示更新 fixture（§6.2"修改前后清单差异仅允许已批准变化"）。
"""
import json
import os

from agent_builder.serve.common.flask_route_dispatch import normalize_registered_flask_path

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "b2_route_inventory.json")


def _load():
    with open(FIXTURE, encoding="utf-8") as f:
        return json.load(f)


def _live_flask_rules():
    from agent_builder.app import app as flask_app
    out = []
    for r in flask_app.url_map.iter_rules():
        methods = sorted(m for m in (r.methods or set()) if m not in ("HEAD", "OPTIONS"))
        out.append({"rule": r.rule, "methods": methods, "endpoint": r.endpoint})
    return out


def _live_fastapi_route_methods():
    """返回 {(path, tuple(sorted(methods)))}——含 method，捕获 method 漂移（P1-2）。"""
    from agent_builder.serve.server_fastapi import app as fa_app
    out = set()

    def walk(routes):
        for rt in routes:
            methods = getattr(rt, "methods", None)
            p = getattr(rt, "path", None)
            if p is not None and methods is not None:
                out.add((p, tuple(sorted(methods))))
            if hasattr(rt, "routes"):
                walk(rt.routes)
            orig = getattr(rt, "original_router", None)
            if orig is not None:
                walk(getattr(orig, "routes", []))

    walk(fa_app.routes)
    return out


def _flask_public_signature_set(routes):
    """(rule, endpoint, tuple(sorted(methods))) 复合键——不折叠同路径不同 method
    （如 .../jobs/<job_id> 的 GET + DELETE 两个 endpoint，P1-1）。"""
    return {
        (r["rule"], r["endpoint"], tuple(sorted(r["methods"])))
        for r in routes
        if r["rule"].startswith("/flask/v1/")
    }


def test_flask_public_routes_match_snapshot():
    """公开 Flask 路由三元组集合须与 fixture 一致。

    同路径不同 method（GET/DELETE）不会被折叠——任一登记删除都会失败（P1-1）。
    """
    snap_routes = [r for r in _load()["flask_url_map"] if r["class"].startswith("public")]
    snap = {
        (r["rule"], r["endpoint"], tuple(sorted(r["methods"])))
        for r in snap_routes
    }
    live = _flask_public_signature_set(_live_flask_rules())
    assert snap == live, (
        f"Flask public (rule,endpoint,methods) set drifted; "
        f"missing_in_live={snap-live} new_in_live={live-snap}; "
        f"update fixtures/b2_route_inventory.json if change is approved")


def test_flask_dual_method_paths_have_both_registrations():
    """P1-1 反例：同名路径同时登记 GET + DELETE 两个 endpoint。

    复合键比较须捕获任一丢失——证明字典折叠不会让单边删除通过。
    """
    live = _live_flask_rules()
    for path in (
        "/flask/v1/prompt/templates_optimization/jobs/<job_id>",
        "/flask/v1/MMprompt/templates_optimization/jobs/<job_id>",
    ):
        entries = [r for r in live if r["rule"] == path]
        method_sets = {tuple(sorted(r["methods"])) for r in entries}
        endpoints = {r["endpoint"] for r in entries}
        assert ("GET",) in method_sets, f"{path} missing GET registration"
        assert ("DELETE",) in method_sets, f"{path} missing DELETE registration"
        assert len(endpoints) == 2, f"{path} should have 2 endpoints (GET+DELETE), got {endpoints}"


def test_every_public_flask_route_covered_by_dispatcher():
    """每个公开 Flask 路由的直连路径（去 /flask 前缀）须被 dispatcher 覆盖。"""
    live = [r for r in _live_flask_rules() if r["rule"].startswith("/flask/v1/")]
    assert live, "no public Flask routes found"
    for r in live:
        direct = r["rule"][len("/flask"):]  # /flask/v1/prompt/build → /v1/prompt/build
        # 对带 <param> 的规则，用前缀（dispatcher 用 startswith 匹配前缀）
        target = normalize_registered_flask_path(direct)
        assert target is not None, (
            f"public Flask route {r['rule']} (direct {direct}) not covered by dispatcher")


def test_static_route_classified_and_excluded():
    """/static 为 auto-static，dispatcher 不接管（转 FastAPI）。"""
    snap_static = [r for r in _load()["flask_url_map"] if r["class"] == "auto-static"]
    assert any(r["rule"].startswith("/static") for r in snap_static)
    assert normalize_registered_flask_path("/static/foo.js") is None, \
        "/static must NOT be dispatched to Flask (auto rule, non-public)"


def test_fastapi_route_set_stable():
    """FastAPI (path, methods) 集合须与 fixture 一致——捕获 method 变化（P1-2）。"""
    snap = {(r["path"], tuple(r["methods"])) for r in _load()["fastapi_routes"]}
    live = _live_fastapi_route_methods()
    assert snap == live, (
        f"FastAPI (path,methods) set drifted; "
        f"missing={snap-live} new={live-snap}; update fixture if approved")


def test_no_root_catch_all_mount():
    """root mount catch-all 已移除（dispatcher 接管）。"""
    from agent_builder.serve.server_fastapi import app as fa_app
    mounts = [r for r in fa_app.routes if getattr(r, "path", None) in ("/", "")]
    assert mounts == [], f"root catch-all mount should be removed, got {mounts}"
