# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Tests for PlanExecute workflow arguments propagation.

Covers fix 11ea5b26 (R08): non-query arguments were dropped when
PlanExecute mode calls a Workflow tool. The fix passes the full
``arguments`` dict through ``_create_workflow_task`` → ``input_data``
and injects it into ``global_variables`` in ``stream_handle_workflow_from_plan_execute``.
"""
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from jiuwen.controller.common.constants import WorkflowConstants


class TestCreateWorkflowTaskArguments:
    """_create_workflow_task should include arguments in input_data."""

    @staticmethod
    def _make_mode():
        """创建一个最小化的 PlanExecuteMode 实例，绕过复杂初始化."""
        with patch(
            "jiuwen.controller.agent.control_mode.plan_execute_mode.PlanExecuteMode.__init__",
            return_value=None,
        ):
            from jiuwen.controller.agent.control_mode.plan_execute_mode import (
                PlanExecuteMode,
            )

            mode = PlanExecuteMode()
            mode.task_id = "task-001"
            # pylint: disable=protected-access
            mode._current_query = "hello"
            mode._conversation_id = "conv-001"
            mode._runtime_context = {}
            mode._workflow_req_params = {}
            # pylint: enable=protected-access
            mode.context_manager = MagicMock()
            mode.context_manager.get_global_variables.return_value = {}
            return mode

    def test_input_data_contains_arguments(self):
        """input_data 中应包含 arguments 字段."""
        mode = self._make_mode()
        workflow_context = MagicMock()
        workflow_context.workflow_id = "wf-001"

        task = mode._create_workflow_task(  # pylint: disable=protected-access
            workflow_context, "tool-call-1", {"query": "hello", "order_id": "3049", "city": "sh"}
        )

        assert "arguments" in task.input_data
        assert task.input_data["arguments"]["order_id"] == "3049"
        assert task.input_data["arguments"]["city"] == "sh"
        assert task.input_data["arguments"]["query"] == "hello"

    def test_input_data_arguments_empty_when_none(self):
        """arguments 为 None 时 input_data 中 arguments 应为空 dict."""
        mode = self._make_mode()
        workflow_context = MagicMock()
        workflow_context.workflow_id = "wf-002"

        task = mode._create_workflow_task(workflow_context, "tool-call-2", None)  # pylint: disable=protected-access

        assert "arguments" in task.input_data
        assert task.input_data["arguments"] == {}

    def test_input_data_arguments_preserves_all_keys(self):
        """多参数场景下所有非 query 参数都应保留."""
        mode = self._make_mode()
        workflow_context = MagicMock()
        workflow_context.workflow_id = "wf-003"

        args = {"query": "q", "a": 1, "b": "text", "c": [1, 2, 3]}
        task = mode._create_workflow_task(workflow_context, "tool-call-3", args)  # pylint: disable=protected-access

        assert task.input_data["arguments"] == args


class TestWorkflowHandlerArgumentsInjection:
    """
    WorkflowHandler.stream_handle_workflow_from_plan_execute should inject
    non-query arguments into global_variables.
    """

    @staticmethod
    def test_arguments_injected_into_global_variables():
        """非 query 参数应被注入到 workflow_req_params['global_variables']."""
        from jiuwen.controller.task_executor.handler.workflow_handler import WorkflowHandler

        # 构造一个最小化的 WorkflowHandler
        handler = WorkflowHandler.__new__(WorkflowHandler)

        # 构造 task mock
        task = MagicMock()
        task.input_data = {
            WorkflowConstants.WORKFLOW_REQ_PARAMS_KEY: {
                "global_variables": {"existing": "value"},
            },
            "arguments": {"query": "hello", "order_id": "3049", "city": "sh"},
        }
        task.workflow_context = MagicMock()
        task.workflow_context.workflow_name = "test-flow"

        # mock prepare_workflow_params 返回带 global_variables 的 req_params
        handler.prepare_workflow_params = MagicMock(
            return_value={
                "global_variables": {"existing": "value"},
            }
        )

        # mock _stream_execute_workflow 返回空异步生成器
        async def empty_gen(*args, **kwargs):
            return
            yield  # make it an async generator

        handler._stream_execute_workflow = empty_gen  # pylint: disable=protected-access

        import asyncio

        async def run():
            results = []
            async for item in handler.stream_handle_workflow_from_plan_execute(task):
                results.append(item)
            return results

        asyncio.run(run())

        # 验证 global_variables 中注入了非 query 参数
        called_params = handler.prepare_workflow_params.return_value
        # prepare_workflow_params 返回的 dict 会被原地修改
        global_vars = called_params["global_variables"]
        assert global_vars["order_id"] == "3049"
        assert global_vars["city"] == "sh"
        assert "query" not in global_vars or global_vars.get("query") != "hello"
        # 已有值应保留
        assert global_vars["existing"] == "value"

    @staticmethod
    def test_no_arguments_no_injection():
        """没有 arguments 时不修改 global_variables."""
        from jiuwen.controller.task_executor.handler.workflow_handler import WorkflowHandler

        handler = WorkflowHandler.__new__(WorkflowHandler)

        task = MagicMock()
        task.input_data = {
            WorkflowConstants.WORKFLOW_REQ_PARAMS_KEY: {},
            "arguments": {},
        }
        task.workflow_context = MagicMock()
        task.workflow_context.workflow_name = "test-flow"

        original_gv = {"existing": "value"}
        handler.prepare_workflow_params = MagicMock(
            return_value={"global_variables": dict(original_gv)}
        )

        async def empty_gen(*args, **kwargs):
            return
            yield

        handler._stream_execute_workflow = empty_gen  # pylint: disable=protected-access

        import asyncio

        async def run():
            results = []
            async for item in handler.stream_handle_workflow_from_plan_execute(task):
                results.append(item)
            return results

        asyncio.run(run())

        # global_variables 应只有原有值，没有新注入
        called_params = handler.prepare_workflow_params.return_value
        assert called_params["global_variables"] == original_gv


class TestGenerateFinalStatusMessageTypeProtection:
    """_generate_final_status_message 中 str(x) 防御性类型转换的 UT.

    PR #1641: "".join(workflow_status.get("final_answer", [])) 假设列表元素
    全为字符串，加了 str(x) 保护。此测试验证各种非字符串类型能被正确转换，
    不会抛出 TypeError。
    """

    @staticmethod
    def _make_handler():
        """构造最小化 WorkflowHandler，跳过 __init__."""
        from jiuwen.controller.task_executor.handler.workflow_handler import (
            WorkflowHandler,
        )

        handler = WorkflowHandler.__new__(WorkflowHandler)
        handler.context_manager = MagicMock()
        handler.task_id = "test-task-id"
        return handler

    @staticmethod
    def _make_workflow_context():
        """构造最小化 WorkflowContext."""
        from jiuwen.controller.context_manager.workflow_context import WorkflowContext
        from jiuwen.controller.common.enum import WorkflowType

        return WorkflowContext(
            workflow_id="wf-test",
            workflow_name="test-workflow",
            description="test",
            type=WorkflowType.GENERAL,
        )

    @pytest.mark.parametrize(
        "final_answer, expected",
        [
            pytest.param(["hello", " world"], "hello world", id="normal-strings"),
            pytest.param(["count:", 42], "count:42", id="int-mixed"),
            pytest.param(["data:", {"k": "v"}], "data:{'k': 'v'}", id="dict-mixed"),
            pytest.param(["items:", [1, 2]], "items:[1, 2]", id="list-mixed"),
            pytest.param(["a", None, "b"], "aNoneb", id="none-element"),
            pytest.param([], "", id="empty-list"),
        ],
    )
    def test_final_answer_type_protection(self, final_answer, expected):
        """final_answer 列表中混入非字符串类型时，str(x) 应正确转换."""
        import asyncio
        from jiuwen.controller.common.message import Message
        from jiuwen.controller.common.message_type import MessageType

        handler = self._make_handler()
        wf_ctx = self._make_workflow_context()
        workflow_status = {
            "workflow_end": True,
            "questioner_interrupted": False,
            "final_answer": final_answer,
        }

        async def run():
            results = []
            async for item in handler._generate_final_status_message(  # pylint: disable=protected-access
                wf_ctx, None, workflow_status
            ):
                results.append(item)
            return results

        results = asyncio.run(run())

        assert len(results) == 1
        assert isinstance(results[0], Message)
        assert results[0].message_type == MessageType.WORKFLOW_COMPLETION
        assert results[0].content["exec_res"]["answer"] == expected

        handler.context_manager.update_workflow_status.assert_called_once()
        handler.context_manager.set_workflow_state.assert_called_once()

    def test_final_answer_missing_key(self):
        """workflow_status 中没有 final_answer key 时，.get 默认返回空列表."""
        import asyncio
        from jiuwen.controller.common.message import Message

        handler = self._make_handler()
        wf_ctx = self._make_workflow_context()
        workflow_status = {
            "workflow_end": True,
            "questioner_interrupted": False,
            # 没有 final_answer key
        }

        async def run():
            results = []
            async for item in handler._generate_final_status_message(  # pylint: disable=protected-access
                wf_ctx, None, workflow_status
            ):
                results.append(item)
            return results

        results = asyncio.run(run())

        assert len(results) == 1
        assert isinstance(results[0], Message)
        assert results[0].content["exec_res"]["answer"] == ""


# ===========================================================================
# Scene tool/workflow filtering — 精确匹配 + guideline 聚合 + 操作级隔离
# ===========================================================================
"""
Java IR parsePluginConfig 确保 plugin.name 包含 operation 后缀
（如 'zhinenghuiyizhushoucreate_meeting'），前端 scene.tools 也存完整 operation 名，
Runtime 精确匹配实现操作级工具隔离。
"""
from jiuwen.controller.common.config import SceneConfig, GuidelineConfig


def _plugin(full_name: str) -> SimpleNamespace:
    """模拟 RestFulAPI 插件对象。"""
    return SimpleNamespace(name=full_name)


def _workflow_ctx(wf_name: str) -> SimpleNamespace:
    """模拟工作流上下文对象。"""
    return SimpleNamespace(workflow_name=wf_name, description="test workflow")


class TestPlannerFilterToolsByScene:  # pylint: disable=protected-access
    """PlanExecutePlanner._filter_tools_by_scene — 精确匹配 + guideline 聚合 + 操作级隔离。"""

    @staticmethod
    def _make_planner(plugins=None):
        from jiuwen.controller.task_planner.planners.plan_execute_planner import (
            PlanExecutePlanner,
        )
        obj = PlanExecutePlanner.__new__(PlanExecutePlanner)
        obj.plugins = plugins or []
        obj.task_id = "test-001"
        return obj

    def test_no_scene_returns_all(self):
        """场景未匹配 → 返回全部插件。"""
        plugins = [_plugin("p1_create"), _plugin("p2_query")]
        planner = self._make_planner(plugins)
        assert len(planner._filter_tools_by_scene(None)) == 2

    def test_exact_match_multiple_operations(self):
        """scene.tools 存完整 operation 名 → 精确匹配命中指定的多个 operation。"""
        plugins = [
            _plugin("zhinenghuiyizhushoucreate_meeting"),
            _plugin("zhinenghuiyizhushouquery_meetings"),
            _plugin("zhinenghuiyizhushouget_meeting"),
            _plugin("zhinenghuiyizhushoucancel_meeting"),
        ]
        planner = self._make_planner(plugins)
        scene = SceneConfig(id="s1", name="会议", description="",
                            tools=["zhinenghuiyizhushoucreate_meeting",
                                   "zhinenghuiyizhushouquery_meetings"])
        result = planner._filter_tools_by_scene(scene)
        assert len(result) == 2
        names = {p.name for p in result}
        assert "zhinenghuiyizhushoucreate_meeting" in names
        assert "zhinenghuiyizhushouquery_meetings" in names

    def test_operation_level_isolation(self):
        """操作级隔离：选 create_meeting 不应放行 query_meetings。"""
        plugins = [
            _plugin("zhinenghuiyizhushoucreate_meeting"),
            _plugin("zhinenghuiyizhushouquery_meetings"),
        ]
        planner = self._make_planner(plugins)
        scene = SceneConfig(id="s1", name="创建", description="",
                            tools=["zhinenghuiyizhushoucreate_meeting"])
        result = planner._filter_tools_by_scene(scene)
        assert len(result) == 1
        assert result[0].name == "zhinenghuiyizhushoucreate_meeting"

    def test_no_match(self):
        """不相关的工具名 → 过滤为空。"""
        planner = self._make_planner([_plugin("other_plugin_action")])
        scene = SceneConfig(id="s1", name="会议", description="",
                            tools=["zhinenghuiyizhushoucreate_meeting"])
        assert len(planner._filter_tools_by_scene(scene)) == 0

    def test_guideline_aggregation(self):
        """scene.tools 为空 → 从 guidelines 聚合完整 operation 名。"""
        plugins = [_plugin("pluginb_action1"), _plugin("plugina_action2")]
        planner = self._make_planner(plugins)
        scene = SceneConfig(id="s1", name="test", description="", tools=[],
                            guidelines=[
                                GuidelineConfig(id=1, condition="c1", action="a1",
                                                tools=["pluginb_action1"]),
                                GuidelineConfig(id=2, condition="c2", action="a2",
                                                tools=["plugina_action2"]),
                            ])
        assert len(planner._filter_tools_by_scene(scene)) == 2

    def test_empty_tool_name_ignored(self):
        """scene.tools 中的空字符串不导致匹配所有。"""
        plugins = [_plugin("pluginA_action1")]
        planner = self._make_planner(plugins)
        scene = SceneConfig(id="s1", name="test", description="",
                            tools=["", "pluginA_action1"])
        assert len(planner._filter_tools_by_scene(scene)) == 1


class TestModeFilterPluginsByScene:  # pylint: disable=protected-access
    """PlanExecuteMode._filter_plugins_by_scene — 执行阶段精确匹配 + 操作级隔离。"""

    @staticmethod
    def _make_mode():
        """构造 PlanExecuteMode，mock 掉重型导入链。"""
        _mocks = {}
        for mod in ("model_service.env_resolver", "model_service.env_resolver"):
            if mod not in sys.modules:
                sys.modules[mod] = MagicMock()
                _mocks[mod] = True
        try:
            from jiuwen.controller.agent.control_mode.plan_execute_mode import (
                PlanExecuteMode,
            )
        finally:
            for mod in _mocks:
                del sys.modules[mod]
        obj = PlanExecuteMode.__new__(PlanExecuteMode)
        obj.task_id = "test-001"
        obj._skill_context = None
        return obj

    def test_exact_match(self):
        """精确匹配命中指定 operation。"""
        plugins = [
            _plugin("zhinenghuiyizhushoucreate_meeting"),
            _plugin("zhinenghuiyizhushouquery_meetings"),
            _plugin("other_plugin_action"),
        ]
        mode = self._make_mode()
        scene = SceneConfig(id="s1", name="会议", description="",
                            tools=["zhinenghuiyizhushoucreate_meeting",
                                   "zhinenghuiyizhushouquery_meetings"])
        result = mode._filter_plugins_by_scene(plugins, scene)
        assert len(result) == 2

    def test_skill_injection_merged(self):
        """skill 注入的工具名与 scene.tools 合并。"""
        plugins = [_plugin("zhinenghuiyizhushoucreate_meeting"), _plugin("read_file")]
        mode = self._make_mode()
        mode._skill_context = SimpleNamespace(tool_names={"read_file"})
        scene = SceneConfig(id="s1", name="会议", description="",
                            tools=["zhinenghuiyizhushoucreate_meeting"])
        result = mode._filter_plugins_by_scene(plugins, scene)
        assert len(result) == 2

    def test_no_scene_returns_all(self):
        """场景未匹配 → 返回全部。"""
        plugins = [_plugin("p1"), _plugin("p2")]
        mode = self._make_mode()
        assert len(mode._filter_plugins_by_scene(plugins, None)) == 2

    def test_operation_level_isolation(self):
        """操作级隔离：选 create 不放行 query。"""
        plugins = [
            _plugin("zhinenghuiyizhushoucreate_meeting"),
            _plugin("zhinenghuiyizhushouquery_meetings"),
        ]
        mode = self._make_mode()
        scene = SceneConfig(id="s1", name="创建", description="",
                            tools=["zhinenghuiyizhushoucreate_meeting"])
        result = mode._filter_plugins_by_scene(plugins, scene)
        assert len(result) == 1
        assert result[0].name == "zhinenghuiyizhushoucreate_meeting"
