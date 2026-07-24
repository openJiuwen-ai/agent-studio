# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Tests for PlanExecute workflow arguments propagation.

Covers fix 11ea5b26 (R08): non-query arguments were dropped when
PlanExecute mode calls a Workflow tool. The fix passes the full
``arguments`` dict through ``_create_workflow_task`` → ``input_data``
and injects it into ``global_variables`` in ``stream_handle_workflow_from_plan_execute``.
"""
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
