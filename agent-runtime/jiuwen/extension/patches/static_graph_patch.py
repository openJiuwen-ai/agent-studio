# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""静态图复用 patch 三件套（issue #1555 / spec 2026-10-12 §4）。

- Patch A：PregelGraph.compile 纯函数化（每次执行全新 Pregel/channels/
  checkpointer/Vertex，fresh vertex 包装共享 executable）；
- Patch B：CompiledGraph._invoke 入口 set workflow 级 session ContextVar；
- Patch C：BranchRouter.__call__ 解析链 组件级 → workflow 级 → self._session。

三件套**始终应用**（含 WORKFLOW_INSTANCE_REUSE_MODE=off）：off 模式下
每请求新建 Workflow 实例，patched 路径与现状严格等价（spec §4.4 与计划
"等价性论证"）。openjiuwen 结构变化时由 _structure_assertions 兜底：
断言失败 → 不应用补丁 + STATIC_GRAPH_DOWNGRADED=True + ERROR 日志，
实例缓存据此强制关闭（即使配置为 static_graph）。

本模块不依赖 openjiuwen 的版本号（git develop 依赖无 pin），结构断言
比版本检查可靠。上游合入等价修复后，按 patches/ 惯例移除本补丁。
"""
from __future__ import annotations

import inspect

from openjiuwen.core.common.logging import workflow_logger

from jiuwen.extension.workflow import execution_session_ctx as _session_ctx

_STATIC_GRAPH_PATCH_APPLIED = False
STATIC_GRAPH_DOWNGRADED = False


def _structure_assertions() -> list:
    """openjiuwen 结构断言（spec §7.2）。返回失败消息列表，空 = 全部通过。

    全部经 inspect 源码/签名检查——不在 import 期实例化引擎对象
    （Vertex() 会创建 asyncio.Future，import 期无事件循环）。

    引擎导入（含 workflow_sub_stream_patch）全部包在 try/except 中：
    导入失败（openjiuwen 循环 import 未被打断、上游模块/符号改名等）记为
    断言失败并跳过对应断言组——本函数永不抛 ImportError，调用方据此走
    降级路径（spec §7.2：断言失败必须降级而非抛异常）。
    """
    failures = []

    # A1/A2: PregelGraph 源码模式——Patch A 的改写基础
    try:
        from openjiuwen.core.graph.graph import PregelGraph
    except (ImportError, OSError) as e:
        failures.append(f"引擎导入失败（视为断言失败，自动降级）: {e}")
        PregelGraph = None
    if PregelGraph is not None:
        compile_fn = getattr(PregelGraph, "compile", None)
        if compile_fn is None:
            failures.append("PregelGraph.compile 不存在（结构断言失败，自动降级）")
        else:
            try:
                compile_src = inspect.getsource(compile_fn)
            except (OSError, TypeError, ValueError) as e:
                failures.append(f"PregelGraph.compile 源码不可内省: {e}")
                compile_src = ""
            if "self.pregel is None" not in compile_src:
                failures.append(
                    "PregelGraph.compile 不再包含 'self.pregel is None' 分支（Patch A 基础失效）"
                )
            if "self._session" not in compile_src:
                failures.append("PregelGraph.compile 不再写/读 self._session（after_step 竞态改写点缺失）")

        # A2: _compile 读取 self.nodes——shadow-copy 方案的注入点
        compile_internal_fn = getattr(PregelGraph, "_compile", None)
        if compile_internal_fn is None:
            failures.append("PregelGraph._compile 不存在（结构断言失败，自动降级）")
        else:
            try:
                compile_internal_src = inspect.getsource(compile_internal_fn)
                if "self.nodes" not in compile_internal_src:
                    failures.append("PregelGraph._compile 不再读取 self.nodes（shadow 方案失效）")
            except (OSError, TypeError, ValueError) as e:
                failures.append(f"PregelGraph._compile 源码不可内省: {e}")

    # B1: Patch B 包装对象必须是 sub_stream 补丁版本（应用顺序断言）
    try:
        from openjiuwen.core.graph.graph import CompiledGraph
        from jiuwen.extension.patches import workflow_sub_stream_patch
    except (ImportError, OSError) as e:
        failures.append(f"引擎导入失败（视为断言失败，自动降级）: {e}")
        CompiledGraph = workflow_sub_stream_patch = None
    if CompiledGraph is not None and workflow_sub_stream_patch is not None:
        patched_invoke = getattr(
            workflow_sub_stream_patch, "_patched_compiled_invoke", None
        )
        current_invoke = getattr(CompiledGraph, "_invoke", None)
        if patched_invoke is None:
            failures.append(
                "workflow_sub_stream_patch._patched_compiled_invoke 不存在"
                "（结构断言失败，自动降级）"
            )
        elif current_invoke is None:
            failures.append("CompiledGraph._invoke 不存在（结构断言失败，自动降级）")
        elif current_invoke is not patched_invoke:
            failures.append(
                "CompiledGraph._invoke 不是 workflow_sub_stream_patch._patched_compiled_invoke"
                "（static_graph_patch 必须在 apply_workflow_sub_stream_patch 之后应用）"
            )

    # C1: BranchRouter.__call__ 以 self._session 解析——Patch C 的替换基础
    try:
        from openjiuwen.core.workflow.components.flow.branch_router import BranchRouter
    except (ImportError, OSError) as e:
        failures.append(f"引擎导入失败（视为断言失败，自动降级）: {e}")
        BranchRouter = None
    if BranchRouter is not None:
        call_fn = getattr(BranchRouter, "__call__", None)
        # 类上无 __call__ 时 getattr 回退到元类的 type.__call__（method-wrapper），
        # isfunction 区分"真实实现缺失"与元类回退——缺失即跳过该组断言。
        if call_fn is None or not inspect.isfunction(call_fn):
            failures.append("BranchRouter.__call__ 不存在（结构断言失败，自动降级）")
        else:
            try:
                call_src = inspect.getsource(call_fn)
                if "self._session" not in call_src:
                    failures.append("BranchRouter.__call__ 不再读取 self._session")
            except (OSError, TypeError, ValueError) as e:
                failures.append(f"BranchRouter.__call__ 源码不可内省: {e}")
        if not hasattr(BranchRouter, "set_session"):
            failures.append("BranchRouter.set_session 不存在")

    # D1: Vertex 实例属性与签名——fresh-vertex 包装依赖
    try:
        from openjiuwen.core.graph.vertex import Vertex
    except (ImportError, OSError) as e:
        failures.append(f"引擎导入失败（视为断言失败，自动降级）: {e}")
        Vertex = None
    if Vertex is not None:
        try:
            vertex_src = inspect.getsource(Vertex.__init__)
            for attr in ("_stream_done", "_call_count", "_stream_call_count"):
                if attr not in vertex_src:
                    failures.append(f"Vertex.__init__ 不再初始化 {attr}")
            params = tuple(inspect.signature(Vertex.__init__).parameters)
            if params != ("self", "node_id", "executable"):
                failures.append(f"Vertex.__init__ 签名变化: {params}（期望 (self, node_id, executable)）")
        except (OSError, TypeError, ValueError) as e:
            failures.append(f"Vertex 不可内省: {e}")

    return failures


def _wrap_compiled_invoke(prev_invoke):
    """Patch B：包装当前 CompiledGraph._invoke（已被 sub_stream 补丁替换的版本）。

    执行树根 set workflow 级 session，finally token 式 reset——嵌套子工作流
    的子 _invoke set 为子 session、返回后恢复父 session，与现状"子编译时
    set_session(子session)"语义一致（spec §4.2）。
    """

    async def _invoke_with_session_ctx(self, inputs, session, config=None):
        token = _session_ctx.set_workflow_session(session)
        try:
            return await prev_invoke(self, inputs, session, config)
        finally:
            _session_ctx.reset_workflow_session(token)

    return _invoke_with_session_ctx


def apply_static_graph_patch() -> bool:
    """幂等应用入口（Task 3/4/5 逐步填充三件套，Task 6 完成编排）。

    Returns:
        True = 本次应用；False = 已应用或断言失败降级。
    """
    global _STATIC_GRAPH_PATCH_APPLIED, STATIC_GRAPH_DOWNGRADED
    if _STATIC_GRAPH_PATCH_APPLIED:
        return False

    failures = _structure_assertions()
    if failures:
        STATIC_GRAPH_DOWNGRADED = True
        for msg in failures:
            workflow_logger.error(
                f"[static_graph_patch] 结构断言失败，自动降级（实例缓存强制关闭）: {msg}"
            )
        _STATIC_GRAPH_PATCH_APPLIED = True  # 降级也视为已处理，防重复告警
        return False

    # Task 4/5 在此填充：PregelGraph.compile / BranchRouter.__call__
    from openjiuwen.core.graph.graph import CompiledGraph

    CompiledGraph._invoke = _wrap_compiled_invoke(CompiledGraph._invoke)

    _STATIC_GRAPH_PATCH_APPLIED = True
    return True
