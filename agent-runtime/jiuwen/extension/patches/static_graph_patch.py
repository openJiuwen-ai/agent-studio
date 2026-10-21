# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""静态图复用 patch（仅剩 Patch B，issue #1555 / spec 2026-10-12 §4）。

openjiuwen 自 `fix/0.1.17.post2-compile-reentrant`（commit f58a5e29）起，
引擎侧已原生提供"编译纯函数化 + 执行期状态 ContextVar 化"：

- ``PregelGraph.compile`` 每次执行全新 Vertex 壳 / Pregel / channels /
  checkpointer，after_step 捕获 session 参数（原 Patch A）；
- ``CompiledGraph._invoke`` 入口 set workflow 级 session ContextVar；
- ``BranchRouter.__call__`` 解析链 组件级 → workflow 级 → ``self._session``
  （原 Patch C，且带 owner 归属校验）；
- ``BranchComponent.invoke`` / ``IntentDetectionExecutable.invoke`` 补写
  组件级 session（原 Patch D）；
- ``AdvancedLoopComponent`` / ``PostLoopBody`` 执行期状态会话化。

原 Patch A/C/D 与循环执行期状态会话化补丁随之移除，本模块只保留 Patch B。

**Patch B 为何仍必须保留**：``workflow_sub_stream_patch`` 整体替换了
``CompiledGraph._invoke``（自带 checkpoint session / 子工作流 aggregate 逻辑），
引擎写在新版 ``_invoke`` 里的 ``set_workflow_session`` 不会执行。缺了这一步，
``resolve_routing_session`` 读不到 workflow 级值，只能退回共享的
``self._session``——并发执行下正是竞态根源。

降级安全网（spec §7.2 语义保留，探测目标随引擎自持而变）：启动时探测引擎
是否真的带上了 reentrant compile。缺失（例如依赖被回退到未含修复的
``@develop``）→ 不应用补丁 + ``STATIC_GRAPH_DOWNGRADED=True`` + ERROR 日志，
实例缓存据此强制关闭（回落直建路径）。不做版本号检查——依赖是 git 分支
无 pin，能力探测比版本检查可靠。
"""
from __future__ import annotations

import inspect
from typing import Any

# 打断 openjiuwen 循环 import（graph.py → vertex.py → workflow.components.base
# → workflow/__init__ → workflow.py:34 回引 graph.py）。缺此先行导入时，本模块
# 若为进程内首个触碰 openjiuwen.core.graph.graph 的模块会 ImportError（与
# tests/unit_tests/extension/patches/test_static_graph_patch.py 顶部同理）。
import openjiuwen.core.workflow  # noqa: F401  # pylint: disable=unused-import
from openjiuwen.core.common.logging import workflow_logger
from openjiuwen.core.graph.graph import CompiledGraph
from openjiuwen.core.session import execution_session_ctx as _engine_session_ctx

_STATIC_GRAPH_PATCH_APPLIED = False
STATIC_GRAPH_DOWNGRADED = False

# 替换前保存的原版引用（patches/ 惯例，nested_branch_barrier_patch 等同理）：
# 供测试取"未打补丁"基线（接线后 CompiledGraph._invoke 进程内恒为 patched，
# 无法再经类属性取得原版）。注意捕获的是 sub_stream 补丁版（本补丁替换前值，
# B1 应用顺序语义），非引擎出厂原版。
# 仅在首次 apply 时捕获（None 判断）——测试复位 flag 重放 apply 时类属性
# 可能已是 patched 版本，覆盖会把 patched 误当原版。
_original_compiled_invoke: Any = None


def _unwrap_wrapper_chain(fn, wrapper_name):
    """展开指定名称的包装链，返回最内层被包装函数。

    Patch B 的包装闭包自由变量仅 prev_invoke（模块级引用非 callable），
    故沿 callable cell 逐层下钻即可。fn 非包装版时原样返回；闭包不可内省
    时返回当前层（调用方按不匹配处理，安全降级）。
    """
    seen = set()
    while getattr(fn, "__name__", "") == wrapper_name and id(fn) not in seen:
        seen.add(id(fn))
        prev = None
        for cell in getattr(fn, "__closure__", None) or ():
            try:
                contents = cell.cell_contents
            except ValueError:  # 未填充 cell（理论不可达）
                continue
            if callable(contents):
                prev = contents
                break
        if prev is None:
            break
        fn = prev
    return fn


def _invoke_chain_root(invoke_fn):
    """展开 Patch B 包装链，返回最内层被包装函数。"""
    return _unwrap_wrapper_chain(invoke_fn, "_invoke_with_session_ctx")


def _engine_has_reentrant_compile() -> bool:
    """探测引擎是否带 reentrant compile（静态图复用的前置能力）。

    探针：``PregelGraph._compile`` 接受 ``nodes`` 参数——compile 把本次执行
    的 fresh vertex 注入编译器的入口。未含修复时该参数不存在（vertex 在
    build 期被 init，调用计数 / Future / NodeSession 全部跨执行残留）。

    只做签名探测，不在 import 期实例化引擎对象（Vertex() 会创建
    asyncio.Future，import 期无事件循环）。
    """
    try:
        from openjiuwen.core.graph.graph import PregelGraph as pregel_graph_cls
    except (ImportError, OSError):
        return False

    compile_internal = getattr(pregel_graph_cls, "_compile", None)
    if compile_internal is None:
        return False
    try:
        params = tuple(inspect.signature(compile_internal).parameters)
    except (TypeError, ValueError):
        return False
    return "nodes" in params


def _structure_assertions() -> list:
    """结构断言（spec §7.2）。返回失败消息列表，空 = 全部通过。

    全部经 inspect 签名 / 模块导入检查——不在 import 期实例化引擎对象。

    引擎导入（含 workflow_sub_stream_patch）全部包在 try/except 中：导入失败
    记为断言失败并跳过对应断言组——本函数永不抛 ImportError，调用方据此走
    降级路径（spec §7.2：断言失败必须降级而非抛异常）。
    """
    failures = []

    # A1: 引擎具备 reentrant compile——本分支实例复用的前置能力
    if not _engine_has_reentrant_compile():
        failures.append(
            "引擎不含 reentrant compile（PregelGraph._compile 无 nodes 参数，"
            "openjiuwen 依赖未指向含修复的版本），静态图复用不安全"
        )

    # B1: Patch B 包装对象必须是 sub_stream 补丁版本（应用顺序断言）。
    # 容忍两种合法态：apply 前 _invoke 即 sub_stream 补丁版；apply 后为
    # Patch B 包装版（其包装链最内层仍须是 sub_stream 补丁版）——接线后
    # 进程内 import 即应用，_structure_assertions 常态看到已包装态。
    try:
        from openjiuwen.core.graph.graph import CompiledGraph as compiled_graph_cls
        from jiuwen.extension.patches import workflow_sub_stream_patch
    except (ImportError, OSError) as e:
        failures.append(f"引擎导入失败（视为断言失败，自动降级）: {e}")
        compiled_graph_cls = workflow_sub_stream_patch = None
    if compiled_graph_cls is not None and workflow_sub_stream_patch is not None:
        patched_invoke = getattr(
            workflow_sub_stream_patch, "_patched_compiled_invoke", None
        )
        current_invoke = getattr(compiled_graph_cls, "_invoke", None)
        if patched_invoke is None:
            failures.append(
                "workflow_sub_stream_patch._patched_compiled_invoke 不存在"
                "（结构断言失败，自动降级）"
            )
        elif current_invoke is None:
            failures.append("CompiledGraph._invoke 不存在（结构断言失败，自动降级）")
        elif current_invoke is patched_invoke:
            pass  # apply 前：_invoke 即 sub_stream 补丁版
        elif _invoke_chain_root(current_invoke) is patched_invoke:
            pass  # apply 后：Patch B 包装版，包装链最内层是 sub_stream 补丁版
        else:
            failures.append(
                "CompiledGraph._invoke 既非 workflow_sub_stream_patch._patched_compiled_invoke"
                " 也非其 Patch B 包装版"
                "（static_graph_patch 必须在 apply_workflow_sub_stream_patch 之后应用）"
            )

    return failures


def _wrap_compiled_invoke(prev_invoke):
    """Patch B：包装当前 CompiledGraph._invoke（已被 sub_stream 补丁替换的版本）。

    执行树根 set workflow 级 session，finally token 式 reset——嵌套子工作流
    的子 _invoke set 为子 session、返回后恢复父 session。

    写入的是**引擎自己的** ContextVar 通道（``openjiuwen.core.session.
    execution_session_ctx``）：引擎的 ``BranchRouter.__call__`` /
    ``BaseWorkflow.new_router`` 都经该通道的 ``resolve_routing_session`` 解析，
    写自研通道不会被读到。
    """

    async def _invoke_with_session_ctx(self, inputs, session, config=None):
        token = _engine_session_ctx.set_workflow_session(session)
        try:
            return await prev_invoke(self, inputs, session, config)
        finally:
            _engine_session_ctx.reset_workflow_session(token)

    return _invoke_with_session_ctx


def apply_static_graph_patch() -> bool:
    """幂等应用入口（真实入口：ir_converter / sub_workflow import 链调用）。

    必须在 `apply_workflow_sub_stream_patch()` 之后调用（B1 断言强制）。

    Returns:
        True = 本次应用；False = 已应用或断言失败降级。
    """
    global _STATIC_GRAPH_PATCH_APPLIED, STATIC_GRAPH_DOWNGRADED
    global _original_compiled_invoke
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

    # 替换前保存原版引用（仅首次捕获：测试复位 flag 重放 apply 时类属性
    # 可能已是 patched 版本，覆盖会把 patched 误当原版基线）
    if _original_compiled_invoke is None:
        # 上游 _invoke 无公开入口，补丁须保存其私有方法引用作基线
        _original_compiled_invoke = CompiledGraph._invoke  # pylint: disable=protected-access

    # 补丁的安装点即该私有方法本身，上游未提供公开的替换入口
    CompiledGraph._invoke = _wrap_compiled_invoke(CompiledGraph._invoke)  # pylint: disable=protected-access

    _STATIC_GRAPH_PATCH_APPLIED = True
    return True
