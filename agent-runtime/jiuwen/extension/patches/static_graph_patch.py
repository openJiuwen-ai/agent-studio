# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""静态图复用 patch 集（A/B/C/D，issue #1555 / spec 2026-10-12 §4）。

- Patch A：PregelGraph.compile 纯函数化（每次执行全新 Pregel/channels/
  checkpointer/Vertex，fresh vertex 包装共享 executable）；
- Patch B：CompiledGraph._invoke 入口 set workflow 级 session ContextVar；
- Patch C：BranchRouter.__call__ 解析链 组件级 → workflow 级 → self._session；
- Patch D：BranchComponent.invoke 包装——补写组件级 session（分支源节点的
  路由 dispatch 保真；venv 源码不可改，包装其唯一动作 set_session）。

四件**始终应用**（实例复用为默认且唯一路径，WORKFLOW_INSTANCE_REUSE_MODE
配置已移除）：patched 路径即引擎现状。openjiuwen 结构变化时由
_structure_assertions 兜底：断言失败 → 不应用补丁 +
STATIC_GRAPH_DOWNGRADED=True + ERROR 日志，实例缓存据此强制关闭
（直建路径）。

本模块不依赖 openjiuwen 的版本号（git develop 依赖无 pin），结构断言
比版本检查可靠。上游合入等价修复后，按 patches/ 惯例移除本补丁。
"""
from __future__ import annotations

import copy
import inspect
from typing import Any

# 打断 openjiuwen 循环 import（graph.py → vertex.py → workflow.components.base
# → workflow/__init__ → workflow.py:34 回引 graph.py）。缺此先行导入时，本模块
# 若为进程内首个触碰 openjiuwen.core.graph.graph 的模块会 ImportError（与
# tests/unit_tests/extension/patches/test_static_graph_patch.py 顶部同理）。
import openjiuwen.core.workflow  # noqa: F401  # pylint: disable=unused-import
from openjiuwen.core.common.exception.codes import StatusCode
from openjiuwen.core.common.exception.errors import build_error
from openjiuwen.core.common.logging import LogEventType, graph_logger, workflow_logger
from openjiuwen.core.graph.graph import CompiledGraph, PregelGraph
from openjiuwen.core.graph.pregel.constants import SESSION_ID
from openjiuwen.core.graph.store import GraphStore
from openjiuwen.core.graph.vertex import Vertex
from openjiuwen.core.session.tracer import TracerWorkflowUtils
from openjiuwen.core.workflow.components.flow.branch_router import BranchRouter

from jiuwen.extension.workflow import execution_session_ctx as _session_ctx

_STATIC_GRAPH_PATCH_APPLIED = False
STATIC_GRAPH_DOWNGRADED = False

# 替换前保存的原版引用（patches/ 惯例，nested_branch_barrier_patch 等同理）：
# 供测试取"未打补丁"基线（接线后 PregelGraph.compile 等进程内恒为 patched，
# 无法再经类属性取得原版）。注意 _original_compiled_invoke 捕获的是 sub_stream
# 补丁版（本补丁替换前值，B1 应用顺序语义），非引擎出厂原版。
# 仅在首次 apply 时捕获（None 判断）——测试复位 flag 重放 apply 时类属性
# 可能已是 patched 版本，覆盖会把 patched 误当原版。
_original_pregel_graph_compile: Any = None
_original_compiled_invoke: Any = None
_original_branch_router_call: Any = None
_original_branch_component_invoke: Any = None


def _unwrap_wrapper_chain(fn, wrapper_name):
    """展开指定名称的包装链，返回最内层被包装函数（B1/C2 断言共用）。

    Patch B/D 的包装闭包自由变量仅 prev_invoke（模块级引用非 callable），
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


def _structure_assertions() -> list:
    """openjiuwen 结构断言（spec §7.2）。返回失败消息列表，空 = 全部通过。

    全部经 inspect 源码/签名检查——不在 import 期实例化引擎对象
    （Vertex() 会创建 asyncio.Future，import 期无事件循环）。

    引擎导入（含 workflow_sub_stream_patch）全部包在 try/except 中：
    导入失败（openjiuwen 循环 import 未被打断、上游模块/符号改名等）记为
    断言失败并跳过对应断言组——本函数永不抛 ImportError，调用方据此走
    降级路径（spec §7.2：断言失败必须降级而非抛异常）。

    口径例外：C2 组（BranchComponent，可选组件）导入失败**仅跳过该组、
    不计入失败**——引擎无此组件时 ir_converter 自身 import 即失败，该
    路径不可达；不因单一可选组件缺失而整体降级（组内注释同此口径）。
    """
    failures = []

    # A1/A2: PregelGraph 源码模式——Patch A 的改写基础
    # 函数内重导入一律用独立别名绑定，避免遮蔽模块级类引用（模块级引用
    # 在 _compile_pregel_fresh / apply_static_graph_patch 中仍被使用）
    try:
        from openjiuwen.core.graph.graph import PregelGraph as pregel_graph_cls
    except (ImportError, OSError) as e:
        failures.append(f"引擎导入失败（视为断言失败，自动降级）: {e}")
        pregel_graph_cls = None
    if pregel_graph_cls is not None:
        compile_fn = getattr(pregel_graph_cls, "compile", None)
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
        compile_internal_fn = getattr(pregel_graph_cls, "_compile", None)
        if compile_internal_fn is None:
            failures.append("PregelGraph._compile 不存在（结构断言失败，自动降级）")
        else:
            try:
                compile_internal_src = inspect.getsource(compile_internal_fn)
                if "self.nodes" not in compile_internal_src:
                    failures.append("PregelGraph._compile 不再读取 self.nodes（shadow 方案失效）")
            except (OSError, TypeError, ValueError) as e:
                failures.append(f"PregelGraph._compile 源码不可内省: {e}")

    # B1: Patch B 包装对象必须是 sub_stream 补丁版本（应用顺序断言）。
    # 容忍两种合法态：apply 前 _invoke 即 sub_stream 补丁版；apply 后为
    # Patch B 包装版（其包装链最内层仍须是 sub_stream 补丁版）——Task 6
    # 接线后进程内 import 即应用，_structure_assertions 常态看到已包装态。
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

    # C1: BranchRouter.__call__ 以 self._session 解析——Patch C 的替换基础
    try:
        from openjiuwen.core.workflow.components.flow.branch_router import (
            BranchRouter as branch_router_cls,
        )
    except (ImportError, OSError) as e:
        failures.append(f"引擎导入失败（视为断言失败，自动降级）: {e}")
        branch_router_cls = None
    if branch_router_cls is not None:
        call_fn = getattr(branch_router_cls, "__call__", None)
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
        if not hasattr(branch_router_cls, "set_session"):
            failures.append("BranchRouter.set_session 不存在")

    # C2: BranchComponent.invoke 的 set_session 写入点（Patch D 包装基础）。
    # 经包装链展开后校验最内层（apply 后 BranchComponent.invoke 即本模块
    # 包装版——直接 getsource 会读到包装函数源码而误报，与 B1 的容忍语义同理）。
    # 导入失败仅跳过本组（引擎无此组件时 ir_converter 自身 import 即失败，
    # 该路径不可达；不因单一可选组件缺失而整体降级）。
    try:
        from openjiuwen.core.workflow.components.flow.branch_comp import BranchComponent
    except (ImportError, OSError):
        pass  # 引擎无此组件（版本差异），跳过
    else:
        branch_invoke = _unwrap_wrapper_chain(
            BranchComponent.invoke, "_invoke_with_component_exec"
        )
        try:
            branch_invoke_src = inspect.getsource(branch_invoke)
        except (OSError, TypeError, ValueError) as e:
            failures.append(f"BranchComponent.invoke 源码不可内省: {e}")
        else:
            if "set_session" not in branch_invoke_src:
                failures.append("BranchComponent.invoke 不再调用 set_session（Patch D 基础失效）")

    # D1: Vertex 实例属性与签名——fresh-vertex 包装依赖
    try:
        from openjiuwen.core.graph.vertex import Vertex as vertex_cls
    except (ImportError, OSError) as e:
        failures.append(f"引擎导入失败（视为断言失败，自动降级）: {e}")
        vertex_cls = None
    if vertex_cls is not None:
        try:
            vertex_src = inspect.getsource(vertex_cls.__init__)
            for attr in ("_stream_done", "_call_count", "_stream_call_count"):
                if attr not in vertex_src:
                    failures.append(f"Vertex.__init__ 不再初始化 {attr}")
            params = tuple(inspect.signature(vertex_cls.__init__).parameters)
            if params != ("self", "node_id", "executable"):
                failures.append(f"Vertex.__init__ 签名变化: {params}（期望 (self, node_id, executable)）")
        except (OSError, TypeError, ValueError) as e:
            failures.append(f"Vertex 不可内省: {e}")

    # A4: StreamActor 持有的 vertex 可被替换——C1 修复的注入点
    # （fresh vertex 注册进 StreamGraph 的 per-execution 副本）。
    try:
        from openjiuwen.core.graph.stream_actor.base import StreamActor
        from openjiuwen.core.graph.stream_actor.manager import ActorManager
    except (ImportError, OSError) as e:
        failures.append(f"引擎导入失败（视为断言失败，自动降级）: {e}")
        StreamActor = ActorManager = None
    if ActorManager is not None:
        init_fn = getattr(ActorManager, "__init__", None)
        if init_fn is None:
            failures.append("ActorManager.__init__ 不存在（结构断言失败，自动降级）")
        else:
            try:
                manager_src = inspect.getsource(init_fn)
                if "self._streams[consumer_id] = StreamActor(" not in manager_src:
                    failures.append(
                        "ActorManager.__init__ 不再以 'self._streams[consumer_id] = StreamActor('"
                        " 构造 StreamActor（C1 修复的 actor 定位点缺失）"
                    )
            except (OSError, TypeError, ValueError) as e:
                failures.append(f"ActorManager.__init__ 源码不可内省: {e}")
    if StreamActor is not None:
        init_fn = getattr(StreamActor, "__init__", None)
        if init_fn is None:
            failures.append("StreamActor.__init__ 不存在（结构断言失败，自动降级）")
        else:
            try:
                actor_src = inspect.getsource(init_fn)
                if "self._vertex = vertex" not in actor_src:
                    failures.append(
                        "StreamActor.__init__ 不再保存 'self._vertex = vertex'"
                        "（C1 修复的 actor._vertex 替换点缺失）"
                    )
            except (OSError, TypeError, ValueError) as e:
                failures.append(f"StreamActor.__init__ 源码不可内省: {e}")

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


async def _patched_branch_router_call(self, *args, **kwargs) -> list:
    """Patch C：session 解析链（spec §4.3）。

    原版首行 `session = self._session`（branch_router.py:93）——共享
    router 实例并发执行时读到错误会话；且 BaseWorkflow.compile 每次替换
    共享 ProxySession._stub 的竞态也经此封堵（执行期间 ContextVar 恒有
    值，racy 的 _stub 永不被读到）。其余逻辑与原版一致。
    """
    # 上游 BranchRouter 未提供 session 的公开读取入口，本补丁须原样代理该字段
    session = _session_ctx.resolve_routing_session(self._session)  # pylint: disable=protected-access
    if self.report_trace:
        branches = []
        # 分支集合是上游 BranchRouter 的内部实现细节，无公开读取入口
        for branch in self._branches:  # pylint: disable=protected-access
            branches.append({
                "branch_id": branch.branch_id,
                "condition": branch.trace_info(session)
            })
        await TracerWorkflowUtils.trace_component_begin(session)
        await TracerWorkflowUtils.trace_component_inputs(session, {"branches": branches})
    # 分支集合无公开读取入口，本补丁须原样遍历其私有字段
    for branch in self._branches:  # pylint: disable=protected-access
        if branch.evaluate(session):
            if self.report_trace:
                await TracerWorkflowUtils.trace_component_outputs(session, {"branch_id": branch.branch_id})
                await TracerWorkflowUtils.trace_component_done(session)
            return branch.target
    raise build_error(
        StatusCode.COMPONENT_BRANCH_EXECUTION_ERROR,
        reason="branch meeting the condition was not found"
    )


def _wrap_branch_component_invoke(prev_invoke):
    """Patch D：BranchComponent.invoke 设置 component_exec（路由保真）。

    BranchComponent（venv）invoke 唯一动作是 router.set_session(session)
    （NodeSession）——Patch C 读侧改走 ContextVar 后，需在此补写组件级
    session，保证分支源节点的 dispatch 解析到与现状一致的 NodeSession。
    不 reset：BranchComponent 是路由属主（router 经 add_conditional_edges
    注册），值须存活到同 NodeTask 内 invoke 返回之后的 dispatch。

    值类型契约（T12 审查）：写入端存**组件面 Session 包装器原样**（不解包
    ——组件自身读点依赖包装器 API）；Patch C 的 BaseSession 契约由
    ``resolve_routing_session`` 读取端解包承担。原函数照常执行——其
    set_session 写成为死写（Patch C 下不被读），语义由本通道等价承接。
    """

    async def _invoke_with_component_exec(self, inputs, session, context):
        _session_ctx.set_component_exec(session, context)
        return await prev_invoke(self, inputs, session, context)

    return _invoke_with_component_exec


def _compile_pregel_fresh(graph, fresh_nodes, graph_store, step_callback):
    """对影子图调用原版 _compile（nodes 注入点）。

    原版 _compile 读 self.nodes——无法安全传参，原地替换 self.nodes 在
    并发 compile 下会串（compile1 换入 fresh1 后 compile2 换入 fresh2，
    compile1 的 _compile 可能读到 fresh2）。shadow-copy：影子图共享
    build 期静态属性（edges/waits/branches/branch_targets 构建完成后
    不再变化），仅覆盖 nodes，各自调用互不可见。

    注意：影子图上 self._resolve_barrier_groups 仍是仓库已 patch 的
    版本（parallel_branch_grouping/nested_branch_barrier），barrier
    解析语义保持。
    """
    shadow = copy.copy(graph)
    shadow.nodes = fresh_nodes
    # 上游 _compile 无公开入口，shadow-copy 方案须直接调用其原版实现
    return PregelGraph._compile(  # pylint: disable=protected-access
        shadow, graph_store=graph_store, step_callback=step_callback
    )


def _patched_pregel_graph_compile(self, session, **kwargs):
    """Patch A：纯函数化 compile（spec §4.1）。

    与原版（graph.py:239-265）差异：
    1. 每节点新建 Vertex 包装共享 executable（原 build 期 Vertex 不再被
       init——规避 Future 绑定旧事件循环、调用计数残留、NodeSession 覆写）；
    2. 无条件全新构建（不再判断 self.pregel is None）；
    3. after_step 闭包捕获 session 参数（原版读 self._session——共享实例
       并发执行时的竞态根源）；
    4. 保留 self.pregel/checkpointer/_session 属性写入（读取方仅为
       compile/after_step 自身，见计划"属性读取方审计"；保留写入使
       off 模式等价论证成立）。异常路径下写入时序与原版不同：原版先写
       checkpointer 再 _compile，本实现统一在 _compile 之后写三者——
       读取方为零，无实质影响（M6）。
    """
    fresh_nodes = {}
    for node_id, node in self.nodes.items():
        fresh = Vertex(node_id, node._executable)  # pylint: disable=protected-access
        fresh.is_end_node = node.is_end_node
        fresh.init(session, **kwargs)
        fresh_nodes[node_id] = fresh

    def after_step(loop):
        if session:
            session.state().commit()
        graph_logger.debug(
            f"Finished to run graph super-step [{loop.step}]",
            event_type=LogEventType.GRAPH_SUPER_STEP_END,
            graph_id=loop.config['ns'],
            session_id=loop.config.get(SESSION_ID),
            metadata={
                "ns": loop.config['ns'],
                "step": loop.step,
                "active_nodes": list(loop.active_nodes)
            }
        )

    checkpointer = session.checkpointer()
    store = GraphStore(checkpointer.graph_store())
    pregel = _compile_pregel_fresh(self, fresh_nodes, graph_store=store, step_callback=after_step)

    # StreamActor 的 vertex 换成本次执行的 fresh vertex（C1 修复）。
    # ActorManager 为每执行新建（_create_workflow_session / LoopGroup.on_invoke），
    # 在 compile 之前构造、经 StreamGraph.get_node() 持有 build 期 vertex；
    # StreamActor.send 的 should_handle_message/is_done/stream_call 依赖
    # Vertex.init 设置的 _component_ability/_session。manager 属 per-execution
    # 状态，此处替换不写任何共享对象。三条路径（主/子工作流/循环体）的
    # compile 收到的 session 均可达 actor_manager()。
    manager = None
    try:
        manager = session.actor_manager()
    except Exception:
        manager = None
    streams = getattr(manager, "_streams", None)
    if isinstance(streams, dict):
        for actor in streams.values():
            fresh = fresh_nodes.get(getattr(actor, "_node_id", None))
            if fresh is not None:
                actor._vertex = fresh  # pylint: disable=protected-access

    # 属性保留写入（偏离②）：兼容潜在读取方；off 模式下每请求新实例的
    # 首次 compile 本来就执行等价赋值（异常路径时序差异见 docstring 第 4 点）。
    self.pregel = pregel
    self.checkpointer = checkpointer
    # 原版编译期即写该私有属性，保留写入以兼容潜在读取方（读取方为零，M6）
    self._session = session  # pylint: disable=protected-access
    return CompiledGraph(pregel, checkpointer)


def apply_static_graph_patch() -> bool:
    """幂等应用入口（真实入口：ir_converter / sub_workflow import 链调用）。

    必须在 `apply_workflow_sub_stream_patch()` 之后调用（B1 断言强制）。

    Returns:
        True = 本次应用；False = 已应用或断言失败降级。
    """
    global _STATIC_GRAPH_PATCH_APPLIED, STATIC_GRAPH_DOWNGRADED
    global _original_pregel_graph_compile, _original_compiled_invoke
    global _original_branch_router_call, _original_branch_component_invoke
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
    if _original_pregel_graph_compile is None:
        _original_pregel_graph_compile = PregelGraph.compile
    if _original_compiled_invoke is None:
        # 上游 _invoke 无公开入口，补丁须保存其私有方法引用作基线
        _original_compiled_invoke = CompiledGraph._invoke  # pylint: disable=protected-access
    if _original_branch_router_call is None:
        _original_branch_router_call = BranchRouter.__call__

    # Patch D 的引擎侧目标（可选组件：无此模块时跳过，不整体降级——
    # 该缺失态下 ir_converter 自身 import 即失败，本补丁路径不可达）
    try:
        from openjiuwen.core.workflow.components.flow.branch_comp import BranchComponent
    except ImportError:
        BranchComponent = None
    if BranchComponent is not None and _original_branch_component_invoke is None:
        _original_branch_component_invoke = BranchComponent.invoke

    # 四件安装：A（PregelGraph.compile）/ B（CompiledGraph._invoke）/ C（BranchRouter.__call__）
    # / D（BranchComponent.invoke）
    # 补丁的安装点即该私有方法本身，上游未提供公开的替换入口
    CompiledGraph._invoke = _wrap_compiled_invoke(CompiledGraph._invoke)  # pylint: disable=protected-access
    PregelGraph.compile = _patched_pregel_graph_compile
    BranchRouter.__call__ = _patched_branch_router_call
    if BranchComponent is not None:
        BranchComponent.invoke = _wrap_branch_component_invoke(BranchComponent.invoke)

    _STATIC_GRAPH_PATCH_APPLIED = True
    return True
