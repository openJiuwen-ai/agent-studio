# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# pylint: disable=protected-access  # 单元测试需直接验证内部方法行为
"""Tests for workflow_name propagation in SSE streaming events.

Covers the fix that adds workflow_name to:
  1. OpenJiuWenWorkflowInstanceLayer._normalize_astream_args / astream
  2. WorkflowWrapper.astream WORKFLOW_START event data
  3. WorkflowHandler._stream_handle_workflow_execute StreamData injection
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from jiuwen.extension.wrapper.workflow_instance_layer import (
    OpenJiuWenWorkflowInstanceLayer,
)
from jiuwen.orchestration.flow.stream.base import StreamData, StreamCode


# =====================================================================
# 1. OpenJiuWenWorkflowInstanceLayer — workflow_name 传递验证
# =====================================================================


class TestWorkflowInstanceLayerWorkflowName:
    """OpenJiuWenWorkflowInstanceLayer 应正确接受和传递 workflow_name。"""

    @staticmethod
    def test_constructor_stores_workflow_name():
        """构造函数应保存 workflow_name 到实例属性。"""
        layer = OpenJiuWenWorkflowInstanceLayer(
            workflow_id="wf-123",
            workflow_name="LLM1138",
        )
        assert layer.workflow_name == "LLM1138"

    @staticmethod
    def test_constructor_default_empty_string():
        """未传 workflow_name 时默认为空字符串。"""
        layer = OpenJiuWenWorkflowInstanceLayer()
        assert layer.workflow_name == ""

    @staticmethod
    def test_normalize_astream_args_extracts_workflow_name_from_kwargs():
        """_normalize_astream_args 应从 kwargs 中提取 workflow_name。"""
        layer = OpenJiuWenWorkflowInstanceLayer(
            workflow_id="wf-123",
            workflow_name="FallbackName",
        )
        result = layer._normalize_astream_args(
            args=(),
            kwargs={"query": "hello", "workflow_name": "KwargName"},
        )
        # 返回 _AstreamArgs，workflow_name 字段应从 kwargs 提取
        assert result.workflow_name == "KwargName"

    @staticmethod
    def test_normalize_astream_args_falls_back_to_instance_attr():
        """kwargs 中没有 workflow_name 时，应 fallback 到实例属性。"""
        layer = OpenJiuWenWorkflowInstanceLayer(
            workflow_id="wf-123",
            workflow_name="InstanceName",
        )
        result = layer._normalize_astream_args(
            args=("hello",),
            kwargs={},
        )
        assert result.workflow_name == "InstanceName"

    @staticmethod
    def test_normalize_astream_args_default_empty():
        """没有 kwargs 也没有实例属性时，workflow_name 应为空字符串。"""
        layer = OpenJiuWenWorkflowInstanceLayer()
        result = layer._normalize_astream_args(
            args=("hello",),
            kwargs={},
        )
        assert result.workflow_name == ""

    @staticmethod
    def test_normalize_astream_args_returns_named_tuple():
        """_normalize_astream_args 应返回 _AstreamArgs。"""
        layer = OpenJiuWenWorkflowInstanceLayer(
            workflow_id="wf-1",
            workflow_name="WF",
        )
        result = layer._normalize_astream_args(
            args=(),
            kwargs={"query": "q"},
        )
        assert result.query == "q"
        assert result.workflow_id == "wf-1"
        assert result.workflow_name == "WF"

    @staticmethod
    def test_normalize_astream_args_kwargs_workflow_name_overrides_instance():
        """kwargs 中的 workflow_name 优先于实例属性。"""
        layer = OpenJiuWenWorkflowInstanceLayer(
            workflow_id="wf-1",
            workflow_name="InstanceName",
        )
        result = layer._normalize_astream_args(
            args=(),
            kwargs={"query": "q", "workflow_name": "KwargOverride"},
        )
        assert result.workflow_name == "KwargOverride"


# =====================================================================
# 2. WorkflowWrapper.astream — 验证 super().astream() 调用传递 workflow_name
# =====================================================================


class TestWorkflowWrapperAstreamWorkflowName:
    """OpenJiuWenWorkflowInstanceLayer.astream 应将 workflow_name 传递给 super().astream()。"""

    @pytest.mark.asyncio
    async def test_astream_passes_workflow_name_to_super(self):
        """astream 应将 workflow_name 传递给 super().astream()。"""
        layer = OpenJiuWenWorkflowInstanceLayer(
            workflow_id="wf-test",
            workflow_name="TestWorkflow",
        )

        async def empty_gen():
            return
            yield

        with patch.object(
            OpenJiuWenWorkflowInstanceLayer.__bases__[0],
            "astream",
            return_value=empty_gen(),
        ) as mock_super_astream:
            gen = layer.astream(query="hello", params={})
            async_gen = await gen
            async for _ in async_gen:
                pass

            mock_super_astream.assert_called_once()
            call_kwargs = mock_super_astream.call_args[1]
            assert call_kwargs.get("workflow_name") == "TestWorkflow"
            assert call_kwargs.get("workflow_id") == "wf-test"

    @pytest.mark.asyncio
    async def test_astream_passes_empty_name_when_not_provided(self):
        """未提供 workflow_name 时，应传递空字符串给 super().astream()。"""
        layer = OpenJiuWenWorkflowInstanceLayer(
            workflow_id="wf-no-name",
        )

        async def empty_gen():
            return
            yield

        with patch.object(
            OpenJiuWenWorkflowInstanceLayer.__bases__[0],
            "astream",
            return_value=empty_gen(),
        ) as mock_super_astream:
            gen = layer.astream(query="hello", params={})
            async_gen = await gen
            async for _ in async_gen:
                pass

            call_kwargs = mock_super_astream.call_args[1]
            assert call_kwargs.get("workflow_name") == ""

    @pytest.mark.asyncio
    async def test_astream_kwargs_workflow_name_overrides_constructor(self):
        """astream kwargs 中的 workflow_name 应覆盖构造时的值。"""
        layer = OpenJiuWenWorkflowInstanceLayer(
            workflow_id="wf-override",
            workflow_name="ConstructorName",
        )

        async def empty_gen():
            return
            yield

        with patch.object(
            OpenJiuWenWorkflowInstanceLayer.__bases__[0],
            "astream",
            return_value=empty_gen(),
        ) as mock_super_astream:
            gen = layer.astream(
                query="hello", params={}, workflow_name="KwargName"
            )
            async_gen = await gen
            async for _ in async_gen:
                pass

            call_kwargs = mock_super_astream.call_args[1]
            assert call_kwargs.get("workflow_name") == "KwargName"


# =====================================================================
# 3. WorkflowWrapper.astream WORKFLOW_START 事件 data 验证
#    需要 workflow.stream() 至少产生一个 chunk 才能触发 WORKFLOW_START
# =====================================================================


class TestWorkflowWrapperStartEventData:
    """WorkflowWrapper.astream 产出的 WORKFLOW_START 事件 data 应包含 workflow_name。"""

    @staticmethod
    def _make_output_schema_chunk():
        """构造一个 OutputSchema chunk，触发 WORKFLOW_START 产出。"""
        from openjiuwen.core.session.stream.base import OutputSchema

        return OutputSchema(
            type="partial_content",
            payload={"answer": "hi", "node_id": "n1", "node_name": "N1", "node_type": "LLM"},
            index=0,
        )

    @pytest.mark.asyncio
    async def test_workflow_start_event_data_contains_workflow_name(self):
        """WORKFLOW_START 事件的 data 字典应包含 workflow_name 和 workflow_id。"""
        from jiuwen.extension.wrapper.workflow_wrapper import WorkflowWrapper

        wrapper = WorkflowWrapper(node_name_type_map={})

        mock_workflow = MagicMock()
        chunk = self._make_output_schema_chunk()

        async def single_chunk_stream(*args, **kwargs):
            yield chunk

        mock_workflow.stream = MagicMock(return_value=single_chunk_stream())

        with patch(
            "openjiuwen.core.session.workflow.create_workflow_session"
        ):
            with patch(
                "openjiuwen.core.runner.Runner.resource_mgr"
            ) as mock_rm:
                mock_rm.get_workflow = AsyncMock(return_value=mock_workflow)
                events = []
                async for event in wrapper.astream(
                    query="hello",
                    params={},
                    workflow_id="wf-start-test",
                    workflow_name="StartEventTest",
                ):
                    events.append(event)

        # 第一个事件应为 WORKFLOW_START
        assert len(events) >= 1
        start_event = events[0]
        assert isinstance(start_event, StreamData)
        assert start_event.code == StreamCode.WORKFLOW_START.value
        assert start_event.data.get("workflow_id") == "wf-start-test"
        assert start_event.data.get("workflow_name") == "StartEventTest"

    @pytest.mark.asyncio
    async def test_workflow_start_event_data_empty_name(self):
        """未传 workflow_name 时，WORKFLOW_START 的 data 中 workflow_name 应为空字符串。"""
        from jiuwen.extension.wrapper.workflow_wrapper import WorkflowWrapper

        wrapper = WorkflowWrapper(node_name_type_map={})

        mock_workflow = MagicMock()
        chunk = self._make_output_schema_chunk()

        async def single_chunk_stream(*args, **kwargs):
            yield chunk

        mock_workflow.stream = MagicMock(return_value=single_chunk_stream())

        with patch(
            "openjiuwen.core.session.workflow.create_workflow_session"
        ):
            with patch(
                "openjiuwen.core.runner.Runner.resource_mgr"
            ) as mock_rm:
                mock_rm.get_workflow = AsyncMock(return_value=mock_workflow)
                events = []
                async for event in wrapper.astream(
                    query="hello",
                    params={},
                    workflow_id="wf-start-empty",
                ):
                    events.append(event)

        assert len(events) >= 1
        start_event = events[0]
        assert start_event.code == StreamCode.WORKFLOW_START.value
        assert start_event.data.get("workflow_name") == ""


# =====================================================================
# 4. WorkflowHandler._stream_handle_workflow_execute — StreamData 注入
# =====================================================================


class TestWorkflowHandlerStreamDataInjection:
    """WorkflowHandler 应在每个 StreamData 上注入 workflow_id 和 workflow_name。"""

    @staticmethod
    def _make_workflow_context(**overrides):
        """构造模拟的 workflow_context 对象。"""
        ctx = MagicMock()
        ctx.workflow_id = overrides.get("workflow_id", "wf-123")
        ctx.workflow_name = overrides.get("workflow_name", "LLM1138")
        ctx.description = overrides.get("description", "test workflow")
        ctx.workflow_ir = overrides.get("workflow_ir", {})
        ctx.state = overrides.get("state", None)
        ctx.action_after_completion = None
        return ctx

    @staticmethod
    def _make_handler():
        """构造 WorkflowHandler 实例，仅设置必要属性。"""
        from jiuwen.controller.task_executor.handler.workflow_handler import (
            WorkflowHandler,
        )

        handler = WorkflowHandler.__new__(WorkflowHandler)
        handler.task_id = "test-task"
        handler.context_manager = MagicMock()
        return handler

    @pytest.mark.asyncio
    async def test_partial_content_event_injects_workflow_id_and_name(self):
        """PARTIAL_CONTENT 类型的 StreamData 应被注入 workflow_id 和 workflow_name。"""
        handler = self._make_handler()
        workflow_context = self._make_workflow_context(
            workflow_id="wf-abc", workflow_name="MyWorkflow"
        )

        mock_wf_instance = MagicMock()
        stream_data = StreamData(
            code=StreamCode.PARTIAL_CONTENT.value,
            msg="success",
            data={"answer": "hello"},
            execution_id="exec-1",
        )

        # astream 是 async def + return，所以 await astream() 得到 async generator
        # 需要模拟: await workflow_instance.astream(**workflow_input) → async generator
        async def _inner_gen():
            yield stream_data

        async def _coroutine_returning_gen(**kwargs):
            return _inner_gen()

        mock_wf_instance.astream = _coroutine_returning_gen

        workflow_status = {
            "is_first_message": True,
            "questioner_interrupted": False,
        }
        workflow_input = {"query": "test query", "params": {}}

        results = []
        async for output in handler._stream_handle_workflow_execute(
            workflow_input=workflow_input,
            workflow_context=workflow_context,
            workflow_instance=mock_wf_instance,
            workflow_status=workflow_status,
            is_intent_workflow=False,
            from_pe=False,
        ):
            results.append(output)

        assert len(results) >= 1
        for event in results:
            if hasattr(event, "data") and event.data:
                assert event.data.get("workflow_id") == "wf-abc", (
                    "所有 StreamData 应包含 workflow_id"
                )
                assert event.data.get("workflow_name") == "MyWorkflow", (
                    "所有 StreamData 应包含 workflow_name"
                )

    @pytest.mark.asyncio
    async def test_workflow_end_event_injects_workflow_id_and_name(self):
        """WORKFLOW_END 类型的 StreamData 也应被注入 workflow_id 和 workflow_name。"""
        handler = self._make_handler()
        workflow_context = self._make_workflow_context(
            workflow_id="wf-end", workflow_name="EndWorkflow"
        )

        mock_wf_instance = MagicMock()

        async def _inner_gen():
            yield StreamData(
                code=StreamCode.PARTIAL_CONTENT.value,
                msg="success",
                data={"answer": "content"},
                execution_id="exec-1",
            )
            yield StreamData(
                code=StreamCode.WORKFLOW_END.value,
                msg="success",
                data={"answer": "final"},
                execution_id="exec-1",
            )

        async def _coroutine_returning_gen(**kwargs):
            return _inner_gen()

        mock_wf_instance.astream = _coroutine_returning_gen

        workflow_status = {
            "is_first_message": True,
            "questioner_interrupted": False,
        }
        workflow_input = {"query": "test query", "params": {}}

        results = []
        async for output in handler._stream_handle_workflow_execute(
            workflow_input=workflow_input,
            workflow_context=workflow_context,
            workflow_instance=mock_wf_instance,
            workflow_status=workflow_status,
            is_intent_workflow=False,
            from_pe=False,
        ):
            results.append(output)

        for event in results:
            if hasattr(event, "data") and event.data:
                assert event.data.get("workflow_id") == "wf-end"
                assert event.data.get("workflow_name") == "EndWorkflow"

    @pytest.mark.asyncio
    async def test_empty_data_stream_event_gets_workflow_name(self):
        """data 为空字典的 StreamData 也应被注入 workflow_id 和 workflow_name。"""
        handler = self._make_handler()
        workflow_context = self._make_workflow_context(
            workflow_id="wf-empty", workflow_name="EmptyData"
        )

        mock_wf_instance = MagicMock()

        async def _inner_gen():
            yield StreamData(
                code=StreamCode.PARTIAL_CONTENT.value,
                msg="success",
                data={},
                execution_id="exec-1",
            )

        async def _coroutine_returning_gen(**kwargs):
            return _inner_gen()

        mock_wf_instance.astream = _coroutine_returning_gen

        workflow_status = {
            "is_first_message": True,
            "questioner_interrupted": False,
        }
        workflow_input = {"query": "test query", "params": {}}

        results = []
        async for output in handler._stream_handle_workflow_execute(
            workflow_input=workflow_input,
            workflow_context=workflow_context,
            workflow_instance=mock_wf_instance,
            workflow_status=workflow_status,
            is_intent_workflow=False,
            from_pe=False,
        ):
            results.append(output)

        # 空 data 字典也应被注入 workflow_id 和 workflow_name
        assert len(results) >= 1
        for event in results:
            if hasattr(event, "data") and event.data:
                assert event.data.get("workflow_id") == "wf-empty"
                assert event.data.get("workflow_name") == "EmptyData"

    @pytest.mark.asyncio
    async def test_multiple_events_all_get_workflow_name(self):
        """多个 StreamData 事件都应被注入 workflow_id 和 workflow_name。"""
        handler = self._make_handler()
        workflow_context = self._make_workflow_context(
            workflow_id="wf-multi", workflow_name="MultiEvent"
        )

        mock_wf_instance = MagicMock()

        async def _inner_gen():
            yield StreamData(
                code=StreamCode.PARTIAL_CONTENT.value,
                msg="success",
                data={"answer": "first"},
                execution_id="exec-1",
            )
            yield StreamData(
                code=StreamCode.PARTIAL_CONTENT.value,
                msg="success",
                data={"answer": "second"},
                execution_id="exec-1",
            )
            yield StreamData(
                code=StreamCode.WORKFLOW_END.value,
                msg="success",
                data={"answer": "done"},
                execution_id="exec-1",
            )

        async def _coroutine_returning_gen(**kwargs):
            return _inner_gen()

        mock_wf_instance.astream = _coroutine_returning_gen

        workflow_status = {
            "is_first_message": True,
            "questioner_interrupted": False,
        }
        workflow_input = {"query": "test query", "params": {}}

        results = []
        async for output in handler._stream_handle_workflow_execute(
            workflow_input=workflow_input,
            workflow_context=workflow_context,
            workflow_instance=mock_wf_instance,
            workflow_status=workflow_status,
            is_intent_workflow=False,
            from_pe=False,
        ):
            results.append(output)

        # 所有有 data 的事件都应有 workflow_id 和 workflow_name
        events_with_data = [e for e in results if hasattr(e, "data") and e.data]
        assert len(events_with_data) >= 1
        for event in events_with_data:
            assert event.data.get("workflow_id") == "wf-multi"
            assert event.data.get("workflow_name") == "MultiEvent"
