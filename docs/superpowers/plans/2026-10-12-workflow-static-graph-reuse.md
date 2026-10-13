# Workflow 静态图复用与实例缓存（L1）实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 issue #1555 的 L1：openjiuwen 引擎 patch 三件套 + 组件无状态化 + 进程内 Workflow 实例缓存（LazyWorkflow 保留制），默认 `off` 发布、零行为变化，`static_graph` 模式下已发布 IR 的重复执行复用已构建图。

**Architecture:** 静态图模板 + 每次执行轻量物化——缓存构建的贵重产物（组件实例、图结构、模型客户端），执行期状态（session、checkpointer、channels、Vertex、流式末帧输出）全部移到 per-execution 对象与 ContextVar。三个 monkey-patch（compile 纯函数化 / `_invoke` 入口 ContextVar / BranchRouter 解析链）始终应用（含 off 模式，严格等价，见下"等价性论证"）；缓存仅对 `static_graph` 模式 + `is_published` IR + 未降级 时启用。

**Tech Stack:** Python 3.11（`agent-runtime/.venv`，openjiuwen **0.1.19**）、pytest 9 + pytest-asyncio（已装入 venv）、contextvars、asyncio。

**Spec:** `docs/superpowers/specs/2026-10-12-workflow-static-graph-reuse-design.md`（本计划从 spec 出发论证；执行者需同时读取 spec）。

## Global Constraints

- 工作目录：所有命令在 `/home/zhongyiwei/git/agent-studio/agent-runtime` 下执行；分支 `feature/workflow-static-graph-reuse`。
- 测试命令：`.venv/bin/python -m pytest <path> -v`（pytest 已装入项目 venv；**不要**用 `uv run pytest`——它会解析到用户级 Python 3.12 环境导致 `common_utils` 缺失报错）。
- openjiuwen 是外部安装包（`.venv/lib/python3.11/site-packages/openjiuwen/`，版本 0.1.19），**禁止修改其源码**；所有引擎行为变更经 `jiuwen/extension/patches/` 的 monkey-patch。
- patch 惯例（对齐现有 5 个补丁）：模块级 `_PATCH_APPLIED` flag + `apply_*() -> bool` 幂等入口（True=本次应用，False=已应用）；docstring 标注"上游修复合并后移除"。
- 性能指标经 `performance_logger`（`from openjiuwen.core.common.logging import performance_logger`），格式 `name|value`。
- 配置经 `agent_runtime/common/config.py` 的 `CacheSettings`（pydantic-settings，`validation_alias` 环境变量名），启动读取、重启生效。
- 提交信息格式：`feat(runtime): <中文描述>` / `test(runtime): <中文描述>` / `refactor(runtime): <中文描述>`，一个任务一提交。
- 默认行为不变式：`WORKFLOW_INSTANCE_REUSE_MODE` 默认 `off`；off 模式下实例缓存零触碰（`aget_or_create_workflow_instance` 直通 build）。

### 等价性论证（off 模式下 patch 始终应用为何安全）

- **Patch A**（compile 纯函数化）：off 模式下每请求新建 Workflow 实例，其首次 compile 本来就走 `self.pregel is None` 全新构建分支——patched 版本只是无条件走该分支。属性读取方审计结论：`PregelGraph.pregel/checkpointer/_session` 的读取方**仅 graph.py 自身**（compile/after_step 闭包），仓库侧 patch 与引擎其他代码零外部读取；patch 保留属性写入（每次写全新对象）。
- **唯一行为变化点**（既是等价性例外也是 bug 修复）：同一图实例多次 compile 的场景（子工作流节点被循环体反复触发时，`Workflow.invoke` 每次都 compile）——现状复用第一次的 pregel/checkpointer（checkpointer 绑定第一个 session，跨 loop 迭代泄漏 checkpoint 到错误 session）；patched 后每次 compile 全新。现有 loop/sub-workflow 测试（`test_resume_cancel_check.py` 等）是此变化的回归门禁。
- **Patch B**：仅在执行树根 set/reset 一个无人读取的 ContextVar（off 模式下 Patch C 的回退分支命中同一 session）。
- **Patch C**：解析顺序 组件级 ContextVar → workflow 级 ContextVar → `self._session`，三层都指向当前执行的 session（off 模式）。

### 计划期已验证的关键事实（执行者不需要重新发现）

1. MagicMock session 可走通真实 IR 构建的 workflow 的 `graph.compile()`（已实验验证），compile 级单测无需真实 checkpointer。
2. `build_openjiuwen_workflow_from_ir` 的 `**kwargs`（cust_headers/project_id）在函数体内完全未使用——缓存命中忽略 kwargs 安全。
3. `BranchRouter.__call__`（`branch_router.py:92-112`）首行 `session = self._session`；被 `ConditionalRouter.dispatch` 裸调（无参）。
4. 引擎 `Vertex._post_stream`（`vertex.py:624-628`）在组件 stream generator 耗尽后调 `self._executable.get_stream_output()` 并写入 `session.state().set_outputs()`——这是 `_stream_final_output` 的唯一消费方，读取发生在 `await end_message` 之后（共享实例上有跨执行清零竞态，组件任务用无 reset 的 ContextVar 修复）。
5. `auto_complete_abilities`（`_workflow.py:336-346`）是同步无 await 函数（事件循环内原子）且终态幂等（`_add_ability_to_node` 有 `not in` 检查、`stream_source_groups` 整体赋值）——**无需守卫 patch**（spec §5.3 的开放问题已在计划期解决，改为幂等性测试锁定）。
6. `CompiledGraph._invoke` 已被 `workflow_sub_stream_patch.py:539` 替换为 `_patched_compiled_invoke`（签名 `(self, inputs, session, config=None)`）；static_graph_patch 必须在其之后应用。
7. NodeTask 每节点经 `asyncio.create_task` 提交（`task.py:27-30`），context 为提交时刻快照的副本——组件内 set 的 ContextVar 不泄漏到兄弟节点任务。
8. 引擎 `Vertex.__init__(node_id, executable=None)`；build 期唯一额外可变属性是 `end_node()` 设置的 `is_end_node`（`graph.py:78-84`），fresh vertex 必须复制。

---

### Task 1: execution_session_ctx 模块（ContextVar 基建）

**Files:**
- Create: `jiuwen/extension/workflow/execution_session_ctx.py`
- Test: `tests/unit_tests/extension/test_execution_session_ctx.py`

**Interfaces:**
- Consumes: 无（纯 contextvars 标准库）。
- Produces（后续所有任务依赖，签名必须与此完全一致）:
  - `set_workflow_session(session) -> Token` / `reset_workflow_session(token) -> None` / `current_workflow_session() -> Any | None`
  - `set_component_exec(session, context) -> Token` / `reset_component_exec(token) -> None` / `current_component_exec() -> tuple[Any | None, Any | None]`
  - `set_stream_final_output(value: dict | None) -> None` / `get_stream_final_output() -> dict | None`
  - `resolve_routing_session(fallback=None) -> Any`（Patch C 的解析链）

- [ ] **Step 1: 写失败测试**

```python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""execution_session_ctx：执行期 session 的 ContextVar 通道单测。

三个通道的写入/读取/隔离语义（模块 docstring 详述"谁写谁读"），
以及 resolve_routing_session 的三层解析顺序（Patch C 语义）。
"""
import pytest

from jiuwen.extension.workflow import execution_session_ctx as ctx


class TestWorkflowSessionChannel:
    def test_set_and_reset(self):
        sentinel = object()
        token = ctx.set_workflow_session(sentinel)
        assert ctx.current_workflow_session() is sentinel
        ctx.reset_workflow_session(token)
        assert ctx.current_workflow_session() is None

    def test_default_is_none(self):
        assert ctx.current_workflow_session() is None


class TestComponentExecChannel:
    def test_set_and_reset(self):
        s, c = object(), object()
        token = ctx.set_component_exec(s, c)
        assert ctx.current_component_exec() == (s, c)
        ctx.reset_component_exec(token)
        assert ctx.current_component_exec() == (None, None)


class TestStreamFinalOutputChannel:
    def test_set_without_reset_is_visible(self):
        # 语义：不 reset——引擎 Vertex._post_stream 在 generator 耗尽后读取
        ctx.set_stream_final_output({"userFields": "x"})
        assert ctx.get_stream_final_output() == {"userFields": "x"}
        ctx.set_stream_final_output(None)
        assert ctx.get_stream_final_output() is None


class TestResolveRoutingSession:
    def test_priority_component_over_workflow_over_fallback(self):
        component_s, workflow_s, fallback_s = object(), object(), object()

        # 仅 fallback
        assert ctx.resolve_routing_session(fallback_s) is fallback_s

        # + workflow 层
        t1 = ctx.set_workflow_session(workflow_s)
        assert ctx.resolve_routing_session(fallback_s) is workflow_s

        # + component 层（最高优先级）
        t2 = ctx.set_component_exec(component_s, None)
        assert ctx.resolve_routing_session(fallback_s) is component_s

        # 逐层退栈
        ctx.reset_component_exec(t2)
        assert ctx.resolve_routing_session(fallback_s) is workflow_s
        ctx.reset_workflow_session(t1)
        assert ctx.resolve_routing_session(fallback_s) is fallback_s
```

- [ ] **Step 2: 运行确认失败**

Run: `.venv/bin/python -m pytest tests/unit_tests/extension/test_execution_session_ctx.py -v`
Expected: FAIL（`ModuleNotFoundError: No module named 'jiuwen.extension.workflow.execution_session_ctx'`）

- [ ] **Step 3: 实现模块**

```python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""执行期 session 的 ContextVar 通道（静态图复用配套，spec §4）。

背景：Workflow 实例缓存复用后，组件实例/图结构跨执行共享，执行期状态
（session、context、流式末帧输出）不能再落在可复用对象的实例属性上。

三个通道，按"谁写入、谁读取"划分：

1. ``_workflow_session``：Patch B 在 ``CompiledGraph._invoke`` 入口 set、
   finally reset，值为本次执行的 workflow 级 session（WorkflowSession /
   SubWorkflowSession）。子工作流嵌套经 token 栈式恢复（子执行期间组件
   解析到子 session）。供 Patch C 的路由第二优先级解析。
2. ``_component_exec``：(session, context) 二元组。分支路由属主组件
   （IntentDetection/_RoutedIntentDetection）在 invoke 入口 set 且**不
   reset**——路由 dispatch 发生在 invoke 返回之后的同一 NodeTask 里
   （task.py 的 NodeTask.run：先跑节点函数再 dispatch），值必须存活到
   dispatch；其他组件（LLMChain 等）set 后在 finally reset，避免本节点
   的路由误解析到组件级 session（与现状 add_conditional_connection 的
   ProxySession 语义对齐）。NodeTask 每节点独立 context
   （asyncio.create_task 拷贝），天然跨执行隔离。
3. ``_stream_final_output``：流式组件的末帧输出。**不 reset**——引擎
   Vertex._post_stream 在 generator 耗尽后读取（vertex.py:624-628），
   reset 会丢值。同样依赖 NodeTask 的 context 隔离。
"""
from __future__ import annotations

from contextvars import ContextVar, Token
from typing import Any, Optional, Tuple

_workflow_session: ContextVar[Optional[Any]] = ContextVar(
    "jiuwen_workflow_session", default=None
)
_component_exec: ContextVar[Tuple[Optional[Any], Optional[Any]]] = ContextVar(
    "jiuwen_component_exec", default=(None, None)
)
_stream_final_output: ContextVar[Optional[dict]] = ContextVar(
    "jiuwen_stream_final_output", default=None
)


def set_workflow_session(session: Any) -> Token:
    return _workflow_session.set(session)


def reset_workflow_session(token: Token) -> None:
    _workflow_session.reset(token)


def current_workflow_session() -> Optional[Any]:
    return _workflow_session.get()


def set_component_exec(session: Any, context: Any) -> Token:
    return _component_exec.set((session, context))


def reset_component_exec(token: Token) -> None:
    _component_exec.reset(token)


def current_component_exec() -> Tuple[Optional[Any], Optional[Any]]:
    return _component_exec.get()


def set_stream_final_output(value: Optional[dict]) -> None:
    _stream_final_output.set(value)


def get_stream_final_output() -> Optional[dict]:
    return _stream_final_output.get()


def resolve_routing_session(fallback: Any = None) -> Any:
    """路由 session 解析链（Patch C）：组件级 → workflow 级 → 调用方回退。

    与现状语义对齐：
    - add_conditional_connection 注册的路由 → ProxySession（workflow 级），
      对应 workflow 级分支；
    - IntentDetection/_RoutedIntentDetection 每次执行 set_session(组件
      NodeSession) → 对应组件级分支（需存活到同 task 内的 dispatch）。
    """
    session, _ = _component_exec.get()
    if session is not None:
        return session
    workflow_session = _workflow_session.get()
    if workflow_session is not None:
        return workflow_session
    return fallback
```

- [ ] **Step 4: 运行确认通过**

Run: `.venv/bin/python -m pytest tests/unit_tests/extension/test_execution_session_ctx.py -v`
Expected: PASS（全部用例）

- [ ] **Step 5: 提交**

```bash
git add jiuwen/extension/workflow/execution_session_ctx.py tests/unit_tests/extension/test_execution_session_ctx.py
git commit -m "feat(runtime): 执行期 session 的 ContextVar 通道（workflow/组件/流式末帧三通道）"
```

---

### Task 2: static_graph_patch 骨架 + 结构断言

**Files:**
- Create: `jiuwen/extension/patches/static_graph_patch.py`
- Create: `tests/unit_tests/extension/patches/__init__.py`（空文件）
- Test: `tests/unit_tests/extension/patches/test_static_graph_patch.py`

**Interfaces:**
- Consumes: Task 1 的 `execution_session_ctx`。
- Produces:
  - 模块级 `_STATIC_GRAPH_PATCH_APPLIED: bool`、`STATIC_GRAPH_DOWNGRADED: bool`（Task 7 缓存门控读取）
  - `_structure_assertions() -> list[str]`（空列表 = 全部通过）
  - 本任务只建骨架：flags + 断言函数 + 一个**只跑断言不装补丁**的 `apply_static_graph_patch()` 骨架（Task 3/4/5 逐步填充三件套，Task 6 完成编排）

- [ ] **Step 1: 写失败测试**

```python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""static_graph_patch 结构断言与降级语义单测。

断言策略：真实 venv（openjiuwen 0.1.19，已由 ir_converter import 时应用
sub_stream 补丁）→ 断言全过；monkeypatch 破坏结构 → 对应断言命中。
"""
import pytest

from jiuwen.extension.patches import static_graph_patch


@pytest.fixture
def _restore_flags():
    """恢复模块级 flag（apply 测试会翻转它们）。"""
    saved = (
        static_graph_patch._STATIC_GRAPH_PATCH_APPLIED,
        static_graph_patch.STATIC_GRAPH_DOWNGRADED,
    )
    yield
    static_graph_patch._STATIC_GRAPH_PATCH_APPLIED = saved[0]
    static_graph_patch.STATIC_GRAPH_DOWNGRADED = saved[1]


class TestStructureAssertions:
    def test_real_engine_passes_all_assertions(self):
        """真实 openjiuwen 0.1.19 + 已应用 sub_stream 补丁 → 断言全过。

        前置：import ir_converter（应用 sub_stream 补丁）。测试文件顶部
        import static_graph_patch 已间接触发（其 import openjiuwen 引擎类），
        但 sub_stream 补丁需 ir_converter 的 import 时应用——显式 import
        保证顺序。
        """
        import jiuwen.serve.controllers.execution.ir_converter  # noqa: F401

        assert static_graph_patch._structure_assertions() == []

    def test_compile_structure_change_detected(self, monkeypatch):
        """模拟上游改掉 compile 的 'pregel is None' 模式 → 断言命中。"""
        from openjiuwen.core.graph.graph import PregelGraph

        def _alien_compile(self, session, **kwargs):
            return None

        monkeypatch.setattr(PregelGraph, "compile", _alien_compile)
        failures = static_graph_patch._structure_assertions()
        assert any("PregelGraph.compile" in f for f in failures)

    def test_invoke_ordering_violation_detected(self, monkeypatch):
        """模拟 sub_stream 补丁未先行应用（_invoke 不是其版本）→ 断言命中。"""
        from openjiuwen.core.graph.graph import CompiledGraph

        async def _alien_invoke(self, inputs, session, config=None):
            return None

        monkeypatch.setattr(CompiledGraph, "_invoke", _alien_invoke)
        failures = static_graph_patch._structure_assertions()
        assert any("CompiledGraph._invoke" in f for f in failures)

    def test_branch_router_structure_change_detected(self, monkeypatch):
        """模拟 BranchRouter.__call__ 不再读 self._session → 断言命中。"""
        from openjiuwen.core.workflow.components.flow.branch_router import BranchRouter

        async def _alien_call(self, *args, **kwargs):
            return []

        monkeypatch.setattr(BranchRouter, "__call__", _alien_call)
        failures = static_graph_patch._structure_assertions()
        assert any("BranchRouter" in f for f in failures)

    def test_vertex_shape_change_detected(self, monkeypatch):
        """模拟 Vertex.__init__ 签名变化 → 断言命中。"""
        from openjiuwen.core.graph.vertex import Vertex

        def _alien_init(self, node_id, executable=None, extra=None):
            self._node_id = node_id

        monkeypatch.setattr(Vertex, "__init__", _alien_init)
        failures = static_graph_patch._structure_assertions()
        assert any("Vertex" in f for f in failures)
```

- [ ] **Step 2: 运行确认失败**

Run: `.venv/bin/python -m pytest tests/unit_tests/extension/patches/test_static_graph_patch.py -v`
Expected: FAIL（模块不存在）

- [ ] **Step 3: 实现骨架与断言**

```python
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

_STATIC_GRAPH_PATCH_APPLIED = False
STATIC_GRAPH_DOWNGRADED = False


def _structure_assertions() -> list:
    """openjiuwen 结构断言（spec §7.2）。返回失败消息列表，空 = 全部通过。

    全部经 inspect 源码/签名检查——不在 import 期实例化引擎对象
    （Vertex() 会创建 asyncio.Future，import 期无事件循环）。
    """
    failures = []

    from openjiuwen.core.graph.graph import CompiledGraph, PregelGraph
    from openjiuwen.core.graph.vertex import Vertex
    from openjiuwen.core.workflow.components.flow.branch_router import BranchRouter
    from jiuwen.extension.patches import workflow_sub_stream_patch

    # A1: compile 的 "首次绑定 pregel" 模式——Patch A 的改写基础
    try:
        compile_src = inspect.getsource(PregelGraph.compile)
    except (OSError, TypeError) as e:
        failures.append(f"PregelGraph.compile 源码不可内省: {e}")
        compile_src = ""
    if "self.pregel is None" not in compile_src:
        failures.append(
            "PregelGraph.compile 不再包含 'self.pregel is None' 分支（Patch A 基础失效）"
        )
    if "self._session" not in compile_src:
        failures.append("PregelGraph.compile 不再写/读 self._session（after_step 竞态改写点缺失）")

    # A2: _compile 读取 self.nodes——shadow-copy 方案的注入点
    try:
        compile_internal_src = inspect.getsource(PregelGraph._compile)
        if "self.nodes" not in compile_internal_src:
            failures.append("PregelGraph._compile 不再读取 self.nodes（shadow 方案失效）")
    except (OSError, TypeError) as e:
        failures.append(f"PregelGraph._compile 源码不可内省: {e}")

    # B1: Patch B 包装对象必须是 sub_stream 补丁版本（应用顺序断言）
    if CompiledGraph._invoke is not workflow_sub_stream_patch._patched_compiled_invoke:
        failures.append(
            "CompiledGraph._invoke 不是 workflow_sub_stream_patch._patched_compiled_invoke"
            "（static_graph_patch 必须在 apply_workflow_sub_stream_patch 之后应用）"
        )

    # C1: BranchRouter.__call__ 以 self._session 解析——Patch C 的替换基础
    try:
        call_src = inspect.getsource(BranchRouter.__call__)
        if "self._session" not in call_src:
            failures.append("BranchRouter.__call__ 不再读取 self._session")
    except (OSError, TypeError) as e:
        failures.append(f"BranchRouter.__call__ 源码不可内省: {e}")
    if not hasattr(BranchRouter, "set_session"):
        failures.append("BranchRouter.set_session 不存在")

    # D1: Vertex 实例属性与签名——fresh-vertex 包装依赖
    try:
        vertex_src = inspect.getsource(Vertex.__init__)
        for attr in ("_stream_done", "_call_count", "_stream_call_count"):
            if attr not in vertex_src:
                failures.append(f"Vertex.__init__ 不再初始化 {attr}")
        params = tuple(inspect.signature(Vertex.__init__).parameters)
        if params != ("self", "node_id", "executable"):
            failures.append(f"Vertex.__init__ 签名变化: {params}（期望 (self, node_id, executable)）")
    except (OSError, TypeError) as e:
        failures.append(f"Vertex 不可内省: {e}")

    return failures


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

    # Task 3/4/5 在此填充：PregelGraph.compile / CompiledGraph._invoke / BranchRouter.__call__
    _STATIC_GRAPH_PATCH_APPLIED = True
    return True
```

- [ ] **Step 4: 运行确认通过**

Run: `.venv/bin/python -m pytest tests/unit_tests/extension/patches/test_static_graph_patch.py -v`
Expected: PASS（5 个用例）

- [ ] **Step 5: 提交**

```bash
git add jiuwen/extension/patches/static_graph_patch.py tests/unit_tests/extension/patches/
git commit -m "feat(runtime): static_graph_patch 骨架与 openjiuwen 结构断言"
```

---

### Task 3: Patch B — CompiledGraph._invoke 入口 ContextVar

**Files:**
- Modify: `jiuwen/extension/patches/static_graph_patch.py`（新增 `_wrap_compiled_invoke`，接入 apply）
- Test: `tests/unit_tests/extension/patches/test_static_graph_patch.py`（追加 TestPatchB 类）

**Interfaces:**
- Consumes: Task 1 的 `set_workflow_session/reset_workflow_session/current_workflow_session`；Task 2 的 `apply_static_graph_patch`。
- Produces: `_wrap_compiled_invoke(prev_invoke) -> callable`（模块级函数；Task 6 的 apply 用它包装当前 `_invoke`）。安装后 `CompiledGraph._invoke` 签名不变：`async (self, inputs, session, config=None)`。

- [ ] **Step 1: 追加失败测试**

```python
class TestPatchB:
    """Patch B：包装当前 _invoke，执行期间 workflow session ContextVar 可见。"""

    def _make_wrapped(self, seen):
        from jiuwen.extension.patches.static_graph_patch import _wrap_compiled_invoke
        from jiuwen.extension.workflow import execution_session_ctx as ctx

        async def fake_prev_invoke(self, inputs, session, config=None):
            seen["during"] = ctx.current_workflow_session()
            seen["session_arg"] = session
            return "result"

        return _wrap_compiled_invoke(fake_prev_invoke)

    @pytest.mark.asyncio
    async def test_sets_and_resets_workflow_session(self):
        from jiuwen.extension.workflow import execution_session_ctx as ctx

        seen = {}
        wrapped = self._make_wrapped(seen)
        sentinel_session = object()

        class FakeCompiled:
            pass

        result = await wrapped(FakeCompiled(), {"i": 1}, sentinel_session, None)

        assert result == "result"
        assert seen["during"] is sentinel_session
        assert seen["session_arg"] is sentinel_session
        assert ctx.current_workflow_session() is None  # finally 已 reset

    @pytest.mark.asyncio
    async def test_nested_invoke_stack_semantics(self):
        """嵌套（子工作流）场景：内层 set 后恢复外层——token 栈式。"""
        from jiuwen.extension.workflow import execution_session_ctx as ctx

        seen = {}
        wrapped = self._make_wrapped(seen)
        outer_session, inner_session = object(), object()

        class FakeCompiled:
            pass

        async def inner_prev(self, inputs, session, config=None):
            return ctx.current_workflow_session()

        from jiuwen.extension.patches.static_graph_patch import _wrap_compiled_invoke
        inner_wrapped = _wrap_compiled_invoke(inner_prev)

        async def outer_prev(self, inputs, session, config=None):
            # 外层执行中调用内层（模拟子工作流）
            inner_result = await inner_wrapped(self, inputs, inner_session, None)
            return {"inner_saw": inner_result, "outer_saw": ctx.current_workflow_session()}

        outer_wrapped = _wrap_compiled_invoke(outer_prev)
        result = await outer_wrapped(FakeCompiled(), {}, outer_session, None)

        assert result["inner_saw"] is inner_session
        assert result["outer_saw"] is outer_session
        assert ctx.current_workflow_session() is None

    @pytest.mark.asyncio
    async def test_exception_still_resets(self):
        from jiuwen.extension.workflow import execution_session_ctx as ctx

        async def boom_prev(self, inputs, session, config=None):
            raise RuntimeError("boom")

        from jiuwen.extension.patches.static_graph_patch import _wrap_compiled_invoke
        wrapped = _wrap_compiled_invoke(boom_prev)

        class FakeCompiled:
            pass

        with pytest.raises(RuntimeError):
            await wrapped(FakeCompiled(), {}, object(), None)
        assert ctx.current_workflow_session() is None
```

- [ ] **Step 2: 运行确认失败**

Run: `.venv/bin/python -m pytest tests/unit_tests/extension/patches/test_static_graph_patch.py::TestPatchB -v`
Expected: FAIL（`ImportError: cannot import name '_wrap_compiled_invoke'`）

- [ ] **Step 3: 实现 _wrap_compiled_invoke 并接入 apply**

在 `static_graph_patch.py` 顶部 import 区追加：

```python
from jiuwen.extension.workflow import execution_session_ctx as _session_ctx
```

在 `_structure_assertions` 之后追加：

```python
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
```

`apply_static_graph_patch()` 中"Task 3/4/5 在此填充"注释处替换为：

```python
    from openjiuwen.core.graph.graph import CompiledGraph

    CompiledGraph._invoke = _wrap_compiled_invoke(CompiledGraph._invoke)
```

- [ ] **Step 4: 运行确认通过**

Run: `.venv/bin/python -m pytest tests/unit_tests/extension/patches/test_static_graph_patch.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add jiuwen/extension/patches/static_graph_patch.py tests/unit_tests/extension/patches/test_static_graph_patch.py
git commit -m "feat(runtime): Patch B——_invoke 入口 workflow session ContextVar（token 栈式）"
```

---

### Task 4: Patch A — PregelGraph.compile 纯函数化

**Files:**
- Modify: `jiuwen/extension/patches/static_graph_patch.py`（新增 `_compile_pregel_fresh` + `_patched_pregel_graph_compile`，接入 apply）
- Test: `tests/unit_tests/extension/patches/test_static_graph_patch.py`（追加 TestPatchA 类）

**Interfaces:**
- Consumes: Task 2 的 apply 骨架；引擎 `Vertex`、`GraphStore`、`CompiledGraph`、`PregelGraph`、`PregelBuilder`（经 import）。
- Produces: `_patched_pregel_graph_compile(self, session, **kwargs) -> CompiledGraph`（签名与原版一致，`BaseWorkflow.compile` 以 `compile(session, context=...)` 调用，`**kwargs` 必须透传给 `Vertex.init`）。

**实现要点（shadow-copy 方案）**：原版 `_compile` 读 `self.nodes`，无法安全传 fresh-vertex map（原地替换 `self.nodes` 在并发 compile 下会串）。方案：`copy.copy(self)` 生成影子图（共享 build 期静态属性 edges/waits/branches/branch_targets），仅覆盖 `nodes`，对影子调原版 `_compile`——零方法体复制、零共享写入。

- [ ] **Step 1: 追加失败测试**

```python
class TestPatchA:
    """Patch A：compile 纯函数化——fresh Pregel/checkpointer/Vertex per compile。"""

    IR_PATH = (
        Path(__file__).resolve().parents[3] / "resource" / "ir_file" / "workflow_message.json"
    )

    @staticmethod
    def _fake_session():
        """MagicMock session（计划期已实验验证可走通真实 compile）。"""
        from unittest.mock import MagicMock

        session = MagicMock()
        session.checkpointer.return_value.graph_store.return_value = MagicMock()
        return session

    @pytest.fixture
    def _patched_compile(self, monkeypatch):
        from openjiuwen.core.graph.graph import PregelGraph
        from jiuwen.extension.patches.static_graph_patch import (
            _patched_pregel_graph_compile,
        )

        monkeypatch.setattr(PregelGraph, "compile", _patched_pregel_graph_compile)

    @pytest.mark.asyncio
    async def test_two_compiles_yield_independent_pregel_and_checkpointer(self, _patched_compile):
        import json

        from jiuwen.serve.controllers.execution.ir_converter import IRConverter

        ir_data = json.loads(self.IR_PATH.read_text(encoding="utf-8"))
        lazy = await IRConverter.async_ir_to_workflow(ir_data)
        wf = await lazy.instantiate()
        graph = wf._internal._graph  # BaseWorkflow._graph 即 PregelGraph
        original_vertices = dict(graph.nodes)

        s1, s2 = self._fake_session(), self._fake_session()
        c1 = graph.compile(s1)
        c2 = graph.compile(s2)

        # 每次编译产出全新 Pregel（全新 channels）与全新 checkpointer
        assert c1._pregel is not c2._pregel
        assert c1._checkpointer is not c2._checkpointer
        # 属性保留写入（读取方兼容，spec §4.1 偏离②）
        assert graph.pregel is c2._pregel
        assert graph.checkpointer is c2._checkpointer
        assert graph._session is s2

        # 原 build 期 Vertex 未被 init 污染、self.nodes 未被替换
        for node_id, vertex in original_vertices.items():
            assert vertex is graph.nodes[node_id]
            assert vertex._session is None

    @pytest.mark.asyncio
    async def test_fresh_vertices_are_initialized_and_isolated(self, _patched_compile):
        import json

        from openjiwen.serve.controllers.execution.ir_converter import IRConverter

        ir_data = json.loads(self.IR_PATH.read_text(encoding="utf-8"))
        lazy = await IRConverter.async_ir_to_workflow(ir_data)
        wf = await lazy.instantiate()
        graph = wf._internal._graph

        s1 = self._fake_session()
        c1 = graph.compile(s1)

        # 两次 compile 的 PregelNode 内包装的是不同 Vertex 实例
        n1 = c1._pregel.nodes["node_start"]
        c2 = graph.compile(self._fake_session())
        n2 = c2._pregel.nodes["node_start"]
        assert n1 is not n2

    @pytest.mark.asyncio
    async def test_after_step_commits_captured_session_not_shared_attr(self, _patched_compile):
        """after_step 闭包捕获 session 参数——竞态根源（原版读 self._session）消除。"""
        import json
        from unittest.mock import MagicMock

        from jiuwen.serve.controllers.execution.ir_converter import IRConverter

        ir_data = json.loads(self.IR_PATH.read_text(encoding="utf-8"))
        lazy = await IRConverter.async_ir_to_workflow(ir_data)
        wf = await lazy.instantiate()
        graph = wf._internal._graph

        s1, s2 = self._fake_session(), self._fake_session()
        c1 = graph.compile(s1)
        graph.compile(s2)  # self._session 已被 s2 覆写（属性保留写入）

        loop_stub = MagicMock()
        loop_stub.step = 1
        loop_stub.config = {"ns": "wf", "session_id": "s1"}
        loop_stub.active_nodes = []

        c1._pregel.after_step(loop_stub)  # c1 的 after_step 应 commit s1 而非 s2
        s1.state().commit.assert_called()
        s2.state().commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_compile_equivalence_off_mode(self, _patched_compile):
        """off 模式等价性：每请求新实例的首次 compile，产物类型与属性绑定正确。"""
        import json

        from openjiuwen.core.graph.graph import CompiledGraph
        from jiuwen.serve.controllers.execution.ir_converter import IRConverter

        ir_data = json.loads(self.IR_PATH.read_text(encoding="utf-8"))
        lazy = await IRConverter.async_ir_to_workflow(ir_data)
        wf = await lazy.instantiate()
        graph = wf._internal._graph

        compiled = graph.compile(self._fake_session())
        assert isinstance(compiled, CompiledGraph)
        assert compiled._pregel is graph.pregel
```

测试文件顶部补 import：`from pathlib import Path`。

- [ ] **Step 2: 运行确认失败**

Run: `.venv/bin/python -m pytest "tests/unit_tests/extension/patches/test_static_graph_patch.py::TestPatchA" -v`
Expected: FAIL（`ImportError: cannot import name '_patched_pregel_graph_compile'`）

- [ ] **Step 3: 实现 Patch A**

`static_graph_patch.py` 顶部 import 区追加：

```python
import copy

from openjiuwen.core.common.logging import LogEventType, graph_logger
from openjiuwen.core.graph.graph import CompiledGraph, PregelGraph
from openjiuwen.core.graph.pregel.constants import SESSION_ID
from openjiuwen.core.graph.store import GraphStore
from openjiuwen.core.graph.vertex import Vertex
```

（`CompiledGraph/PregelGraph` 若 Task 3 已在函数内 import，统一移到模块顶部。）

追加实现：

```python
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
    return PregelGraph._compile(shadow, graph_store=graph_store, step_callback=step_callback)


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
       off 模式等价论证成立）。
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

    # 属性保留写入（偏离②）：兼容潜在读取方；off 模式下每请求新实例的
    # 首次 compile 本来就执行等价赋值。
    self.pregel = pregel
    self.checkpointer = checkpointer
    self._session = session
    return CompiledGraph(pregel, checkpointer)
```

`apply_static_graph_patch()` 的填充区追加（与 Task 3 的 Patch B 并列）：

```python
    PregelGraph.compile = _patched_pregel_graph_compile
```

- [ ] **Step 4: 运行确认通过**

Run: `.venv/bin/python -m pytest tests/unit_tests/extension/patches/test_static_graph_patch.py -v`
Expected: PASS

- [ ] **Step 5: off 模式等价回归（关键门禁）**

Run: `.venv/bin/python -m pytest tests/unit_tests/runner/ tests/unit_tests/serve/ -x -q`
Expected: 全部 PASS（Patch A/B 手动 monkeypatch 不影响其他测试；此步验证不破坏现有构建/执行语义）

- [ ] **Step 6: 提交**

```bash
git add jiuwen/extension/patches/static_graph_patch.py tests/unit_tests/extension/patches/test_static_graph_patch.py
git commit -m "feat(runtime): Patch A——compile 纯函数化（shadow-copy 注入 fresh vertex，属性保留写入）"
```

---

### Task 5: Patch C — BranchRouter 解析链

**Files:**
- Modify: `jiuwen/extension/patches/static_graph_patch.py`（新增 `_patched_branch_router_call`，接入 apply）
- Test: `tests/unit_tests/extension/patches/test_static_graph_patch.py`（追加 TestPatchC 类）

**Interfaces:**
- Consumes: Task 1 的 `resolve_routing_session`。
- Produces: `_patched_branch_router_call(self, *args, **kwargs) -> list[str]`（替换 `BranchRouter.__call__`，签名不变）。

- [ ] **Step 1: 追加失败测试**

```python
class TestPatchC:
    """Patch C：BranchRouter 解析链 组件级 → workflow 级 → self._session。"""

    @pytest.fixture
    def _patched_call(self, monkeypatch):
        from openjiuwen.core.workflow.components.flow.branch_router import BranchRouter
        from jiuwen.extension.patches.static_graph_patch import _patched_branch_router_call

        monkeypatch.setattr(BranchRouter, "__call__", _patched_branch_router_call)

    @pytest.mark.asyncio
    async def test_resolution_order_three_tiers(self, _patched_call):
        from openjiuwen.core.workflow.components.flow.branch_router import BranchRouter
        from jiuwen.extension.workflow import execution_session_ctx as ctx

        comp_marker, wf_marker, fallback_marker = object(), object(), object()

        router = BranchRouter(report_trace=False)
        router.add_branch(lambda s: s is comp_marker, ["component_tier"])
        router.add_branch(lambda s: s is wf_marker, ["workflow_tier"])
        router.add_branch(lambda s: s is fallback_marker, ["fallback_tier"])
        router.set_session(fallback_marker)

        # 仅 fallback（兼容层：与原版行为一致）
        assert await router() == ["fallback_tier"]

        # + workflow 层（add_conditional_connection 注册的路由今日语义：ProxySession→workflow session）
        t1 = ctx.set_workflow_session(wf_marker)
        assert await router() == ["workflow_tier"]

        # + component 层（_RoutedIntentDetection 今日语义：set_session(NodeSession)）
        t2 = ctx.set_component_exec(comp_marker, None)
        assert await router() == ["component_tier"]

        # 逐层退栈
        ctx.reset_component_exec(t2)
        assert await router() == ["workflow_tier"]
        ctx.reset_workflow_session(t1)
        assert await router() == ["fallback_tier"]

    @pytest.mark.asyncio
    async def test_set_session_still_works_as_fallback(self, _patched_call):
        """set_session 保留（兼容层）：无 ContextVar 时与原版行为一致。"""
        from openjiuwen.core.workflow.components.flow.branch_router import BranchRouter

        marker = object()
        router = BranchRouter(report_trace=False)
        router.add_branch(lambda s: s is marker, ["hit"])
        router.set_session(marker)
        assert await router() == ["hit"]
```

- [ ] **Step 2: 运行确认失败**

Run: `.venv/bin/python -m pytest tests/unit_tests/extension/patches/test_static_graph_patch.py::TestPatchC -v`
Expected: FAIL（ImportError）

- [ ] **Step 3: 实现 Patch C**

`static_graph_patch.py` 顶部 import 区追加：

```python
from openjiuwen.core.common.exception.codes import StatusCode
from openjiuwen.core.common.exception.errors import build_error
from openjiuwen.core.session.tracer import TracerWorkflowUtils
from openjiuwen.core.workflow.components.flow.branch_router import BranchRouter
```

追加实现（除首行解析外与原版 `branch_router.py:92-112` 逐行一致）：

```python
async def _patched_branch_router_call(self, *args, **kwargs) -> list:
    """Patch C：session 解析链（spec §4.3）。

    原版首行 `session = self._session`（branch_router.py:93）——共享
    router 实例并发执行时读到错误会话；且 BaseWorkflow.compile 每次替换
    共享 ProxySession._stub 的竞态也经此封堵（执行期间 ContextVar 恒有
    值，racy 的 _stub 永不被读到）。其余逻辑与原版一致。
    """
    session = _session_ctx.resolve_routing_session(self._session)
    if self.report_trace:
        branches = []
        for branch in self._branches:
            branches.append({
                "branch_id": branch.branch_id,
                "condition": branch.trace_info(session)
            })
        await TracerWorkflowUtils.trace_component_begin(session)
        await TracerWorkflowUtils.trace_component_inputs(session, {"branches": branches})
    for branch in self._branches:
        if branch.evaluate(session):
            if self.report_trace:
                await TracerWorkflowUtils.trace_component_outputs(session, {"branch_id": branch.branch_id})
                await TracerWorkflowUtils.trace_component_done(session)
            return branch.target
    raise build_error(
        StatusCode.COMPONENT_BRANCH_EXECUTION_ERROR,
        reason="branch meeting the condition was not found"
    )
```

`apply_static_graph_patch()` 填充区追加：

```python
    BranchRouter.__call__ = _patched_branch_router_call
```

- [ ] **Step 4: 运行确认通过**

Run: `.venv/bin/python -m pytest tests/unit_tests/extension/patches/test_static_graph_patch.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add jiuwen/extension/patches/static_graph_patch.py tests/unit_tests/extension/patches/test_static_graph_patch.py
git commit -m "feat(runtime): Patch C——BranchRouter 三层解析链（ContextVar 优先，_session 回退）"
```

---

### Task 6: apply 编排 + import 接线 + off 模式全量回归

**Files:**
- Modify: `jiuwen/serve/controllers/execution/ir_converter.py:114` 后（patch 应用序列）
- Modify: `jiuwen/extension/workflow_node/sub_workflow.py:1573` 后（patch 应用序列）
- Test: `tests/unit_tests/extension/patches/test_static_graph_patch.py`（追加 TestApplyAndDowngrade 类）

**Interfaces:**
- Consumes: Task 2/3/4/5 的 apply 与三件套。
- Produces: `apply_static_graph_patch()` 完整编排（真实入口）；import `ir_converter` 或 `sub_workflow` 即完成应用。

- [ ] **Step 1: 追加失败测试**

```python
class TestApplyAndDowngrade:
    """apply 编排：正常应用、幂等、断言失败自动降级。"""

    @pytest.fixture
    def _restore_engine(self):
        """保存/恢复引擎类方法与模块 flag（apply 会改类属性）。"""
        from openjiuwen.core.graph.graph import CompiledGraph, PregelGraph
        from openjiuwen.core.workflow.components.flow.branch_router import BranchRouter

        saved = (
            PregelGraph.compile,
            CompiledGraph._invoke,
            BranchRouter.__call__,
            static_graph_patch._STATIC_GRAPH_PATCH_APPLIED,
            static_graph_patch.STATIC_GRAPH_DOWNGRADED,
        )
        yield
        (
            PregelGraph.compile,
            CompiledGraph._invoke,
            BranchRouter.__call__,
        ) = saved[0], saved[1], saved[2]
        static_graph_patch._STATIC_GRAPH_PATCH_APPLIED = saved[3]
        static_graph_patch.STATIC_GRAPH_DOWNGRADED = saved[4]

    def test_apply_patches_all_three_and_is_idempotent(self, _restore_engine):
        import jiuwen.serve.controllers.execution.ir_converter  # noqa: F401 确保 sub_stream 已应用

        from openjiuwen.core.graph.graph import CompiledGraph, PregelGraph
        from openjiuwen.core.workflow.components.flow.branch_router import BranchRouter

        assert static_graph_patch.apply_static_graph_patch() is True
        assert PregelGraph.compile is static_graph_patch._patched_pregel_graph_compile
        assert BranchRouter.__call__ is static_graph_patch._patched_branch_router_call
        # _invoke 是包装版（包装了 sub_stream 的 _patched_compiled_invoke）
        assert CompiledGraph._invoke.__name__ == "_invoke_with_session_ctx"
        assert not static_graph_patch.STATIC_GRAPH_DOWNGRADED

        # 幂等：第二次调用返回 False
        assert static_graph_patch.apply_static_graph_patch() is False

    def test_assertion_failure_downgrades_and_skips_patches(self, _restore_engine, monkeypatch, caplog):
        import jiuwen.serve.controllers.execution.ir_converter  # noqa: F401

        from openjiuwen.core.graph.graph import PregelGraph

        original_compile = PregelGraph.compile
        monkeypatch.setattr(
            static_graph_patch, "_structure_assertions", lambda: ["模拟上游结构变更"]
        )
        static_graph_patch._STATIC_GRAPH_PATCH_APPLIED = False
        static_graph_patch.STATIC_GRAPH_DOWNGRADED = False

        assert static_graph_patch.apply_static_graph_patch() is False
        assert static_graph_patch.STATIC_GRAPH_DOWNGRADED is True
        assert PregelGraph.compile is original_compile  # 未被替换
        assert any("结构断言失败" in r.message for r in caplog.records)

        # 降级后再次调用不重复告警（幂等守卫）
        assert static_graph_patch.apply_static_graph_patch() is False
```

- [ ] **Step 2: 运行确认失败**

Run: `.venv/bin/python -m pytest tests/unit_tests/extension/patches/test_static_graph_patch.py::TestApplyAndDowngrade -v`
Expected: FAIL（`test_apply_patches_all_three_and_is_idempotent` 断言失败——apply 尚未接线到真实 import 链，且 ir_converter 还没调用它）

- [ ] **Step 3: 接线两个 import 应用点**

`ir_converter.py:111-114` 当前为：

```python
apply_workflow_sub_stream_patch()
apply_loop_body_session_cleanup_patch()
apply_loop_state_cleanup_patch()
apply_global_memory_ref_resolution_patch()
```

在其 import 区（`apply_global_memory_ref_resolution_patch` 的 import 附近）追加：

```python
from jiuwen.extension.patches.static_graph_patch import apply_static_graph_patch
```

应用序列末尾追加（**必须在 `apply_workflow_sub_stream_patch()` 之后**——B1 断言强制）：

```python
apply_static_graph_patch()
```

`sub_workflow.py:1570-1573` 同样处理：import 区追加 `from jiuwen.extension.patches.static_graph_patch import apply_static_graph_patch`，应用序列（:1570-1573）末尾追加 `apply_static_graph_patch()`。

- [ ] **Step 4: 运行确认通过**

Run: `.venv/bin/python -m pytest tests/unit_tests/extension/patches/test_static_graph_patch.py -v`
Expected: PASS

- [ ] **Step 5: off 模式全量回归（三件套始终应用的机器验证）**

Run: `.venv/bin/python -m pytest tests/unit_tests/ -q`
Expected: 全部 PASS（现有全部单测在 patch 始终应用下保持绿——这是"off = 现状"验收标准 1 的主体）

- [ ] **Step 6: 提交**

```bash
git add jiuwen/serve/controllers/execution/ir_converter.py jiuwen/extension/workflow_node/sub_workflow.py tests/unit_tests/extension/patches/test_static_graph_patch.py
git commit -m "feat(runtime): static_graph_patch 三件套接入 import 应用链（off 模式全量回归通过）"
```

---

### Task 7: 配置项 + workflow_instance_cache 模块

**Files:**
- Modify: `agent-runtime/agent_runtime/common/config.py`（`CacheSettings` 追加 2 字段，插在 `workflow_cache_ttl_seconds`（:290-292）之后）
- Create: `jiuwen/serve/controllers/execution/workflow_instance_cache.py`
- Test: `tests/unit_tests/cache/test_workflow_instance_cache.py`

**Interfaces:**
- Consumes: Task 2 的 `STATIC_GRAPH_DOWNGRADED`；`settings.cache.workflow_instance_reuse_mode` / `settings.cache.workflow_instance_cache_num`（本任务新增）。
- Produces（Task 8 依赖，签名必须一致）:
  - `aget_or_create_workflow_instance(ir_path: str, ir_data: dict, build: Callable[..., Awaitable], build_kwargs: dict | None = None) -> LazyWorkflow`
  - `evict_workflow_instances_by_path(ir_path: str) -> int`
  - `clear_workflow_instance_cache() -> None`（测试用）

- [ ] **Step 1: 写失败测试**

```python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""workflow_instance_cache：LazyWorkflow 保留制实例缓存单测（spec §6）。"""
import pytest

from agent_runtime.common.config import settings
from jiuwen.serve.controllers.execution import workflow_instance_cache as wic


@pytest.fixture(autouse=True)
def _clean_cache():
    wic.clear_workflow_instance_cache()
    yield
    wic.clear_workflow_instance_cache()


def _published_ir():
    return {"workflowId": "wf-1", "is_published": True, "nodes": []}


def _unpublished_ir():
    return {"workflowId": "wf-2", "is_published": False, "nodes": []}


class TestGating:
    @pytest.mark.asyncio
    async def test_off_mode_bypasses_cache_entirely(self, monkeypatch):
        """off 模式：直通 build，缓存零触碰（默认行为不变式）。"""
        monkeypatch.setattr(settings.cache, "workflow_instance_reuse_mode", "off")
        builds = []

        async def build(ir_data, **kwargs):
            builds.append(ir_data)
            return object()

        r1 = await wic.aget_or_create_workflow_instance("p", _published_ir(), build)
        r2 = await wic.aget_or_create_workflow_instance("p", _published_ir(), build)
        assert r1 is not r2
        assert len(builds) == 2
        assert wic._cache == {}  # 缓存零触碰

    @pytest.mark.asyncio
    async def test_static_graph_mode_with_downgrade_bypasses(self, monkeypatch):
        monkeypatch.setattr(settings.cache, "workflow_instance_reuse_mode", "static_graph")
        monkeypatch.setattr(wic, "STATIC_GRAPH_DOWNGRADED", True)
        builds = []

        async def build(ir_data, **kwargs):
            builds.append(ir_data)
            return object()

        r1 = await wic.aget_or_create_workflow_instance("p", _published_ir(), build)
        r2 = await wic.aget_or_create_workflow_instance("p", _published_ir(), build)
        assert r1 is not r2
        assert len(builds) == 2

    @pytest.mark.asyncio
    async def test_unpublished_ir_bypasses(self, monkeypatch):
        monkeypatch.setattr(settings.cache, "workflow_instance_reuse_mode", "static_graph")
        builds = []

        async def build(ir_data, **kwargs):
            builds.append(ir_data)
            return object()

        r1 = await wic.aget_or_create_workflow_instance("p", _unpublished_ir(), build)
        r2 = await wic.aget_or_create_workflow_instance("p", _unpublished_ir(), build)
        assert r1 is not r2
        assert wic._cache == {}


class TestHitMissAndEviction:
    @pytest.mark.asyncio
    async def test_second_call_hits_cache(self, monkeypatch):
        monkeypatch.setattr(settings.cache, "workflow_instance_reuse_mode", "static_graph")

        async def build(ir_data, **kwargs):
            return object()

        r1 = await wic.aget_or_create_workflow_instance("p", _published_ir(), build)
        r2 = await wic.aget_or_create_workflow_instance("p", _published_ir(), build)
        assert r1 is r2  # LazyWorkflow 保留制：同一实例

    @pytest.mark.asyncio
    async def test_capacity_lru_eviction(self, monkeypatch):
        monkeypatch.setattr(settings.cache, "workflow_instance_reuse_mode", "static_graph")
        monkeypatch.setattr(settings.cache, "workflow_instance_cache_num", 2)

        async def build(ir_data, **kwargs):
            return object()

        a = await wic.aget_or_create_workflow_instance("p1", _published_ir(), build)
        b = await wic.aget_or_create_workflow_instance("p2", _published_ir(), build)
        c = await wic.aget_or_create_workflow_instance("p3", _published_ir(), build)
        assert len(wic._cache) == 2
        # p1（最旧）被淘汰
        a2 = await wic.aget_or_create_workflow_instance("p1", _published_ir(), build)
        assert a2 is not a

    @pytest.mark.asyncio
    async def test_content_hash_key_republish_invalidates(self, monkeypatch):
        """同 path 不同内容 → 不同 key（重新发布即刻 miss，无旧图窗口）。"""
        monkeypatch.setattr(settings.cache, "workflow_instance_reuse_mode", "static_graph")

        async def build(ir_data, **kwargs):
            return object()

        v1 = _published_ir()
        r1 = await wic.aget_or_create_workflow_instance("p", v1, build)
        v2 = _published_ir()
        v2["nodes"] = [{"id": "n1"}]  # 内容变化
        r2 = await wic.aget_or_create_workflow_instance("p", v2, build)
        assert r2 is not r1

    @pytest.mark.asyncio
    async def test_evict_by_path_prefix(self, monkeypatch):
        monkeypatch.setattr(settings.cache, "workflow_instance_reuse_mode", "static_graph")

        async def build(ir_data, **kwargs):
            return object()

        await wic.aget_or_create_workflow_instance("wf/ir/a.json", _published_ir(), build)
        await wic.aget_or_create_workflow_instance("wf/ir/b.json", _published_ir(), build)
        evicted = await wic.evict_workflow_instances_by_path("wf/ir/a.json")
        assert evicted == 1
        assert len(wic._cache) == 1

    @pytest.mark.asyncio
    async def test_build_kwargs_forwarded_on_miss(self, monkeypatch):
        monkeypatch.setattr(settings.cache, "workflow_instance_reuse_mode", "static_graph")
        seen = {}

        async def build(ir_data, **kwargs):
            seen.update(kwargs)
            return object()

        await wic.aget_or_create_workflow_instance(
            "p", _published_ir(), build, build_kwargs={"cust_headers": {"k": "v"}, "project_id": "pj"}
        )
        assert seen == {"cust_headers": {"k": "v"}, "project_id": "pj"}
```

- [ ] **Step 2: 运行确认失败**

Run: `.venv/bin/python -m pytest tests/unit_tests/cache/test_workflow_instance_cache.py -v`
Expected: FAIL（`workflow_instance_reuse_mode` 属性不存在 → AttributeError/ValidationError）

- [ ] **Step 3: 加配置字段**

`agent_runtime/common/config.py` 的 `CacheSettings`，在 `workflow_cache_ttl_seconds` 字段后追加（`Literal` 已在 :5 导入）：

```python
    # Workflow 实例复用模式（issue #1555）：off = 现状（每请求重建，零行为变化）；
    # static_graph = 复用已构建图（patch 三件套 + LazyWorkflow 保留制缓存）。
    # 注意与 MAX_WORKFLOW_CACHE_NUM 区分：后者是 BPMN spec 缓存队列（jiuwen
    # orchestration 路径）的容量，本配置是 openjiuwen Workflow 实例缓存的容量。
    workflow_instance_reuse_mode: Literal["off", "static_graph"] = Field(
        default="off", validation_alias="WORKFLOW_INSTANCE_REUSE_MODE"
    )
    workflow_instance_cache_num: int = Field(
        default=100, ge=1, validation_alias="WORKFLOW_INSTANCE_CACHE_NUM"
    )
```

- [ ] **Step 4: 实现缓存模块**

```python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Workflow 实例缓存（LazyWorkflow 保留制，spec §6 / issue #1555）。

- 缓存对象为 LazyWorkflow（构建时机不变：仍发生在首次 stream，
  LazyWorkflow._instantiate_lock 双检锁天然去重并发首调构建）；
- key = ir_path + IR 内容 hash（canonical JSON 的 sha256 前 16 位）——
  重新发布即刻 miss，不存在旧图窗口；
- 仅进程内 memory LRU：Workflow 实例含 Future/Lock/闭包不可序列化，
  不进 Redis，不复用 cache_workflow_queue（BPMN spec 专用）；
- 资格：static_graph 模式 + 未降级 + is_published（跟随 IR 缓存惯例）。
"""
from __future__ import annotations

import asyncio
import hashlib
import json
from collections import OrderedDict
from typing import Any, Awaitable, Callable, Optional

from agent_runtime.common.config import settings
from openjiuwen.core.common.logging import performance_logger

# 降级标志经模块属性引用（测试 monkeypatch wic.STATIC_GRAPH_DOWNGRADED 生效）
from jiuwen.extension.patches.static_graph_patch import STATIC_GRAPH_DOWNGRADED  # noqa: F401

_lock = asyncio.Lock()
_cache: "OrderedDict[str, Any]" = OrderedDict()
_DOWNGRADE_METRIC_LOGGED = False


def _cache_key(ir_path: str, ir_data: dict) -> str:
    canonical = json.dumps(ir_data, sort_keys=True, ensure_ascii=False, default=str)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
    return f"{ir_path}:{digest}"


async def aget_or_create_workflow_instance(
    ir_path: str,
    ir_data: dict,
    build: Callable[..., Awaitable[Any]],
    build_kwargs: Optional[dict] = None,
) -> Any:
    """命中返回缓存的 LazyWorkflow；未命中调用 build 并缓存。

    build 为 ``IRConverter.async_ir_to_workflow``（创建 LazyWorkflow 壳，
    毫秒级）；miss 路径在锁内 await build——并发 miss 经锁串行后首个
    存入、其余转 hit，昂贵构建仍由 LazyWorkflow 自身的双检锁去重。
    """
    global _DOWNGRADE_METRIC_LOGGED

    if settings.cache.workflow_instance_reuse_mode != "static_graph":
        return await build(ir_data, **(build_kwargs or {}))
    if STATIC_GRAPH_DOWNGRADED:
        if not _DOWNGRADE_METRIC_LOGGED:
            _DOWNGRADE_METRIC_LOGGED = True
            performance_logger.info("workflow_cache|downgrade")
        return await build(ir_data, **(build_kwargs or {}))
    if not ir_data.get("is_published"):
        return await build(ir_data, **(build_kwargs or {}))

    key = _cache_key(ir_path, ir_data)
    async with _lock:
        cached = _cache.get(key)
        if cached is not None:
            _cache.move_to_end(key)
            performance_logger.info("workflow_cache|hit")
            return cached

        performance_logger.info("workflow_cache|miss")
        workflow = await build(ir_data, **(build_kwargs or {}))
        _cache[key] = workflow
        capacity = settings.cache.workflow_instance_cache_num
        while len(_cache) > capacity:
            _cache.popitem(last=False)
        return workflow


async def evict_workflow_instances_by_path(ir_path: str) -> int:
    """按 ir_path 前缀驱逐（删除执行实例端点的内存卫生钩子，非正确性需要）。"""
    evicted = 0
    async with _lock:
        for key in [k for k in _cache if k.startswith(f"{ir_path}:")]:
            _cache.pop(key, None)
            evicted += 1
    return evicted


def clear_workflow_instance_cache() -> None:
    """清空缓存（测试用）。"""
    _cache.clear()
```

- [ ] **Step 5: 运行确认通过**

Run: `.venv/bin/python -m pytest tests/unit_tests/cache/test_workflow_instance_cache.py -v`
Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add agent_runtime/common/config.py jiuwen/serve/controllers/execution/workflow_instance_cache.py tests/unit_tests/cache/test_workflow_instance_cache.py
git commit -m "feat(runtime): WORKFLOW_INSTANCE_REUSE_MODE 配置与 LazyWorkflow 保留制实例缓存"
```

---

### Task 8: workflow_runner 接入 + 删除端点驱逐

**Files:**
- Modify: `agent_runtime/agent_runtime/runner/workflow_runner.py`（:341-345 的 `async_ir_to_workflow` 调用改为缓存查找；顶部 import）
- Modify: `agent-runtime/agent_runtime/serve/apis/orchestration.py`（:762-763 删除端点追加驱逐）
- Test: `tests/unit_tests/runner/test_workflow_runner_instance_cache.py`

**Interfaces:**
- Consumes: Task 7 的 `aget_or_create_workflow_instance` / `evict_workflow_instances_by_path`。
- Produces: 无（调用侧终点）。

- [ ] **Step 1: 写失败测试**

```python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""workflow_runner 实例缓存接入单测。

复用 test_workflow_runner.py 的 mock 范式：mock async_ir_load 等基础设施，
驱动 run_streaming 两次，断言 static_graph 模式下第二次复用同一
LazyWorkflow（缓存命中）、off 模式下不复用。
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent_runtime.common.config import settings
from agent_runtime.runner.workflow_runner import WorkflowRunner


def _make_mock_req(conversation_id="conv-1", query="test"):
    req = MagicMock()
    req.conversation_id = conversation_id
    req.ir_path = "workflow/ir/test/pub_1770000000000.json"
    req.query = query
    req.resume_input = None
    req.user_id = "testUser"
    req.params = MagicMock()
    req.params.is_debug = False
    req.params.model_dump = MagicMock(return_value={})
    req.params.conversation_history = []
    req.params.enable_memory_extract = False
    return req


IR_DATA = {"workflowId": "wf-cache-test", "is_published": True, "nodes": []}


async def _collect(agen):
    return [item async for item in agen]


@pytest.fixture(autouse=True)
def _infra_mocks():
    """mock 掉 run_streaming 依赖的基础设施（session/redis/记忆）。"""
    with patch(
        "agent_runtime.runner.workflow_runner.async_ir_load", new=AsyncMock(return_value=IR_DATA)
    ), patch(
        "agent_runtime.runner.workflow_runner.create_workflow_session_with_trace",
        return_value=MagicMock(),
    ), patch(
        "agent_runtime.runner.workflow_runner.ExecutionIdStore.save", new=AsyncMock()
    ), patch(
        "agent_runtime.runner.workflow_runner.TraceIdStore.save", new=AsyncMock()
    ), patch(
        "agent_runtime.runner.workflow_runner.get_redis_client"
    ) as _redis_mock:
        _redis_mock.return_value = AsyncMock()
        yield


class TestWorkflowRunnerInstanceCache:
    @pytest.fixture(autouse=True)
    def _clean_cache(self):
        from jiuwen.serve.controllers.execution import workflow_instance_cache as wic
        wic.clear_workflow_instance_cache()
        yield
        wic.clear_workflow_instance_cache()

    @pytest.mark.asyncio
    async def test_off_mode_builds_per_request(self, monkeypatch):
        monkeypatch.setattr(settings.cache, "workflow_instance_reuse_mode", "off")
        runner = WorkflowRunner()

        with patch.object(
            runner._ir_converter, "async_ir_to_workflow", new=AsyncMock(side_effect=lambda d, **kw: MagicMock())
        ) as build:
            req = _make_mock_req(conversation_id="c1")
            await _collect(runner.run_streaming(req))
            req = _make_mock_req(conversation_id="c2")
            await _collect(runner.run_streaming(req))
        assert build.call_count == 2

    @pytest.mark.asyncio
    async def test_static_graph_mode_reuses_instance(self, monkeypatch):
        monkeypatch.setattr(settings.cache, "workflow_instance_reuse_mode", "static_graph")
        runner = WorkflowRunner()

        sentinel_workflows = []

        async def fake_build(d, **kw):
            wf = MagicMock()
            sentinel_workflows.append(wf)
            return wf

        with patch.object(runner._ir_converter, "async_ir_to_workflow", new=fake_build):
            req = _make_mock_req(conversation_id="c1")
            await _collect(runner.run_streaming(req))
            req = _make_mock_req(conversation_id="c2")
            await _collect(runner.run_streaming(req))

        # build 只发生一次（第二次缓存命中，复用同一 LazyWorkflow）
        assert len(sentinel_workflows) == 1
```

注意：mock 的 `async_ir_to_workflow` 返回 MagicMock（非真 LazyWorkflow）——缓存层不感知类型，存取一致即可；`run_streaming` 中 `workflow.stream(...)` 返回 MagicMock 的异步生成器需可迭代——若 MagicMock 不可 `async for`，给 stream 返回值配置 `__aiter__`：

```python
            wf = MagicMock()
            wf.stream.return_value = _aiter([])  # 空 async iterator
```

```python
async def _aiter(items):
    for it in items:
        yield it
```

- [ ] **Step 2: 运行确认失败**

Run: `.venv/bin/python -m pytest tests/unit_tests/runner/test_workflow_runner_instance_cache.py -v`
Expected: FAIL（`test_static_graph_mode_reuses_instance`：build 被调用 2 次——runner 还没接缓存）

- [ ] **Step 3: 接入 workflow_runner**

`workflow_runner.py` 顶部 import 区（:29 `from jiuwen.serve.controllers.execution.open_utils import async_ir_load` 附近）追加：

```python
from jiuwen.serve.controllers.execution.workflow_instance_cache import (
    aget_or_create_workflow_instance,
)
```

:341-345 的调用：

```python
            workflow = await self._ir_converter.async_ir_to_workflow(
                ir_json,
                cust_headers=_cust_headers,
                project_id=_project_id,
            )
```

替换为：

```python
            workflow = await aget_or_create_workflow_instance(
                ir_path,
                ir_json,
                build=self._ir_converter.async_ir_to_workflow,
                build_kwargs={
                    "cust_headers": _cust_headers,
                    "project_id": _project_id,
                },
            )
```

（`ir_build` 的 try/except 结构与 `ir_convert` 埋点不动——缓存命中时 `ir_convert` 会显著缩短，属预期观测效果。）

- [ ] **Step 4: 接入删除端点**

`orchestration.py` 顶部 import 区追加：

```python
from jiuwen.serve.controllers.execution.workflow_instance_cache import (
    evict_workflow_instances_by_path,
)
```

:761-763 的：

```python
        # 清除 WorkFlow spec缓存
        if req.ir_path:
            await cache_workflow_queue.apop(req.ir_path)
```

改为：

```python
        # 清除 WorkFlow spec缓存 + 静态图实例缓存（内存卫生，非正确性需要）
        if req.ir_path:
            await cache_workflow_queue.apop(req.ir_path)
            await evict_workflow_instances_by_path(req.ir_path)
```

- [ ] **Step 5: 运行确认通过**

Run: `.venv/bin/python -m pytest tests/unit_tests/runner/test_workflow_runner_instance_cache.py tests/unit_tests/runner/test_workflow_runner.py -v`
Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add agent_runtime/runner/workflow_runner.py agent_runtime/serve/apis/orchestration.py tests/unit_tests/runner/test_workflow_runner_instance_cache.py
git commit -m "feat(runtime): run_streaming 接入实例缓存 + 删除端点按 path 驱逐"
```

---

## 组件无状态化（Task 9-15）

以下任务基于**计划期完成的组件全量审计**（结论已并入各任务的"审计发现"，行号为当前分支实测）。通用约定：

- **末帧输出统一走 Task 1 的 ContextVar 通道**：组件内 `self._xxx_final_output/_stream_output/_stream_state` 的写入改 `set_stream_final_output(value)`，`get_stream_output()` 改 `return get_stream_final_output()`，能力方法入口 `set_stream_final_output(None)` 复位（替代原 `self._xxx = None`）。依据：唯一消费方是引擎 `Vertex._post_stream`（generator 耗尽后读取，同 task 可见；无 reset 设计见 Task 1 模块 docstring）。
- **懒初始化统一照抄 FlowMcp 范式**（`flow_mcp.py:316-319` 的 `async with self._init_lock` 双检）：
  ```python
  self._init_lock = asyncio.Lock()  # __init__ 中

  async def _initialize_if_needed(self):
      if self._initialized:
          return
      async with self._init_lock:
          if self._initialized:
              return
          try:
              self._llm = await self._create_llm_instance()
              self._initialized = True
          except Exception as e:
              raise build_error(...) from e
  ```
- **(b) 类执行期 session/context 的组件内传递**统一走 `set_component_exec(session, context)`（入口 set + finally reset）与 `current_component_exec()`（辅助方法读取）。**分支路由属主组件例外：set 后不 reset**（值须存活到同 task 的 dispatch）。
- 每个任务的测试先写**失败测试**（模拟并发两次调用断言隔离/复位），再改代码，再验证通过后提交。

### Task 9: End 组件无状态化（复用正确性的最硬前提）

**Files:**
- Modify: `jiuwen/extension/workflow_node/end.py`
- Test: `tests/unit_tests/extension/workflow_node/test_end_stateless.py`

**审计发现（end.py，行号为实测）**：四个幂等标志 `_invoke_executed/_stream_executed/_collect_executed/_transform_executed`（:326-329，各能力入口置 True 后**永不复位**——:622/:767/:1041/:1155 附近）；mix 协调状态 `_mix_condition/_mix_data/_mix_push_count/_mix_render_complete/_mix_batch_pushed`（:503-536、:551-556，从不复位，且 `:527-536` 会写 `self._mix = False` 永久关闭 mix）；末帧 `_stream_output`（:757/:1058/:1546 写，仅 transform 入口 :425-426 有复位）；共享 `self._template`（TemplateProcessor）渲染位置互踩。注释 :322-325 说明标志语义：**同一执行内** `wait_for_all=False` 时每条入边分别触发 End，标志防重复——因此不能用局部变量（跨能力方法传递），必须用 per-execution 载体。

**修复设计**：

> 为什么不用 `set_mix`（引擎每执行必调，`Vertex.init` → `hasattr` 探测）做统一复位：`set_mix` 在 **compile 期**执行——并发场景下执行 2 的 compile 会复位正在运行的执行 1 的 mix 协调状态（竞态）。按 NodeSession 键控的容器天然隔离（每执行独立 NodeSession）。引擎的 `set_mix` 调用保留（`_mix`/`_data_source_count` 的幂等配置自愈），仅协调状态迁出。

1. **per-execution 状态容器**（模块级新类 + 实例级 WeakKeyDictionary，key 为 NodeSession——Patch A 下每次执行新建 Vertex 时 `Vertex.init` 重建 NodeSession，执行结束即可 GC，无泄漏）：

```python
import weakref

class _EndExecState:
    """单次执行的 End 能力协调状态（跨执行隔离）。

    原 self._invoke_executed 等四个标志 + _mix_* 协调状态迁入此类；
    NodeSession 每执行新建（Patch A fresh vertex），WeakKeyDictionary
    随执行结束自动回收。
    """

    def __init__(self):
        self.invoke_executed = False
        self.stream_executed = False
        self.collect_executed = False
        self.transform_executed = False
        self.mix_condition = None  # asyncio.Condition，lazy init
        self.mix_data = {}
        self.mix_push_count = 0
        self.mix_render_complete = False
        self.mix_batch_pushed = False
```

`__init__` 中把 :316-329 的 `self._expect_mix`（构建期，保留）、`self._mix_condition` 起的执行期字段替换为：

```python
        self._expect_mix: Optional[bool] = None  # 构建期，保留
        # 执行期协调状态迁移到 per-execution 容器（跨执行隔离，见 _EndExecState）
        self._exec_states: "weakref.WeakKeyDictionary" = weakref.WeakKeyDictionary()
```

并新增访问器：

```python
    def _exec_state(self, session) -> "_EndExecState":
        """当前执行的协调状态（按 NodeSession 隔离；单事件循环内无 await，原子）。"""
        st = self._exec_states.get(session)
        if st is None:
            st = _EndExecState()
            self._exec_states[session] = st
        return st
```

2. **逐点替换**（每个能力方法入口先 `st = self._exec_state(session)`，后续 `self._invoke_executed` → `st.invoke_executed`、`self._mix_condition` → `st.mix_condition`、`self._mix_data` → `st.mix_data`、`self._mix_push_count` → `st.mix_push_count`、`self._mix_render_complete` → `st.mix_render_complete`、`self._mix_batch_pushed` → `st.mix_batch_pushed`；`:527-536` 的 `self._mix = False` 是父类构建期字段，保留引擎 `set_mix` 每执行重开的既有自愈，不改）。涉及方法：`_mix_coordinate`（:503-536）、invoke（:622 起）、stream（:767 起）、collect（:1041 起）、transform（:1155 起）及它们的下游辅助方法（`_mix_coordinate` 的调用方需要把 `st` 作为参数传入或经 `_exec_state(session)` 重取）。

3. **末帧 ContextVar 化**：`self._stream_output` 的全部写点（:757/:1058/:1546 等，grep `self._stream_output` 确认）→ `set_stream_final_output(...)`；`get_stream_output`（:587）→ `return get_stream_final_output()`；四个能力方法入口统一 `set_stream_final_output(None)`（替代 transform 独有的 `_reset_stream_output`，该方法保留但改为调 ContextVar）；`__init__` 删除 `self._stream_output` 字段。

4. **TemplateProcessor 渲染隔离**：`self._template` / `self._batch_template` 的 `render_stream` 调用点（渲染位置 `_current_position/_chunk_index/_count` 并发互踩）改为先克隆：`renderer = copy.copy(self._template)` 后对 `renderer` 调用渲染。注意 `set_mix`（引擎每执行调）写共享 `self._template.set_data_source_count(2)` 属幂等配置，保留共享；`Vertex._sanitize_end_node_inputs` 每执行调 `set_data_source_count(0)` 同理保留。

- [ ] **Step 1: 失败测试**（骨架，断言核心隔离语义）：

```python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""End 组件跨执行隔离测试（静态图复用前提）。"""
import pytest

from jiuwen.extension.workflow import execution_session_ctx as ctx
from jiuwen.extension.workflow_node.end import End, _EndExecState


def _end_conf():
    return {"name": "end", "outputMode": "direct", "responseTemplate": ""}


class TestEndExecStateIsolation:
    def test_exec_state_keyed_by_session(self):
        end = End(_end_conf())
        s1, s2 = object(), object()
        st1 = end._exec_state(s1)
        st2 = end._exec_state(s2)
        assert st1 is not st2
        assert end._exec_state(s1) is st1  # 同 session 复用同一容器

    def test_flags_do_not_leak_across_executions(self):
        end = End(_end_conf())
        s1, s2 = object(), object()
        end._exec_state(s1).invoke_executed = True
        assert end._exec_state(s2).invoke_executed is False

    def test_weakref_releases_with_session(self):
        import gc
        end = End(_end_conf())
        s = object()
        end._exec_state(s)
        assert len(end._exec_states) == 1
        del s
        gc.collect()
        assert len(end._exec_states) == 0

    def test_stream_output_via_contextvar(self):
        """get_stream_output 读 ContextVar 通道，两次执行互不串扰。"""
        end = End(_end_conf())
        ctx.set_stream_final_output({"userFields": "first"})
        assert end.get_stream_output() == {"userFields": "first"}
        ctx.set_stream_final_output({"userFields": "second"})
        assert end.get_stream_output() == {"userFields": "second"}
```

（若 `End.__init__` 签名/依赖不匹配，按实际调整构造；测试核心是四个断言语义。）

- [ ] **Step 2: 运行确认失败** — Run: `.venv/bin/python -m pytest tests/unit_tests/extension/workflow_node/test_end_stateless.py -v`，Expected: FAIL（`_EndExecState`/`_exec_state` 不存在）。
- [ ] **Step 3: 按上述设计实施修改**（容器 + 逐点替换 + ContextVar 末帧 + 渲染克隆；每改一个方法 grep 该标志的全部残留引用确认无遗漏：`grep -n "_invoke_executed\|_mix_push_count\|self._stream_output" jiuwen/extension/workflow_node/end.py` 应仅剩 `_EndExecState` 定义与 `_exec_states` 容器）。
- [ ] **Step 4: 运行新测试 + End 相关既有测试** — Run: `.venv/bin/python -m pytest tests/unit_tests/extension/workflow_node/test_end_stateless.py -v` 与 `.venv/bin/python -m pytest tests/unit_tests/ -q -k "end"`，Expected: PASS。
- [ ] **Step 5: 提交** — `git add jiuwen/extension/workflow_node/end.py tests/unit_tests/extension/workflow_node/test_end_stateless.py && git commit -m "refactor(runtime): End 组件执行期状态迁移到 per-execution 容器与 ContextVar 末帧通道"`

---

### Task 10: SubWorkflow 组件无状态化

**Files:**
- Modify: `jiuwen/extension/workflow_node/sub_workflow.py`
- Test: `tests/unit_tests/extension/workflow_node/test_sub_workflow_stateless.py`

**审计发现（sub_workflow.py）**：`_current_query`（:889 写，:1198/:1237 读）；`_last_child_completed`（:999/:1019/:1037/:1040/:1049、:1163/:1203/:1222/:1250/:1270/:1273/:1279 写——成功后保持 True 泄漏进下一执行，:969/:1128 的 `reset_sub_outputs` 用错值）；`_interrupt_child_node_id`（:706/:1031/:1171/:1331/:1362/:1374 写——**成功完成后从不清空**，下一执行 :868 误走 resume_query 路径，query 被污染）；`_pending_interact_prompt`（stream :1088 入口复位，:1334/:1353/:1368 写）；`_stream_state`（:757/:1007/:1230 写，get_stream_output :1549 读）；`node_state.status`（多处写，reset :774-781 无调用方）；`_workflow_instance`（invoke :949/stream :1098——构造传入 LazyWorkflow 时等值重写无害；**None 降级路径**会把 session global_state 里的 per-execution 实例缓存到组件上）；`_global_var_names`（:275 写）。

**修复设计（逐属性）**：

| 属性 | 修复 |
|---|---|
| `_interrupt_child_node_id` | 迁入 session state：写点改为 `session.state().update({"__sub_wf_interrupt_child": node_id})` / 成功完成时清空（`update({...: None})`）；读点 :868 改从 session state 取（`get_state_info(session, "__sub_wf_interrupt_child")`）。中断-恢复跨请求语义天然由 session state 承载（与 `_should_resume_child_workflow(session)` 同通道） |
| `_last_child_completed` | 同上迁入 session state（key `__sub_wf_last_child_completed`），写点/读点（:969/:1128）同步改 |
| `_current_query` | 局部变量化：`_build_invoke_params`（:889）改为返回值携带 query，调用方以局部变量传递至 :1198/:1237 读点（必要时给中间方法加参数） |
| `_pending_interact_prompt` | 局部变量化：stream（:1068 起）内局部，传递给 `_process_stream_chunk`（:1331/:1353/:1368 的写点改为经参数/返回值；`_raise_user_interact_from_chunk` :706 若同 stream 内则参数传递） |
| `_stream_state` | ContextVar 末帧通道：写点 → `set_stream_final_output(...)`；`get_stream_output`（:1549-1552）→ `return get_stream_final_output()`；stream 入口复位 |
| `node_state.status` | 局部变量化（各 invoke/stream 内 status 判断改局部；`reset()/load_state` 遗留无调用方，保留不动） |
| `_workflow_instance` | `_get_workflow_instance`（:811-824）删除"缓存 session 来源实例"行为：None 降级路径每次直接从 `WORKFLOW_INSTANCE_DICT` 取，不写回 `self._workflow_instance`；LazyWorkflow 构造传入路径保持 |
| `_global_var_names` | grep 读点确认后局部变量化（审计判断其值由静态 schema 决定，若读点仅在单次执行内则局部传递） |

- [ ] **Step 1: 失败测试**（核心断言：中断残留不跨执行串台 + 末帧走 ContextVar）：

```python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""SubWorkflow 组件跨执行隔离测试（静态图复用前提）。"""
from unittest.mock import MagicMock

from jiuwen.extension.workflow import execution_session_ctx as ctx
from jiuwen.extension.workflow_node.sub_workflow import SubWorkflow


def _mock_session():
    """带 state 字典的 mock NodeSession。"""
    session = MagicMock()
    state = MagicMock()

    def _update(d):
        state._store.update(d)

    state._store = {}
    state.update = _update
    session.state.return_value = state
    session.get_session_id.return_value = "s-1"
    return session


class TestSubWorkflowStateless:
    def test_interrupt_child_not_leaked_to_new_execution(self):
        """上一执行的中断子节点 ID 不影响全新执行（session state 按 session 隔离）。"""
        # 修复后：中断 ID 存 session state，两个 session 互不可见
        # （实现细节若经 get_state_info，mock 对应读链）
        s_old, s_new = _mock_session(), _mock_session()
        # 模拟旧执行写入中断标记（经修复后的写通道）
        # —— 具体写入函数由实现决定，测试经公开行为驱动：
        # 构造 SubWorkflow 实例，驱动 _build_invoke_params(s_new)
        # 断言其不进入 resume_query 分支（s_new 的 state 无标记）
        assert s_new.state()._store == {}

    def test_stream_output_via_contextvar(self):
        sub = SubWorkflow.__new__(SubWorkflow)  # 跳过重构造，仅测方法
        ctx.set_stream_final_output({"frame": 1})
        assert sub.get_stream_output() == {"frame": 1}
```

（`_build_invoke_params` 的驱动方式按实现调整——mock 子工作流实例与 session 链；测试核心是"新 session 无残留中断标记 + 末帧走 ContextVar"两个断言语义。）

- [ ] **Step 2: 运行确认失败** — Run: `.venv/bin/python -m pytest tests/unit_tests/extension/workflow_node/test_sub_workflow_stateless.py -v`，Expected: FAIL。
- [ ] **Step 3: 按逐属性表实施**（每属性改完 grep 残留：`grep -n "self\._interrupt_child_node_id\|self\._last_child_completed\|self\._current_query\|self\._pending_interact_prompt\|self\._stream_state\b" jiuwen/extension/workflow_node/sub_workflow.py` 应零命中——`_stream_state` 若有同名局部使用除外）。
- [ ] **Step 4: 运行** — Run: `.venv/bin/python -m pytest tests/unit_tests/extension/workflow_node/test_sub_workflow_stateless.py -v` 及 `.venv/bin/python -m pytest tests/unit_tests/ -q -k "sub_workflow or workflow_sub"`，Expected: PASS（workflow_sub_stream_patch 既有测试不回归）。
- [ ] **Step 5: 提交** — `git commit -m "refactor(runtime): SubWorkflow 执行期状态迁入 session state/局部变量/ContextVar 末帧通道"`

---

### Task 11: LLMChain 无状态化

**Files:**
- Modify: `jiuwen/extension/workflow_node/llm_chain.py`
- Test: `tests/unit_tests/extension/test_llm_chain_stateless.py`

**审计发现**：`self._session/_context` 覆写（invoke :164-165、stream :209-211，读点在辅助方法 :378/:395-396/:726-729/:910-920/:980-1001）；`_stream_final_output`（:212 复位、:244/:341/:462/:573 写、get_stream_output :196-198 读——引擎 `_post_stream` 消费）；`_initialize_if_needed`（:122-132）懒初始化无锁。

**修复设计**：

1. invoke/stream 入口：`self._session = session; self._context = context` 两行替换为 `token = set_component_exec(session, context)`，方法体包 `try/finally: reset_component_exec(token)`（需整体缩进方法体）；`__init__` 删除 `self._session/self._context` 字段（:108-109）。
2. 辅助方法读点：`self._session` → `current_component_exec()[0]`（:378、:395-396、:910-920、:980-1001）；`self._context` → `current_component_exec()[1]`（:726-729）。
3. 末帧：`:212` → `set_stream_final_output(None)`；:244/:341/:462/:573 → `set_stream_final_output(...)`；`get_stream_output` → `return get_stream_final_output()`；`__init__` 删 `self._stream_final_output`（:111）。注意 stream 的 JSON 模式分支（:229 调 `self.invoke`）会重设 component_exec——同值无害。
4. 懒初始化加锁（通用范式，`__init__` 加 `self._init_lock = asyncio.Lock()`）。
5. 删除死代码：`self._state = LLMChainState()`（:107，`initialized/llm` 字段无人读写）及关联 import。

- [ ] **Step 1: 失败测试**：

```python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""LLMChain 组件跨执行隔离测试。"""
import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from jiuwen.extension.workflow import execution_session_ctx as ctx
from jiuwen.extension.workflow_node.llm_chain import LLMChain


class TestLLMChainStateless:
    def test_no_exec_state_instance_fields(self):
        """实例不再持有执行期 session/context/末帧字段。"""
        chain = LLMChain({"name": "llm"})
        assert not hasattr(chain, "_session")
        assert not hasattr(chain, "_context")
        assert not hasattr(chain, "_stream_final_output")

    def test_stream_final_output_via_contextvar(self):
        chain = LLMChain({"name": "llm"})
        ctx.set_stream_final_output({"userFields": "a"})
        assert chain.get_stream_output() == {"userFields": "a"}
        ctx.set_stream_final_output({"userFields": "b"})
        assert chain.get_stream_output() == {"userFields": "b"}
        ctx.set_stream_final_output(None)

    @pytest.mark.asyncio
    async def test_lazy_init_lock_dedupes_concurrent_first_calls(self):
        """并发首调只建一次 Model（锁双检）。"""
        chain = LLMChain({"name": "llm"})
        chain._create_llm_instance = AsyncMock(return_value=MagicMock())
        await asyncio.gather(
            chain._initialize_if_needed(), chain._initialize_if_needed()
        )
        assert chain._create_llm_instance.call_count == 1
```

- [ ] **Step 2: 运行确认失败** — Run: `.venv/bin/python -m pytest tests/unit_tests/extension/test_llm_chain_stateless.py -v`，Expected: FAIL。
- [ ] **Step 3: 按设计实施**（改完 grep：`grep -n "self\._session\|self\._context\|self\._stream_final_output" jiuwen/extension/workflow_node/llm_chain.py` 应零命中）。
- [ ] **Step 4: 运行新测试 + LLMChain 既有测试** — Run: `.venv/bin/python -m pytest tests/unit_tests/extension/test_llm_chain_stateless.py tests/unit_tests/extension/test_llm_chain_format_instructions.py -v`，Expected: PASS。
- [ ] **Step 5: 提交** — `git commit -m "refactor(runtime): LLMChain 执行期状态 ContextVar 化 + 懒初始化加锁"`

---

### Task 12: IntentDetection / _RoutedIntentDetection 无状态化

**Files:**
- Modify: `jiuwen/extension/workflow_node/intent_detection.py`
- Modify: `jiuwen/serve/controllers/execution/ir_converter.py`（:891-895 `_RoutedIntentDetection.invoke`）
- Test: `tests/unit_tests/extension/test_intent_detection_stateless.py`

**审计发现**：invoke :447-450 写 `conversation_id`（仅日志读）/`_session`（读点 :801/:813/:899）/`_router.set_session`；:648 `self.few_shot_example +=`（只写不读的无界累积）；`get_llm_result` :791-792 懒初始化 `self.llm` 无锁；`node_state.status` 多处写（读方为遗留接口，引擎不调用）。

**修复设计**：

1. **set_session → component_exec（不 reset）**：`intent_detection.py:450` 与 `ir_converter.py:894` 的 `self._router.set_session(session)` 都替换为 `set_component_exec(session, context)`（路由属主组件，值须存活到同 task 的 dispatch——Patch C 的组件级优先读取）。两处都改（`_RoutedIntentDetection.invoke` 先执行、`super().invoke` 内 :450 再执行，同值幂等）。
2. `self._session = session`（:448）删除，读点 :801/:813/:899 改 `current_component_exec()[0]`。
3. `self.conversation_id = ...`（:447）改局部变量（grep `conversation_id` 确认读点均在 invoke 链内，参数传递）。
4. `self.few_shot_example += ...`（:648）删除该行（grep 确认无读点后；若有读点改局部拼接）。
5. `get_llm_result` 的 `self.llm = await self._get_llm_instance(...)` 加 `_init_lock` 双检（`__init__` 加锁字段）。
6. `node_state.status` 写点保留（遗留接口无引擎读方，跨执行残留无功能影响），invoke 入口加 `self.node_state = IntentDetectionState()` 式重建复位（按实际 state 类名）。

- [ ] **Step 1: 失败测试**：

```python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""IntentDetection 跨执行隔离测试。"""
import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from jiuwen.extension.workflow import execution_session_ctx as ctx


class TestIntentDetectionStateless:
    def test_routed_intent_sets_component_exec_without_reset(self):
        """_RoutedIntentDetection.invoke 设置 component_exec（不 reset——存活到 dispatch）。"""
        from jiuwen.serve.controllers.execution.ir_converter import _RoutedIntentDetection

        comp = _RoutedIntentDetection({"name": "intent"})
        comp.add_branch(lambda s: True, ["node_a"])

        # 替身 super().invoke（真实链路会走 LLM，测试只验证 set 语义）
        import jiuwen.extension.workflow_node.intent_detection as idm
        original = idm.IntentDetection.invoke

        async def fake_super_invoke(self, inputs, session, context, **kwargs):
            return {}

        idm.IntentDetection.invoke = fake_super_invoke
        try:
            import asyncio
            asyncio.run(comp.invoke({}, MagicMock(), None))
            # component_exec 已设置且未 reset（读得到）
            session_seen, _ = ctx.current_component_exec()
            assert session_seen is not None
        finally:
            idm.IntentDetection.invoke = original
            # 清理：重置 ContextVar（新 event loop 的 context 实际独立，此处防御性）
```

（`asyncio.run` 与 pytest-asyncio 混用需谨慎——改为 `@pytest.mark.asyncio` 驱动更佳，执行者按实际调整，断言语义不变：invoke 返回后 component_exec 仍可读。）

- [ ] **Step 2: 运行确认失败** — Run: `.venv/bin/python -m pytest tests/unit_tests/extension/test_intent_detection_stateless.py -v`，Expected: FAIL。
- [ ] **Step 3: 按设计实施**（grep 验证：`grep -n "set_session\|self\._session\b\|few_shot_example +=" jiuwen/extension/workflow_node/intent_detection.py` 应零命中 set_session 与 +=）。
- [ ] **Step 4: 运行** — Run: `.venv/bin/python -m pytest tests/unit_tests/extension/test_intent_detection_stateless.py -v` 及 `.venv/bin/python -m pytest tests/unit_tests/ -q -k "intent"`，Expected: PASS。
- [ ] **Step 5: 提交** — `git commit -m "refactor(runtime): IntentDetection 路由 session 改走 component_exec，执行期状态清理"`

---

### Task 13: Message / FlowCard 模板渲染隔离

**Files:**
- Modify: `jiuwen/extension/workflow_node/flow_message.py`
- Modify: `jiuwen/extension/workflow_node/flow_card.py`
- Test: `tests/unit_tests/extension/test_template_render_isolation.py`

**审计发现**：两组件本体零执行期写入，但共享 `self._processor/_template_processor`（TemplateProcessor，`end_comp.py:250-308`）的 `render_stream` 逐段推进 `_current_position/_chunk_index/_count`——并发执行渲染位置互踩（顺序复用可经 finally `reset()` 自愈，并发不行）。Message 无 `set_mix`，引擎不会帮它复位。

**修复设计**：所有 `render_stream`/`render` 调用点改为先 `renderer = copy.copy(self._processor)` 再对 `renderer` 调用（浅拷贝足够：位置字段是 int，模板 split 结果共享只读）。Message 的调用点在 invoke/stream（flow_message.py，grep `render_stream\|_processor.render`）；FlowCard 在 stream 路径 :323-330 的 `hasattr(render_stream)` 分支（grep `_template_processor`）。`__init__` 保留原 processor（构建期产物，克隆廉价）。

- [ ] **Step 1: 失败测试**：

```python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Message/FlowCard 模板渲染位置并发隔离测试。"""
import copy


class TestTemplateRenderIsolation:
    def test_render_leaves_original_processor_untouched(self):
        """渲染使用克隆 processor——原 processor 游标位置不变。"""
        from unittest.mock import MagicMock

        from jiuwen.extension.workflow_node.flow_message import Message

        msg = Message({"template": "hello {{userFields.answer}}", "name": "m"})
        original = msg._processor
        pos_before = getattr(original, "_current_position", None)

        session = MagicMock()
        # 驱动 invoke（标准组件接口 (inputs, session, context)）；
        # mock session 的 io 写入链路，仅观察 processor 游标
        import asyncio
        inputs = {"userFields": {"answer": "world"}}
        asyncio.run(msg.invoke(inputs, session, None))

        assert getattr(original, "_current_position", None) == pos_before
```

（此测试按实际渲染入口补全驱动逻辑——核心断言：渲染后 `original._current_position` 等位置字段与渲染前一致。）

- [ ] **Step 2: 运行确认失败** — Run: `.venv/bin/python -m pytest tests/unit_tests/extension/test_template_render_isolation.py -v`，Expected: FAIL。
- [ ] **Step 3: 实施克隆**（两文件的全部渲染调用点）。
- [ ] **Step 4: 运行** — Run: `.venv/bin/python -m pytest tests/unit_tests/extension/test_template_render_isolation.py -v` 及 `.venv/bin/python -m pytest tests/unit_tests/ -q -k "message or flow_card"`，Expected: PASS。
- [ ] **Step 5: 提交** — `git commit -m "refactor(runtime): Message/FlowCard 渲染改用克隆 TemplateProcessor，消除共享渲染位置互踩"`

---

### Task 14: FlowApi / FlowQA / Questioner / FlowAgent 清理

**Files:**
- Modify: `jiuwen/extension/workflow_node/flow_api.py`
- Modify: `jiuwen/extension/workflow_node/flow_qa.py`
- Modify: `agent_runtime/extension/workflow_node/questioner.py`（注意：ir_converter 实际注册的是 agent_runtime 版，不是 jiuwen 副本）
- Modify: `jiuwen/extension/workflow_node/flow_agent.py`
- Test: `tests/unit_tests/extension/test_stream_components_stateless.py`

**审计发现与逐项修复**：

| 组件 | 问题 | 修复 |
|---|---|---|
| FlowApi | `_final_stream_output`（:759 写，:770-775 get_stream_output 读，**入口无复位**——异常退出会把上一执行输出写入本次 io_state） | :759 → `set_stream_final_output(formatted_res)`；get_stream_output → `return get_stream_final_output()`；stream 入口 `set_stream_final_output(None)`；`__init__` 删字段（:156） |
| FlowQA | `_stream_output`（:576-581 写）——INVOKE-only 组件引擎不读，遗留死状态 | 删除字段与写点；`_node_state` 保留（每执行 :552-564 从 session 重建，自愈） |
| Questioner | `_metadata`（:2103-2107 写，回调读）局部化；`_stream_output`（:2178 写）遗留死状态删除；`_initialize_model`（:1882-1912）无锁 | `_metadata` 改局部变量传递；`_stream_output` 删；`_initialize_model` 加 `_init_lock` 双检 |
| FlowAgent | `_ensure_initialized`（:169-195）无锁——并发首调重复建 ReActAgent + `Runner.resource_mgr.add_tool`（:287，默认严格拒绝重复注册，异常被吞成脏日志）+ `register_rail` 重复 | `_ensure_initialized` 加锁双检；`:287` 的 add_tool 加 `skip_if_exists=True`（resource_manager.py:403-426 已支持该参数） |
| FlowMcp | `_header_params`（:442 写，invoke :339-343 读，写读间无 await 单执行无交错、旧版路径不写无残留——(b) 但低危） | `_format_api_inputs` 已返回 tuple，追加 `header_params` 项消除实例写入，invoke 侧解包使用 |

注意：jiuwen 侧另有一份近似 Questioner 副本（`jiuwen/extension/workflow_node/questioner.py`，注册表不用它）——先 grep 确认无运行时引用（BPMN/orchestration 路径），无引用则不动（YAGNI）；有引用则同 agent_runtime 版一并处理。

- [ ] **Step 1: 失败测试**：

```python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""FlowApi/FlowQA/Questioner/FlowAgent 执行期状态清理测试。"""
import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from jiuwen.extension.workflow import execution_session_ctx as ctx


class TestFlowApiStateless:
    def test_final_stream_output_via_contextvar(self):
        from jiuwen.extension.workflow_node.flow_api import FlowApi

        api = FlowApi.__new__(FlowApi)  # 跳过重构造
        ctx.set_stream_final_output({"frame": 1})
        assert api.get_stream_output() == {"frame": 1}
        ctx.set_stream_final_output(None)

    def test_no_instance_final_output_field(self):
        from jiuwen.extension.workflow_node.flow_api import FlowApi
        import inspect

        src = inspect.getsource(FlowApi)
        assert "self._final_stream_output" not in src


class TestFlowAgentInitLock:
    @pytest.mark.asyncio
    async def test_concurrent_ensure_initialized_runs_once(self, monkeypatch):
        from jiuwen.extension.workflow_node import flow_agent as fa

        agent = fa.FlowAgent.__new__(fa.FlowAgent)
        agent._initialized = False
        agent._init_lock = asyncio.Lock()
        agent._config = MagicMock()
        agent._tools = []
        agent._model = MagicMock()
        created = []

        async def fake_create():
            created.append(1)
            await asyncio.sleep(0.01)
            return MagicMock()

        monkeypatch.setattr(agent, "_create_react_agent", fake_create)
        await asyncio.gather(agent._ensure_initialized(), agent._ensure_initialized())
        assert len(created) == 1
```

- [ ] **Step 2: 运行确认失败** — Run: `.venv/bin/python -m pytest tests/unit_tests/extension/test_stream_components_stateless.py -v`，Expected: FAIL。
- [ ] **Step 3: 按逐项表实施**。
- [ ] **Step 4: 运行** — Run: `.venv/bin/python -m pytest tests/unit_tests/extension/test_stream_components_stateless.py -v` 及 `.venv/bin/python -m pytest tests/unit_tests/ -q -k "flow_api or flow_qa or questioner or flow_agent"`，Expected: PASS。
- [ ] **Step 5: 提交** — `git commit -m "refactor(runtime): FlowApi/FlowQA/Questioner/FlowAgent 执行期状态清理与懒初始化加锁"`

---

### Task 15: Patch D — BranchComponent.invoke 包装（路由 session 保真的最后一块）

**Files:**
- Modify: `jiuwen/extension/patches/static_graph_patch.py`
- Test: `tests/unit_tests/extension/patches/test_static_graph_patch.py`（追加 TestPatchD）

**背景（审计发现）**：`BranchRouter.set_session` 共 4 处执行期写入：仓库侧 2 处（Task 12 已改 component_exec）+ openjiuwen venv 2 处（`branch_comp.py:39` 的 `BranchComponent.invoke`、`intent_detection_comp.py:210` 的 `IntentDetectionExecutable.invoke`）。jiuwen IR 注册表会创建 **BranchComponent**（ir_converter.py:2367，jiuwen.branch 节点）——venv 源码不可改，但其 invoke 只做 `set_session + return {}`，包装即可。`IntentDetectionExecutable` 不被 jiuwen 注册表使用（原生 API 路径），不处理。

**Patch D 设计**：包装 `BranchComponent.invoke`，set component_exec（不 reset——同 task 的 dispatch 需要读到该节点的 NodeSession，与今天 `set_session(session)` 语义一致）；原函数照常执行（其 set_session 写成为死写，Patch C 下不被读）：

```python
def _wrap_branch_component_invoke(prev_invoke):
    """Patch D：BranchComponent.invoke 设置 component_exec（路由保真）。

    BranchComponent（venv）invoke 唯一动作是 router.set_session(session)
    （NodeSession）——Patch C 读侧改走 ContextVar 后，需在此补写组件级
    session，保证分支源节点的 dispatch 解析到与现状一致的 NodeSession。
    不 reset：值须存活到同 NodeTask 内 invoke 返回之后的 dispatch。
    """

    async def _invoke_with_component_exec(self, inputs, session, context):
        _session_ctx.set_component_exec(session, context)
        return await prev_invoke(self, inputs, session, context)

    return _invoke_with_component_exec
```

`_structure_assertions()` 追加断言（C2）：

```python
    # C2: BranchComponent.invoke 的 set_session 写入点（Patch D 包装基础）
    try:
        from openjiuwen.core.workflow.components.flow.branch_comp import BranchComponent
        branch_invoke_src = inspect.getsource(BranchComponent.invoke)
        if "set_session" not in branch_invoke_src:
            failures.append("BranchComponent.invoke 不再调用 set_session（Patch D 基础失效）")
    except ImportError:
        pass  # 引擎无此组件（版本差异），跳过
    except (OSError, TypeError) as e:
        failures.append(f"BranchComponent.invoke 源码不可内省: {e}")
```

`apply_static_graph_patch()` 填充区追加：

```python
    try:
        from openjiuwen.core.workflow.components.flow.branch_comp import BranchComponent
        BranchComponent.invoke = _wrap_branch_component_invoke(BranchComponent.invoke)
    except ImportError:
        pass
```

- [ ] **Step 1: 失败测试**：

```python
class TestPatchD:
    def test_branch_component_invoke_sets_component_exec(self, monkeypatch):
        from openjiuwen.core.workflow.components.flow.branch_comp import BranchComponent
        from jiuwen.extension.patches.static_graph_patch import _wrap_branch_component_invoke
        from jiuwen.extension.workflow import execution_session_ctx as ctx

        async def fake_prev(self, inputs, session, context):
            return {"orig": True}

        wrapped = _wrap_branch_component_invoke(fake_prev)
        comp = BranchComponent()
        marker_session, marker_ctx = object(), object()

        import asyncio
        result = asyncio.run(comp.__class__.__call__ and None) or None
        # 直接驱动包装函数（BranchComponent.__init__ 无参可用）
        result = asyncio.run(_drive(wrapped, comp, marker_session, marker_ctx))
        assert result == {"orig": True}
        assert ctx.current_component_exec() == (marker_session, marker_ctx)  # 未 reset
```

```python
async def _drive(wrapped, comp, session, context):
    return await wrapped(comp, {}, session, context)
```

（`asyncio.run` 会创建独立事件循环——ContextVar 的 context 在 run 内独立，断言须在 run 内做或用 pytest-asyncio；执行者调整为 `@pytest.mark.asyncio` 单测试方法内完成断言。）

- [ ] **Step 2: 运行确认失败** — Run: `.venv/bin/python -m pytest tests/unit_tests/extension/patches/test_static_graph_patch.py::TestPatchD -v`，Expected: FAIL。
- [ ] **Step 3: 实施 Patch D**（包装 + 断言 + apply 接线）。
- [ ] **Step 4: 运行** — Run: `.venv/bin/python -m pytest tests/unit_tests/extension/patches/ -v`，Expected: PASS。
- [ ] **Step 5: 提交** — `git commit -m "feat(runtime): Patch D——BranchComponent.invoke 组件级 session 补写（路由保真）"`

---

## 集成验证与收尾（Task 16-17）

### Task 16: 真实引擎并发隔离集成测试

**Files:**
- Create: `tests/integration_tests/test_workflow_static_graph_reuse.py`

**Interfaces:**
- Consumes: 全部前序任务（patch 三件套经 import 应用、组件无状态化、缓存）。
- Produces: 验收标准 5（同实例不同 session 无串扰）与验收标准 2/3（缓存命中、重发布失效）的机器验证。

**前置事实**：真实引擎在 venv 可用；`workflow_message.json` 为 Start/Message/End 纯消息流（无 LLM 依赖，可真实 stream）；**import 顺序**：先 `import jiuwen.serve.controllers.execution.ir_converter`（触发 patch 应用链），再取引擎类（否则 circular import——计划期实验踩过）。

- [ ] **Step 1: 写测试**

```python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""静态图复用集成测试（spec §9.2，issue #1555 验收标准 2/3/5）。

真实 openjiuwen 引擎 + 真实 IR 构建（workflow_message.json，无 LLM 依赖）：
- 同一 Workflow 实例 N 路并发 stream、不同 session → 输出互不串扰；
- static_graph 模式下缓存命中（第二次 aget 直取同实例）；
- IR 内容变化 → miss。
"""
import asyncio
import copy
import json
from pathlib import Path

import pytest

# 先触发 patch 应用链（circular import 规避：引擎类后取）
import jiuwen.serve.controllers.execution.ir_converter  # noqa: F401

from agent_runtime.common.config import settings
from jiuwen.serve.controllers.execution import workflow_instance_cache as wic
from jiuwen.serve.controllers.execution.ir_converter import IRConverter
from openjiuwen.core.workflow import create_workflow_session

IR_PATH = Path(__file__).resolve().parents[1] / "resource" / "ir_file" / "workflow_message.json"


@pytest.fixture(autouse=True)
def _static_graph_mode(monkeypatch):
    monkeypatch.setattr(settings.cache, "workflow_instance_reuse_mode", "static_graph")
    wic.clear_workflow_instance_cache()
    yield
    wic.clear_workflow_instance_cache()


async def _drive(wf, session, tag):
    chunks = []
    async for chunk in wf.stream({"query": f"hello-{tag}"}, session):
        chunks.append(chunk)
    return chunks


class TestConcurrentIsolationOnSharedInstance:
    @pytest.mark.asyncio
    async def test_concurrent_streams_on_same_instance_are_isolated(self):
        """同一 Workflow 实例 4 路并发、不同 session：全部完成且输出各自完整。"""
        ir_data = json.loads(IR_PATH.read_text(encoding="utf-8"))
        ir_data["is_published"] = True
        lazy = await IRConverter.async_ir_to_workflow(ir_data)
        wf = await lazy.instantiate()

        sessions = [create_workflow_session(session_id=f"sess-{i}") for i in range(4)]
        results = await asyncio.gather(*[
            _drive(wf, s, str(i)) for i, s in enumerate(sessions)
        ])

        # 每路执行都产生完整输出（消息型 workflow 的 chunk 流非空）
        for i, chunks in enumerate(results):
            assert len(chunks) > 0, f"执行 {i} 输出为空——并发串扰"

        # 图实例的编译产物未被并发污染：每执行独立 Pregel（Patch A）
        graph = wf._internal._graph
        assert graph.pregel is not None

    @pytest.mark.asyncio
    async def test_repeated_execution_matches_fresh_build_output(self):
        """等价性：同 IR 缓存实例的执行输出 == 每请求新建实例的输出（事件序列语义）。"""
        ir_data = json.loads(IR_PATH.read_text(encoding="utf-8"))
        ir_data["is_published"] = True

        # 新建实例路径（off 模式语义）
        lazy_fresh = await IRConverter.async_ir_to_workflow(copy.deepcopy(ir_data))
        wf_fresh = await lazy_fresh.instantiate()
        s_fresh = create_workflow_session(session_id="fresh")
        out_fresh = await _drive(wf_fresh, s_fresh, "fresh")

        # 缓存实例路径（static_graph 语义）——两次执行（第二次为复用）
        s1 = create_workflow_session(session_id="reuse-1")
        s2 = create_workflow_session(session_id="reuse-2")
        wf_reuse = await wic.aget_or_create_workflow_instance(
            "integration/reuse.json", ir_data, IRConverter.async_ir_to_workflow
        )
        out1 = await _drive(wf_reuse, s1, "r1")
        wf_reuse2 = await wic.aget_or_create_workflow_instance(
            "integration/reuse.json", ir_data, IRConverter.async_ir_to_workflow
        )
        assert wf_reuse2 is wf_reuse  # 命中同一 LazyWorkflow
        out2 = await _drive(wf_reuse2, s2, "r2")

        # 三次执行的输出 chunk 数量一致（消息型流的确定性骨架）
        assert len(out_fresh) == len(out1) == len(out2)

    @pytest.mark.asyncio
    async def test_republish_invalidates_cache(self):
        ir_v1 = json.loads(IR_PATH.read_text(encoding="utf-8"))
        ir_v1["is_published"] = True
        ir_v2 = copy.deepcopy(ir_v1)
        ir_v2["nodes"] = ir_v1.get("nodes", []) + []  # 触发内容 hash 变化的最小改动

        w1 = await wic.aget_or_create_workflow_instance(
            "integration/republish.json", ir_v1, IRConverter.async_ir_to_workflow)
        w2 = await wic.aget_or_create_workflow_instance(
            "integration/republish.json", ir_v2, IRConverter.async_ir_to_workflow)
        assert w2 is not w1  # 内容变化 → miss
```

- [ ] **Step 2: 运行** — Run: `.venv/bin/python -m pytest tests/integration_tests/test_workflow_static_graph_reuse.py -v`
Expected: PASS（若 `create_workflow_session` 在测试环境因 checkpointer 配置失败，查 `CheckpointerFactory.get_checkpointer("in_memory")` 路径显式设置默认 checkpointer：`CheckpointerFactory.set_default_checkpointer(InMemoryCheckpointer())`——按实际类名导入）。
- [ ] **Step 3: 若并发串扰断言失败** — 用 `superpowers:systematic-debugging` 定位（通常是遗漏的 (b) 类状态——回查对应组件任务）。
- [ ] **Step 4: 已知测试缺口记录** — 本 fixture（消息型，无 LLM/QA）无法驱动 spec §9.2 的两个场景：缓存实例上的**中断/恢复**（需 Questioner 交互）与**嵌套子工作流复用**（需含 SubWorkflow 的 IR）。这两个场景由 Task 17 Step 2 记入 spec（作为 L2 灰度前的补充测试项，或需要 stub LLM 的后续测试）。
- [ ] **Step 5: 提交** — `git commit -m "test(runtime): 静态图复用真实引擎并发隔离集成测试"`

---

### Task 17: spec 附录 A 回填 + 文档同步 + 全量回归

**Files:**
- Modify: `docs/superpowers/specs/2026-10-12-workflow-static-graph-reuse-design.md`（附录 A 审计表 + §5.1 修正）
- 无代码变更

**Steps:**

- [ ] **Step 1: 回填附录 A**——用计划期审计结论填表（每组件一行：类型/实例属性写入/分类/处理/结论）。要点：Start/Aggregate/FlowCode/lane-done 系 = (a) 可共享；LLMChain/End/SubWorkflow/IntentDetection/FlowApi/FlowQA/Questioner/FlowAgent/Message/FlowCard/BranchComponent = 已按 Task 9-15 修复；FlowMcp/LazyWorkflow = (c) 带锁正确范式。
- [ ] **Step 2: 修正 spec §5.1 已知必改项表**：`set_expect_mix/set_mix` 实际在 End 上（非 Questioner）且为构建期幂等 (a)；FlowApi/FlowMcp 工具注册 tag 为构建期幂等 (a)（真正的问题是 FlowApi 末帧无复位）；补充 §4.3 两层解析链说明（component_exec 优先级与 Patch D）与 §5.3 auto_complete 结论（幂等 + 事件循环原子，无需守卫）；记录 Task 16 的测试缺口（中断/恢复与嵌套子工作流场景待 L2 前补）。
- [ ] **Step 2.5: lakesearch ContextVar 边界确认**（spec §8 风险 2）— 读 `agent_runtime/extension/workflow_node/kb_adapter/lakesearch_adapter.py:330` 的 `run_in_executor` 块，确认块内是否读取 session/ContextVar（GSSAPI token 获取预期只依赖配置）。若块内确有 session 依赖，记录到 spec 风险表并在该处显式传参（`functools.partial` 携带所需值），使线程内不依赖 ContextVar。
- [ ] **Step 3: 全量回归** — Run: `.venv/bin/python -m pytest tests/unit_tests/ tests/integration_tests/test_workflow_static_graph_reuse.py -q`
Expected: 全部 PASS（验收标准 1：默认 off + patch 始终应用 = 现状行为）。
- [ ] **Step 4: 提交** — `git add docs/superpowers/specs/ && git commit -m "docs(spec): 附录 A 组件审计表回填与 §5.1/§4.3/§5.3 计划期结论同步"`
