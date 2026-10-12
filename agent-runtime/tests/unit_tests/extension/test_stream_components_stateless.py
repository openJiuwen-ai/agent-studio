# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""FlowApi / FlowQA / Questioner / FlowAgent / FlowMcp / ComplexIntentDetection
执行期状态清理测试（issue #1555 / Task 14）。

审计发现（静态图复用前提）——实例跨执行复用后，执行期状态不能再落在组件
实例上：

1. ``FlowApi._final_stream_output``：流式末帧写实例字段、``get_stream_output``
   回读，且 stream 入口无复位——上一执行（或同一执行内前一次 stream）的末帧
   会经引擎 ``Vertex._post_stream`` 写入本次 io_state。迁 ContextVar 末帧
   通道（Task 1）+ 入口复位。
2. ``FlowQA._stream_output``：INVOKE-only 组件（无 stream/transform），引擎
   的 ``_post_stream`` 永不触达，纯遗留死状态。
3. ``Questioner._metadata``：invoke 写实例、回调读（同一调用链），可局部化；
   ``_stream_output`` 同 FlowQA 为死状态；``_initialize_model`` 懒初始化无锁
   （并发首调重复建 Model）。
4. ``FlowAgent._ensure_initialized``：懒初始化无锁——并发首调重复建
   ReActAgent、重复 ``Runner.resource_mgr.add_tool``（默认严格拒绝重复注册，
   异常被吞成脏日志）、重复 ``register_rail``；``add_tool`` 需
   ``skip_if_exists=True``（构建期幂等注册）。
5. ``FlowMcp._header_params``：``_format_api_inputs`` 写实例、invoke 回读
   （写读间无 await，低危但仍是跨调用共享写入），改为随返回值传递。
6. ``ComplexIntentDetection._session`` / ``_context``：执行期状态落实例，
   读点分散在辅助方法；迁 component_exec ContextVar（非路由属主，参照
   LLMChain 模式 set + finally reset）。**嵌套子执行**（分支子工作流）经
   is_sub 路径 inline await 在本节点 task 内执行，其子图节点 task 由
   ``TaskExecutorPool.submit`` 的 ``asyncio.create_task`` 派生、会继承
   组件级值——子图内分支节点的路由解析（Patch C 优先级 1）读到本组件
   session 即遮蔽子图自身 session，故子工作流调用期间通道临时置空
   （执行后恢复）。另：``_state``（status/intent_result/branch_id）执行期
   状态入口重建，``_sub_workflows``（子工作流实例缓存）与
   ``_sub_workflow_error`` 不再落实例（前者改为 invoke 链局部传递，
   后者为只写死状态删除）。
"""
import asyncio
import inspect
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from jiuwen.extension.workflow import execution_session_ctx as ctx


@pytest.fixture(autouse=True)
def _clean_exec_channels():
    """两个执行期 ContextVar 通道进程内共享，用例前后复位避免互相串扰。"""
    ctx.set_component_exec(None, None)
    ctx.set_stream_final_output(None)
    yield
    ctx.set_component_exec(None, None)
    ctx.set_stream_final_output(None)


# =============================================================================
# FlowApi
# =============================================================================


class TestFlowApiStateless:
    def test_no_instance_final_output_field(self):
        """实例不再持有流式末帧字段（源码级 + 实例级双断言）。"""
        from jiuwen.extension.workflow_node.flow_api import FlowApi

        src = inspect.getsource(FlowApi)
        assert "self._final_stream_output" not in src
        assert not hasattr(FlowApi(), "_final_stream_output")

    def test_final_stream_output_via_contextvar(self):
        """get_stream_output 读 ContextVar 通道（引擎 _post_stream 消费）。"""
        from jiuwen.extension.workflow_node.flow_api import FlowApi

        api = FlowApi.__new__(FlowApi)  # 跳过重构造
        ctx.set_stream_final_output({"frame": 1})
        assert api.get_stream_output() == {"frame": 1}
        ctx.set_stream_final_output(None)
        assert api.get_stream_output() is None

    @pytest.mark.asyncio
    async def test_stream_writes_final_output_to_channel(self):
        """流式末帧写入通道，且保持引擎可见形态（userFields 包裹）。

        io_state 引用路径为 ``${node.userFields.field}``——通道值必须保持
        ``{userFields: {...}}`` 包裹形态，否则下游非流式节点引用解析失败。
        """
        from jiuwen.extension.workflow_node.flow_api import FlowApi

        api = FlowApi()
        api._conf = {"userFields": {"outputs": [{"id": "raw_output"}]}}
        session = MagicMock()
        session.get_session_id = MagicMock(return_value="sess-1")

        async def _api_stream():
            yield SimpleNamespace(content="hello ")
            yield SimpleNamespace(content="world")

        frames = [
            frame
            async for frame in api._transform_async_stream_data(_api_stream(), session)
        ]

        assert len(frames) == 3  # 2 个流式帧 + 1 个 finish 帧
        expected = {"userFields": {"raw_output": "hello world"}}
        assert ctx.get_stream_final_output() == expected
        assert api.get_stream_output() == expected

    @pytest.mark.asyncio
    async def test_stream_entry_resets_stale_final_output_on_failure(self):
        """入口复位末帧通道：上一执行的末帧不串入本执行（判别用例）。

        预置 stale 末帧后驱动 stream 在**写末帧之前**失败（api.astream 抛错）。
        成功路径会写新末帧、掩盖入口复位，故必须用「写末帧前失败」路径判别：
        删掉入口 ``set_stream_final_output(None)`` 时本用例读到 stale 值转红。
        """
        from jiuwen.extension.workflow_node.flow_api import FlowApi
        from jiuwen.extension.workflow_node.utils import JiuWenBaseException

        ctx.set_stream_final_output({"stale": True})

        api = FlowApi()
        api._conf = {}
        api._api_id = "api-1"
        api._api = MagicMock()
        api._api.astream = MagicMock(side_effect=RuntimeError("boom"))
        session = MagicMock()
        session.trace = AsyncMock()

        with pytest.raises(JiuWenBaseException):
            async for _ in api.stream({}, session=session, context=MagicMock()):
                pass

        assert ctx.get_stream_final_output() is None
        assert api.get_stream_output() is None


# =============================================================================
# FlowQA
# =============================================================================


class TestFlowQAStateless:
    def test_no_dead_stream_output_field(self):
        """INVOKE-only 组件不再持有引擎不可达的 _stream_output 死状态。"""
        from jiuwen.extension.workflow_node.flow_qa import FlowQA

        src = inspect.getsource(FlowQA)
        assert "self._stream_output" not in src

        qa = FlowQA({"name": "qa", "options": ["a"], "needReply": False})
        assert not hasattr(qa, "_stream_output")

    def test_get_stream_output_reads_contextvar(self):
        from jiuwen.extension.workflow_node.flow_qa import FlowQA

        qa = FlowQA({"name": "qa", "options": ["a"], "needReply": False})
        ctx.set_stream_final_output({"userFields": {"response": "hi"}})
        assert qa.get_stream_output() == {"userFields": {"response": "hi"}}
        ctx.set_stream_final_output(None)
        assert qa.get_stream_output() is None


# =============================================================================
# Questioner
# =============================================================================


class TestQuestionerStateless:
    @staticmethod
    def _questioner():
        from agent_runtime.extension.workflow_node.questioner import Questioner

        return Questioner({"model_name": "test-model"})

    def test_no_exec_state_instance_fields(self):
        """实例不再持有 _metadata / _stream_output 执行期字段。"""
        from agent_runtime.extension.workflow_node.questioner import Questioner

        src = inspect.getsource(Questioner)
        assert "self._metadata" not in src
        assert "self._stream_output" not in src

        questioner = self._questioner()
        assert not hasattr(questioner, "_metadata")
        assert not hasattr(questioner, "_stream_output")

    def test_get_stream_output_reads_contextvar(self):
        questioner = self._questioner()
        ctx.set_stream_final_output({"userFields": {"USER_RESPONSE": "hi"}})
        assert questioner.get_stream_output() == {"userFields": {"USER_RESPONSE": "hi"}}

    @pytest.mark.asyncio
    async def test_initialize_model_lock_dedupes_concurrent_calls(self, monkeypatch):
        """懒初始化双检加锁：并发首调只建一次 Model。

        provider.get_llm_config 内 sleep 让出事件循环制造真交错：无锁时两个
        协程都会通过 ``if self._initialized`` 检查，重复建 Model。
        """
        from agent_runtime.extension.workflow_node import questioner as qm

        questioner = self._questioner()
        calls = []

        async def _slow_get_llm_config(conf):
            calls.append(conf)
            await asyncio.sleep(0.01)
            return SimpleNamespace(
                model_client_config=MagicMock(), model_config=MagicMock()
            )

        provider = MagicMock()
        provider.get_llm_config = AsyncMock(side_effect=_slow_get_llm_config)
        monkeypatch.setattr(
            "jiuwen.serve.controllers.execution.ir_converter._get_model_config_provider",
            lambda: provider,
        )
        monkeypatch.setattr(qm, "Model", MagicMock())

        await asyncio.gather(
            questioner._initialize_model(), questioner._initialize_model()
        )

        assert len(calls) == 1
        assert questioner._initialized is True

    @pytest.mark.asyncio
    async def test_invoke_passes_metadata_without_instance_field(self, monkeypatch):
        """invoke 构建的组件元数据经参数传给回调（不再写实例字段）。"""
        from agent_runtime.extension.workflow_node import questioner as qm

        questioner = self._questioner()
        questioner._initialize_model = AsyncMock()
        monkeypatch.setattr(
            qm.Questioner,
            "_load_state_from_session",
            AsyncMock(return_value=qm.QuestionerState()),
        )
        monkeypatch.setattr(
            qm.Questioner, "_store_state_to_session", AsyncMock()
        )

        captured = {}

        async def _fake_direct_reply(
            inputs, session, context, current_state, is_resuing=False, metadata=None
        ):
            captured["metadata"] = metadata
            return {"user_response": "hi"}

        monkeypatch.setattr(
            questioner, "_handle_questioner_direct_reply_safe", _fake_direct_reply
        )

        session = MagicMock()
        session.get_component_id = MagicMock(return_value="q_node")
        session.get_session_id = MagicMock(return_value="sess-1")

        result = await questioner.invoke({"query": "hi"}, session, MagicMock())

        assert captured["metadata"] == {
            "component_id": "q_node",
            "component_name": "q_node",
            "component_type": "Questioner",
        }
        assert not hasattr(questioner, "_metadata")
        assert result == {"userFields": {"USER_RESPONSE": "hi"}}


# =============================================================================
# FlowAgent
# =============================================================================


class TestFlowAgentInitLock:
    @pytest.mark.asyncio
    async def test_concurrent_ensure_initialized_runs_once(self, monkeypatch):
        """懒初始化双检加锁：并发首调只建一次 ReActAgent（register_rail 只注册一次）。

        register_rail 内 sleep 让出事件循环制造真交错：无锁时第二个协程会再次
        通过 ``if self._initialized`` 检查，重复建 Agent + 重复注册 rail。
        """
        from jiuwen.extension.workflow_node import flow_agent as fa

        agent = fa.FlowAgent(fa.FlowAgentConfig(max_iteration=1))
        created = []

        async def _slow_register_rail(rail):
            await asyncio.sleep(0.01)

        def _fake_create():
            created.append(1)
            react_agent = MagicMock()
            react_agent.register_rail = AsyncMock(side_effect=_slow_register_rail)
            agent._react_agent = react_agent

        monkeypatch.setattr(agent, "_create_react_agent", _fake_create)

        await asyncio.gather(
            agent._ensure_initialized(), agent._ensure_initialized()
        )

        assert len(created) == 1
        assert agent._react_agent.register_rail.await_count == 1

    def test_register_tools_adds_with_skip_if_exists(self, monkeypatch):
        """构建期工具注册幂等：add_tool 带 skip_if_exists=True。"""
        from openjiuwen.core.runner import Runner
        from jiuwen.extension.workflow_node import flow_agent as fa

        agent = fa.FlowAgent(fa.FlowAgentConfig(max_iteration=1))
        tool = MagicMock()
        tool.card = MagicMock()
        tool.card.name = "tool_a"
        agent._tools = [tool]
        agent._react_agent = MagicMock()

        add_tool = MagicMock()
        monkeypatch.setattr(Runner.resource_mgr, "add_tool", add_tool)

        agent._register_tools()

        add_tool.assert_called_once_with(tool, skip_if_exists=True)


# =============================================================================
# FlowMcp
# =============================================================================


class _MockParam:
    """最小 MCP 参数桩（与 test_flow_mcp_format_inputs.MockParam 同构）。"""

    def __init__(self, name, param_type="string", method="Body", required=False):
        self.name = name
        self.type = param_type
        self.method = method
        self.required = required
        self.default_value = None
        self.type_inferred = False
        self.description = ""


def _flow_mcp(params):
    from jiuwen.extension.workflow_node.flow_mcp import FlowMcp

    mcp = FlowMcp.__new__(FlowMcp)
    mcp._conf = {"type": "sse", "url": "http://test", "tool_name": "test_tool"}
    mcp._is_older_version = False
    client = MagicMock()
    client._tool_params = params
    mcp._client = client
    return mcp


class TestFlowMcpStateless:
    def test_format_api_inputs_returns_header_params(self):
        """header 参数随返回值传递，不再写实例字段。"""
        mcp = _flow_mcp(
            [
                _MockParam("auth_token", method="Headers"),
                _MockParam("query"),
            ]
        )

        api_inputs, schema_patches, header_params = mcp._format_api_inputs(
            {"auth_token": "my_token", "query": "hello"}
        )

        assert api_inputs == {"query": "hello"}
        assert schema_patches == {}
        assert header_params == {"auth_token": "my_token"}
        assert not hasattr(mcp, "_header_params")

    @pytest.mark.asyncio
    async def test_invoke_merges_header_params_into_runtime_auth(self):
        """invoke 把 header 参数合并进 runtime_auth.headers 下传底层工具。"""
        from jiuwen.extension.wrapper.mcp_tool_wrapper import JIUWEN_RUNTIME_KWARGS

        mcp = _flow_mcp(
            [
                _MockParam("auth_token", method="Headers"),
                _MockParam("query"),
            ]
        )
        mcp.api = MagicMock()
        mcp.api.invoke = AsyncMock(
            return_value={
                "result": SimpleNamespace(
                    structuredContent={"ok": True}, content=None
                )
            }
        )

        session = MagicMock()
        session.get_global_state = MagicMock(return_value=None)

        result = await mcp.invoke(
            {"userFields": {"auth_token": "tok-1", "query": "hi"}},
            session,
            MagicMock(),
        )

        assert result == {"userFields": {"ok": True}}
        call_args = mcp.api.invoke.call_args.args[0]
        runtime_kwargs = call_args[JIUWEN_RUNTIME_KWARGS]
        assert runtime_kwargs["runtime_auth"]["headers"] == {"auth_token": "tok-1"}
        assert call_args["query"] == "hi"
        assert "auth_token" not in call_args


# =============================================================================
# ComplexIntentDetection（T12 审计补入）
# =============================================================================


def _complex_conf() -> dict:
    """最小可用 ComplexIntentDetection 配置。"""
    return {
        "name": "cid",
        "intentDetectionContainerNodeId": "sub",
        "branches": [{"id": "branch_0", "catalog": "其他意图"}],
        "groups": {"g1": ["${branch_0.result}"]},
    }


def _complex_component():
    from agent_runtime.extension.workflow_node.complex_intent_detection import (
        ComplexIntentDetection,
    )

    return ComplexIntentDetection(_complex_conf(), node_id="cid_node", node_name="cid")


class TestComplexIntentDetectionStateless:
    def test_no_exec_state_instance_fields(self):
        """实例不再持有 _session / _context / 子工作流缓存 / 错误字段。"""
        from agent_runtime.extension.workflow_node.complex_intent_detection import (
            ComplexIntentDetection,
        )

        src = inspect.getsource(ComplexIntentDetection)
        assert "self._session" not in src
        assert "self._context" not in src
        assert "self._sub_workflows" not in src
        assert "self._sub_workflow_error" not in src

        comp = _complex_component()
        assert not hasattr(comp, "_session")
        assert not hasattr(comp, "_context")
        assert not hasattr(comp, "_sub_workflows")
        assert not hasattr(comp, "_sub_workflow_error")

    @pytest.mark.asyncio
    async def test_invoke_sets_and_resets_component_exec(self):
        """invoke 期间通道可见 (session, context)，返回后复位（finally）。"""
        comp = _complex_component()
        session = MagicMock()
        session.get_session_id = MagicMock(return_value="sess-1")
        context = MagicMock()
        seen = {}

        async def _fake_intent(inputs, **kwargs):
            seen["exec"] = ctx.current_component_exec()
            return {"classificationId": 0}, "branch_0"

        comp._get_intent_result = _fake_intent
        comp._execute_branch_workflow = AsyncMock(return_value=(None, None))

        result = await comp.invoke({"input": "hi"}, session, context)

        assert seen["exec"] == (session, context)
        assert isinstance(result, dict)
        assert ctx.current_component_exec() == (None, None)

    @pytest.mark.asyncio
    async def test_invoke_resets_component_exec_on_error(self):
        """invoke 异常路径同样复位通道（finally）。"""
        comp = _complex_component()
        session = MagicMock()
        session.get_session_id = MagicMock(return_value="sess-1")
        context = MagicMock()
        seen = {}

        async def _fail(inputs, **kwargs):
            seen["exec"] = ctx.current_component_exec()
            raise RuntimeError("boom")

        comp._get_intent_result = _fail

        result = await comp.invoke({"input": "hi"}, session, context)

        assert result["error"] == "boom"
        assert seen["exec"] == (session, context)
        assert ctx.current_component_exec() == (None, None)

    def test_resume_read_points_use_component_exec_session(self, monkeypatch):
        """恢复读点经通道取 session（不再是实例字段）。"""
        from agent_runtime.extension.workflow_node import complex_intent_detection as cidm

        comp = cidm.ComplexIntentDetection(
            _complex_conf(), node_id="cid_node", node_name="cid"
        )
        session = MagicMock(spec_set=["get_state", "get_session_id"])
        session.get_state = MagicMock(
            return_value={"workflow_state": {"__interactive_input__": "hello"}}
        )
        seen = {}

        def _fake_get_state_info(sess, key):
            seen["session"] = sess
            return {"__interactive_input__": "hello"}

        monkeypatch.setattr(cidm, "get_state_info", _fake_get_state_info)

        token = ctx.set_component_exec(session, None)
        try:
            assert comp._check_child_workflow_needs_resume() is True
            assert comp._extract_resume_query() == "hello"
        finally:
            ctx.reset_component_exec(token)

        assert seen["session"] is session

    def test_resume_read_points_work_with_real_session_wrapper(self):
        """逃逸面：真实 Session 包装器入通道时读点不抛 AttributeError 且读到状态。

        写入端存**组件面包装器**（与旧 ``self._session = session`` 同物）——
        组件自身读点（get_state / get_state_info 经 _inner 定位）依赖包装器
        API，NodeSession 无 get_state_info 所需的 _inner。状态经真实 NodeSession
        的 workflow_state 底层 dict 写入（get_state_info 的读取目标）。
        """
        from agent_runtime.common.session_state_access import get_state_info
        from openjiuwen.core.session import NodeSession, WorkflowSession
        from openjiuwen.core.session.node import Session as SessionWrapper

        wf_session = WorkflowSession(workflow_id="wf_t14", session_id="wf-sess")
        node_session = NodeSession(wf_session, "cid_node")
        wrapper = SessionWrapper(node_session, False)
        # get_state_info 的 workflow_state 取值为底层 dict 引用（见其 docstring）
        get_state_info(wrapper, "workflow_state")["__interactive_input__"] = "hello"

        comp = _complex_component()
        token = ctx.set_component_exec(wrapper, None)
        try:
            assert comp._extract_resume_query() == "hello"
            assert comp._check_child_workflow_needs_resume() is False
        finally:
            ctx.reset_component_exec(token)

    @pytest.mark.asyncio
    async def test_nested_sub_workflow_invocation_clears_component_exec(self):
        """嵌套子执行期间通道置空（执行后恢复）。

        子工作流经 is_sub 路径 inline await 在本节点 task 内执行，其子图各节点
        task 由 ``TaskExecutorPool.submit`` 的 ``asyncio.create_task``
        （``graph/pregel/task.py:29``）从本节点 task 派生，会继承组件级值；
        子图内分支节点的路由解析（Patch C 优先级 1）若读到本组件 session 即
        遮蔽子图自身 session（分支条件对错误 io_state 求值 → 恒 False →
        分支未命中报错）。本用例钉住子执行窗口内通道为空、窗口外恢复。
        """
        from agent_runtime.extension.workflow_node.complex_intent_detection import (
            BranchWorkflowConfig,
        )

        comp = _complex_component()
        session = MagicMock(spec_set=["get_state", "get_session_id"])
        session.get_state = MagicMock(return_value={})
        seen = {}

        async def _fake_sub_invoke(
            sub_inputs, sub_session, sub_context, is_resuming=False, **kwargs
        ):
            seen["exec"] = ctx.current_component_exec()
            return {"responseContent": "ok"}

        sub_workflow = MagicMock()
        sub_workflow.invoke = _fake_sub_invoke
        sub_workflow.get_state = MagicMock(return_value={"status": "END"})
        sub_workflows = {
            "wf-1": {"instance": sub_workflow, "sub_instance": None, "configs": {}}
        }

        token = ctx.set_component_exec(session, None)
        try:
            await comp._invoke_sub_workflow(
                {"input": "hi"},
                BranchWorkflowConfig(workflow_id="wf-1"),
                sub_workflows,
            )
            # 子执行窗口外：外层组件级值恢复
            assert ctx.current_component_exec() == (session, None)
        finally:
            ctx.reset_component_exec(token)

        assert seen["exec"] == (None, None)


# =============================================================================
# ComplexIntentDetection 残留执行期状态（fix round 1 / Important-2）
# =============================================================================


def _complex_conf_with_branch_workflow() -> dict:
    """带分支子工作流配置的最小 CID 配置（branch_0 → wf-1）。"""
    conf = _complex_conf()
    conf["branches"] = [
        {
            "id": "branch_0",
            "catalog": "其他意图",
            "configs": {"workflow_id": "wf-1", "ir_path": "ir/wf-1.json"},
        }
    ]
    return conf


class TestComplexIntentDetectionResidualState:
    @pytest.mark.asyncio
    async def test_second_execution_on_same_instance_reclassifies(self):
        """判别用例：同一实例第二次执行必须重新识别意图，不复用上一执行残留。

        复用实例下 `_state.status` 残留为 END/USER_INTERACT 时，
        `_get_intent_result` 会走"非 START 即复用旧 intent_result/branch_id"
        分支 → 静默选错分支。本用例驱动真实 `_get_intent_result`
        （`_intent_detection.invoke` 打桩），第一次执行经真实
        `_execute_branch_workflow` 把 `_state.status` 推到 END（branch_0 无
        configs → 早返回），第二次执行必须再次调用意图识别并返回新结果。
        """
        comp = _complex_component()
        session = MagicMock()
        session.get_session_id = MagicMock(return_value="sess-1")
        detected = []

        async def _fake_detect(inputs, session_, context, **kwargs):
            index = len(detected)
            detected.append(inputs.get("input"))
            return {"classificationId": index, "result": f"分类{index}"}

        comp._intent_detection = MagicMock()
        comp._intent_detection.invoke = _fake_detect

        first = await comp.invoke({"input": "查天气"}, session, MagicMock())
        assert first["classificationId"] == 0
        # 第一次执行结束：真实 _execute_branch_workflow 把状态推到 END（残留面）
        from agent_runtime.extension.workflow_node.complex_intent_detection import (
            ExecutionStatus,
        )

        assert comp._state.status == ExecutionStatus.END

        second = await comp.invoke({"input": "再见"}, session, MagicMock())

        assert detected == ["查天气", "再见"]
        assert second["classificationId"] == 1

    @pytest.mark.asyncio
    async def test_sub_workflow_cache_is_per_execution(self):
        """子工作流实例缓存为本次 invoke 局部：每次执行从空缓存开始（不残留）。"""
        from agent_runtime.extension.workflow_node.complex_intent_detection import (
            ComplexIntentDetection,
        )

        comp = ComplexIntentDetection(
            _complex_conf_with_branch_workflow(), node_id="cid_node", node_name="cid"
        )
        session = MagicMock()
        session.get_session_id = MagicMock(return_value="sess-1")
        comp._get_intent_result = AsyncMock(
            return_value=({"classificationId": 0}, "branch_0")
        )
        seen = []

        async def _fake_init(workflow_id, branch_config, sub_workflows):
            seen.append(dict(sub_workflows))
            sub_workflows[workflow_id] = {
                "instance": None,
                "sub_instance": None,
                "configs": {},
            }

        comp._init_sub_workflow = _fake_init

        await comp.invoke({"input": "a"}, session, MagicMock())
        await comp.invoke({"input": "b"}, session, MagicMock())

        # 每次执行都从空缓存开始（跨执行无残留），且实例上无缓存字段
        assert seen == [{}, {}]
        assert not hasattr(comp, "_sub_workflows")
