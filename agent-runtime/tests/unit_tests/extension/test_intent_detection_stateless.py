# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# 本文件是 IntentDetection 组件跨执行隔离的白盒验收：判据的观测面就是组件实例上的
# 执行期私有成员（路由会话 _router._session、懒初始化入口 _get_llm_instance、中断
# 处理入口 _handle_global_intent），这些成员没有公开入口可读写，断言必须直接钉住
# “执行期状态不再落共享实例”这一内部不变量，故按测试需要直接访问。
# pylint: disable=protected-access
"""IntentDetection / _RoutedIntentDetection 组件跨执行隔离测试。

审计发现（issue #1555 / Task 12）：实例复用后，执行期状态落在组件实例上——
`self._session`（辅助方法回读）、`self.conversation_id`（仅日志读）、
`self._router.set_session(session)`（路由会话写死在共享 router 上）、
`self.few_shot_example += ...`（只写不读的无界累积），以及 `get_llm_result`
懒初始化 `self.llm` 无锁（并发首调重复建 Model）。

本测试钉住：
1. 路由属主组件的 component_exec **不 reset**——invoke 返回后仍可读，
   存活到同一 NodeTask 的 dispatch（Patch C 优先级 1）；
2. 实例上不再挂执行期字段（`_session` / `conversation_id` /
   `few_shot_example`），辅助方法经 ContextVar / 参数取会话；
3. 懒初始化双检加锁：并发首调只建一次 Model；
4. node_state 为遗留接口，invoke 入口重建复位（上一执行残留不串入）。
"""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from jiuwen.extension.workflow import execution_session_ctx as ctx
from jiuwen.extension.workflow_node.intent_detection import (
    ExecutionStatus,
    IntentDetection,
)


def _conf() -> dict:
    """最小可用 IntentDetection 配置（无 LLM / 无 KG 调用）。"""
    return {
        "name": "intent",
        "branches": [
            {"id": "branch_0", "catalog": "其他意图"},
            {"id": "branch_1", "catalog": "查天气"},
        ],
        "prompt": "test prompt",
        "enableHistory": False,
        "enableInput": True,
        "chatHistoryMaxTurn": 3,
        "exampleContent": [],
        "overridable": False,
    }


def _mock_session(session_id: str = "sess-1") -> MagicMock:
    """最小 session 桩（spec_set 限定接口面）。

    spec_set 必要：普通 MagicMock 会**自动生成**任意属性（含 `_inner`），
    使写入端 `getattr(session, "_inner", session)` 解包到一个假包装器上——
    与真实引擎 session（NodeSession 无 `_inner`）不同构，会掩盖类型契约缺陷。
    """
    session = MagicMock(
        spec_set=["get_session_id", "get_component_id", "get_global_state",
                  "trace", "interact"]
    )
    session.get_session_id = MagicMock(return_value=session_id)
    session.get_component_id = MagicMock(return_value="intent_node")
    session.get_global_state = MagicMock(return_value=None)
    session.trace = AsyncMock()
    session.interact = MagicMock(return_value={"result": "interrupt"})
    return session


@pytest.fixture(autouse=True)
def _clean_component_exec():
    """执行期 ContextVar 通道进程内共享，用例前后复位避免互相串扰。"""
    ctx.set_component_exec(None, None)
    yield
    ctx.set_component_exec(None, None)


def _session_arg_condition(func):
    """session 透传条件（测试专用）。

    引擎 FuncCondition.invoke 为**无参**调用（condition.py:44 `self._func()`），
    条件函数收不到 session；本变体把 session 透传给条件函数，使断言能直接
    观察 Patch C 解析出的 session 对象（同 test_static_graph_patch 的助手）。
    """
    from openjiuwen.core.workflow.components.condition.condition import FuncCondition

    class _SessionArgFuncCondition(FuncCondition):
        def invoke(self, inputs, session):
            return self._func(session)

    return _SessionArgFuncCondition(func)


def _original_router_call():
    """原版 ``BranchRouter.__call__``（降级模式的真实读侧）。

    Patch C 已安装时从补丁模块取保存的原版引用；未安装（apply 未触发）时
    类属性本身即原版——两态下返回的都是"读 self._session"的实现。
    """
    from jiuwen.extension.patches import static_graph_patch
    from openjiuwen.core.workflow.components.flow.branch_router import BranchRouter

    orig = static_graph_patch._original_branch_router_call
    return orig if orig is not None else BranchRouter.__call__


class TestIntentDetectionStateless:
    @staticmethod
    def test_no_exec_state_instance_fields():
        """实例不再持有执行期 session/conversation_id/few_shot_example 字段。"""
        comp = IntentDetection(_conf())
        assert not hasattr(comp, "_session")
        assert not hasattr(comp, "conversation_id")
        assert not hasattr(comp, "few_shot_example")

    @pytest.mark.asyncio
    async def test_invoke_sets_component_exec_without_reset(self):
        """invoke 设置 component_exec 且不 reset——返回后仍可读（存活到 dispatch）。"""
        comp = IntentDetection(_conf())
        comp.get_llm_result = AsyncMock(
            return_value='{"class": "分类1", "reason": "r"}'
        )
        session = _mock_session()
        context = MagicMock()

        result = await comp.invoke({"input": "你好"}, session, context)

        assert result["result"] == "分类1"
        # 路由属主组件：值须存活到同一 NodeTask 的 dispatch（Patch C 优先级 1）
        assert ctx.current_component_exec() == (session, context)
        # 无执行期字段残留
        assert not hasattr(comp, "_session")
        assert not hasattr(comp, "conversation_id")

    @pytest.mark.asyncio
    async def test_routed_intent_sets_component_exec_without_reset(self, monkeypatch):
        """_RoutedIntentDetection.invoke 设置 component_exec（不 reset——存活到 dispatch）。"""
        from jiuwen.serve.controllers.execution.ir_converter import (
            _RoutedIntentDetection,
        )
        import jiuwen.extension.workflow_node.intent_detection as idm

        comp = _RoutedIntentDetection(_conf())
        session = _mock_session()
        context = MagicMock()
        seen = {}

        async def fake_super_invoke(self, inputs, session, context, **kwargs):
            seen["exec"] = ctx.current_component_exec()
            return {"result": "ok"}

        monkeypatch.setattr(idm.IntentDetection, "invoke", fake_super_invoke)
        result = await comp.invoke({"input": "x"}, session, context)

        assert result == {"result": "ok"}
        # super 执行期间可见
        assert seen["exec"] == (session, context)
        # 返回后未 reset（同 task 的 dispatch 需要读到组件级 session）
        assert ctx.current_component_exec() == (session, context)
        # 测试桩非 Session/BaseSession → 降级兼容写入（类型守卫）跳过；
        # 真实包装器下的兼容写入由
        # test_router_session_compat_write_feeds_original_read_path 钉住
        assert comp._router._session is None

    @pytest.mark.asyncio
    async def test_router_session_compat_write_feeds_original_read_path(self):
        """降级模式路由保真：真实 Session 下兼容写入落 router，原版读侧可解析。

        结构断言失败时四补丁均不安装（apply_static_graph_patch 降级分支），
        原版 ``BranchRouter.__call__`` 直接读 ``self._session``（唯一写入方
        set_session）——组件侧不写则路由 session 恒 None，分支条件
        （ExpressionCondition 需 NodeSession.state()）直接失败。本用例以真实
        Session 包装器驱动 invoke，钉住（1）兼容写入已落（解包到 NodeSession，
        与原版一致）；（2）原版 ``__call__``（降级模式的真实读侧）经该字段
        解析出目标分支。
        """
        from openjiuwen.core.session import NodeSession, WorkflowSession
        from openjiuwen.core.session.node import Session

        comp = IntentDetection(_conf())
        comp.get_llm_result = AsyncMock(
            return_value='{"class": "分类1", "reason": "r"}'
        )
        wf_session = WorkflowSession(workflow_id="wf-compat", session_id="sess-compat")
        node_session = NodeSession(wf_session, "intent_node")
        session = Session(node_session, False)

        await comp.invoke({"input": "你好"}, session, MagicMock())

        # set_session 写入端解包：与原版 self._router.set_session(session) 同物
        assert comp._router._session is node_session

        # 原版读侧（降级模式）：session = self._session → 条件求值需 NodeSession
        comp._router.add_branch(
            _session_arg_condition(lambda s: s is node_session), ["hit"]
        )
        assert await _original_router_call()(comp._router) == ["hit"]

    @pytest.mark.asyncio
    async def test_routed_intent_full_path_keeps_component_exec(self, monkeypatch):
        """路由子类走真实 super().invoke（两处 set 同值幂等）：返回后通道仍可读。"""
        from jiuwen.serve.controllers.execution.ir_converter import (
            _RoutedIntentDetection,
        )

        comp = _RoutedIntentDetection(_conf())
        comp.get_llm_result = AsyncMock(
            return_value='{"class": "分类1", "reason": "r"}'
        )
        session = _mock_session()
        context = MagicMock()

        result = await comp.invoke({"input": "你好"}, session, context)

        assert result["result"] == "分类1"
        assert ctx.current_component_exec() == (session, context)

    @pytest.mark.asyncio
    async def test_faq_result_keeps_few_shot_example_local(self):
        """get_faq_result 不再把 few_shot_example 累加/挂到实例上。"""
        comp = IntentDetection(_conf())
        comp.intent_config.enable_knowledge = True
        current_inputs = {"input": "天气"}

        await comp.get_faq_result(current_inputs, [], conversation_id="sess-1")

        # 行为保留：example_content 仍写进 current_inputs（局部）
        assert "example_content" in current_inputs
        assert not hasattr(comp, "few_shot_example")

    @pytest.mark.asyncio
    async def test_invoke_faq_path_no_few_shot_residue(self):
        """完整 invoke 的 FAQ 路径（真实 get_faq_result/get_search_answer）无残留。"""
        comp = IntentDetection(_conf())
        comp.intent_config.enable_knowledge = True  # api 为 None → 搜索空结果
        comp.get_llm_result = AsyncMock(
            return_value='{"class": "分类1", "reason": "r"}'
        )
        session = _mock_session()

        result = await comp.invoke({"input": "天气"}, session, MagicMock())

        # FAQ 未命中 → 落到默认分类后继续走 LLM 分支（已 mock）
        assert result["result"] == "分类1"
        assert not hasattr(comp, "few_shot_example")

    @pytest.mark.asyncio
    async def test_lazy_llm_init_lock_dedupes_concurrent_first_calls(self):
        """并发首调只建一次 Model（锁双检）。

        side_effect 内 sleep(0) 让出事件循环制造真交错：无锁时两个协程都会
        通过 `if self.llm is None` 检查，重复建 Model。
        """
        comp = IntentDetection(_conf())
        llm = MagicMock()
        llm.invoke = AsyncMock(return_value=SimpleNamespace(content="{}"))

        async def _slow_create(_conf):
            await asyncio.sleep(0)
            return llm

        comp._get_llm_instance = AsyncMock(side_effect=_slow_create)
        await asyncio.gather(
            comp.get_llm_result({"input": "a"}),
            comp.get_llm_result({"input": "b"}),
        )
        assert comp._get_llm_instance.call_count == 1

    @pytest.mark.asyncio
    async def test_node_state_rebuilt_at_invoke_entry(self):
        """invoke 入口重建 node_state：上一执行残留状态不串入本执行。"""
        comp = IntentDetection(_conf())
        comp.node_state.status = ExecutionStatus.END  # 上一执行残留
        # FAQ 命中路径提前返回、不写 node_state——只有入口重建才能回到 START
        comp.intent_config.enable_knowledge = True
        comp.get_faq_result = AsyncMock(return_value="分类1")

        await comp.invoke({"input": "查天气"}, _mock_session(), MagicMock())

        assert comp.node_state.status == ExecutionStatus.START

    @staticmethod
    def test_global_intent_interrupt_reads_session_from_component_exec():
        """中断路径（_handle_global_intent）经 ContextVar 读 session，不再读实例字段。"""
        comp = IntentDetection(_conf())
        session = _mock_session()
        token = ctx.set_component_exec(session, None)
        try:
            comp._handle_global_intent(
                "分类1", "r", {"分类1": SimpleNamespace(intent_id="i-1")}
            )
        finally:
            ctx.reset_component_exec(token)

        session.interact.assert_called_once()
        assert comp.node_state.status == ExecutionStatus.USER_INTERACT


class TestComponentExecSessionTypeContract:
    """Critical-1：component_exec 值的类型契约（Patch C 消费方）。

    引擎 `WorkflowComponent.on_invoke`（component.py:95-99）以
    `Session(node_session, False)` 包装器调 invoke——包装器**不是** BaseSession、
    无 state()、无 __getattr__ 委托；dispatch 同 NodeTask → patched
    BranchRouter.__call__ → `resolve_routing_session` **读取端解包**
    （通道存包装器，路由解析返回 NodeSession）→ 分支条件
    Condition.__call__ → AtomicNode._validate_session_and_state
    （atomic_node.py:13-26）要求 isinstance BaseSession + CommitState，
    否则抛 GRAPH_STATE_COMMIT_ERROR。写入端存组件面包装器（组件自身读点
    trace / get_global_state / interact 依赖包装器 API），BaseSession 契约
    全由读取端解包承担（双契约分离）。
    """

    @staticmethod
    def _engine_session():
        """真实引擎 session 三元组：WorkflowSession → NodeSession → Session 包装器。"""
        from openjiuwen.core.session import NodeSession, WorkflowSession
        from openjiuwen.core.session.node import Session as SessionWrapper

        wf_session = WorkflowSession(workflow_id="wf_t12", session_id="wf-sess")
        node_session = NodeSession(wf_session, "intent_node")
        return node_session, SessionWrapper(node_session, False)

    @pytest.mark.asyncio
    async def test_component_exec_unwraps_session_wrapper_for_router_conditions(
        self, monkeypatch
    ):
        """双契约分离：通道存包装器（组件自身读点），解析链解包 NodeSession（Patch C 消费方）。"""
        from openjiuwen.core.session import BaseSession
        from openjiuwen.core.workflow.components.flow.branch_router import (
            BranchRouter,
        )
        from jiuwen.extension.patches.static_graph_patch import (
            _patched_branch_router_call,
        )
        from jiuwen.serve.controllers.execution.ir_converter import (
            _RoutedIntentDetection,
        )
        import jiuwen.extension.workflow_node.intent_detection as idm

        monkeypatch.setattr(BranchRouter, "__call__", _patched_branch_router_call)

        node_session, wrapper = self._engine_session()
        assert not isinstance(wrapper, BaseSession)  # 包装器不满足条件求值契约

        async def fake_super_invoke(self, inputs, session, context, **kwargs):
            return {}

        monkeypatch.setattr(idm.IntentDetection, "invoke", fake_super_invoke)

        comp = _RoutedIntentDetection(_conf())
        await comp.invoke({}, wrapper, None)

        # 契约 1（组件自身读点）：通道内存组件面包装器（NodeSession 无
        # trace/get_global_state/interact，解包存储会打断组件主路径）
        stored, _ = ctx.current_component_exec()
        assert stored is wrapper

        # 契约 2（Patch C 消费方）：解析链返回解包后的 NodeSession（BaseSession）
        assert ctx.resolve_routing_session() is node_session
        assert isinstance(ctx.resolve_routing_session(), BaseSession)

        # 消费端：patched BranchRouter → 条件求值不抛类型错，收到 NodeSession
        seen = {}

        def _record(session):
            seen["session"] = session
            return True

        router = BranchRouter(report_trace=False)
        router.add_branch(_session_arg_condition(_record), ["node_a"])
        assert await router() == ["node_a"]
        assert seen["session"] is node_session

    @pytest.mark.asyncio
    async def test_base_invoke_stores_session_wrapper(self):
        """基类 invoke 写入端存包装器（真实 Session 包装器驱动完整路径）。"""
        node_session, wrapper = self._engine_session()
        comp = IntentDetection(_conf())
        comp.get_llm_result = AsyncMock(
            return_value='{"class": "分类1", "reason": "r"}'
        )

        result = await comp.invoke({"input": "你好"}, wrapper, None)

        assert result["result"] == "分类1"
        stored, _ = ctx.current_component_exec()
        assert stored is wrapper

    @pytest.mark.asyncio
    async def test_wrapper_in_channel_supports_component_own_session_reads(self):
        """逃逸面：真实包装器入通道 + 真实 get_llm_result/interact 读点不抛 AttributeError。

        IntentDetection 自身读点只用包装器 API（trace / get_global_state /
        interact / get_session_id / get_component_id）——NodeSession 无这些
        方法（写入端若解包存储，生产主路径（FAQ 未命中/未开知识库时必经的
        `get_llm_result` 无条件 trace）即 AttributeError）。本用例不 mock
        `get_llm_result` 本体，仅 mock Model，钉住该逃逸面。
        """
        from openjiuwen.core.graph.pregel.base import GraphInterrupt

        node_session, wrapper = self._engine_session()
        comp = IntentDetection(_conf())
        llm = MagicMock()
        llm.invoke = AsyncMock(
            return_value=SimpleNamespace(content='{"class": "分类1"}')
        )
        comp.llm = llm  # 跳过懒初始化，驱动真实 get_llm_result

        result = await comp.invoke({"input": "你好"}, wrapper, None)

        assert result["result"] == "分类1"
        stored, _ = ctx.current_component_exec()
        assert stored is wrapper

        # 中断路径：wrapper.interact 可达（NodeSession 无 interact → AttributeError）；
        # 真实语义为等待用户输入（GraphInterrupt）。
        with pytest.raises(GraphInterrupt):
            await comp._handle_global_intent(
                "分类1", "r", {"分类1": SimpleNamespace(intent_id="i-1")}
            )

    def test_resolve_routing_session_unwraps_wrapper_from_any_writer(self):
        """读取端防御性解包：通道内即使是包装器（未来写入方），解析结果仍满足契约。"""
        from openjiuwen.core.session import BaseSession

        node_session, wrapper = self._engine_session()
        token = ctx.set_component_exec(wrapper, None)
        try:
            resolved = ctx.resolve_routing_session()
        finally:
            ctx.reset_component_exec(token)

        assert resolved is node_session
        assert isinstance(resolved, BaseSession)
