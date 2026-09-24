#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

"""nl2 模块单元测试"""
# pylint: disable=no-self-use

import hashlib
import json
import sys
import types
from unittest.mock import MagicMock, patch

import pytest


def _setup_nl2_mocks():
    if "psycopg2" not in sys.modules:
        psycopg2_mock = types.ModuleType("psycopg2")
        psycopg2_mock.sql = MagicMock()
        psycopg2_mock.extras = types.ModuleType("psycopg2.extras")
        psycopg2_mock.extras.execute_values = MagicMock()
        sys.modules["psycopg2"] = psycopg2_mock
        sys.modules["psycopg2.extras"] = psycopg2_mock.extras

    if "jiuwen.serve.controllers.execution.manager" not in sys.modules:
        manager_mock = types.ModuleType("jiuwen.serve.controllers.execution.manager")
        manager_mock.StateManager = MagicMock
        sys.modules["jiuwen.serve.controllers.execution.manager"] = manager_mock


_setup_nl2_mocks()


from agent_builder.nl_to_agent.nl2 import (
    AGENT_TYPE_MAP,
    NL2_AGENT,
    EiCloudNl2AgentInfo,
    N2LRequestBody,
    SSEEvent,
    _error_sse_generator,
    _generate,
    _generate_optimize_task_job_id,
    _n2l_json_wapper,
)


class TestGenerateOptimizeTaskJobId:
    """_generate_optimize_task_job_id 函数测试"""

    @staticmethod
    def test_returns_string_with_jnt_prefix():
        """返回以 JNT_ 前缀开头的字符串"""
        result = _generate_optimize_task_job_id({"key": "value"})
        assert result.startswith("JNT_")

    @staticmethod
    def test_different_inputs_produce_different_ids():
        """不同输入产生不同 ID"""
        id1 = _generate_optimize_task_job_id({"key": "value1"})
        id2 = _generate_optimize_task_job_id({"key": "value2"})
        assert id1 != id2

    @staticmethod
    def test_same_input_same_output():
        """相同输入产生相同 ID（时间戳相同情况下）"""
        data = {"key": "value"}
        with patch("agent_builder.nl_to_agent.nl2.time") as mock_time:
            mock_time.time.return_value = 1000.0
            id1 = _generate_optimize_task_job_id(data)
            id2 = _generate_optimize_task_job_id(data)
        assert id1 == id2

    @staticmethod
    def test_custom_mode_prefix():
        """自定义 mode 前缀"""
        result = _generate_optimize_task_job_id({"key": "value"}, mode="CUSTOM")
        assert result.startswith("CUSTOM_")


class TestN2LRequestBody:
    """N2LRequestBody 模型测试"""

    @staticmethod
    def test_default_none_for_optional_fields():
        """可选字段默认为 None"""
        body = N2LRequestBody(query="test")
        assert body.model is None
        assert body.resource is None
        assert body.conversationId is None

    @staticmethod
    def test_assignment_works():
        """字段赋值正常工作"""
        from agent_builder.nl_to_agent.nl2 import N2LModel, N2LResource

        body = N2LRequestBody(
            query="test",
            model=N2LModel(modelName="model1"),
            resource=N2LResource(plugins={"p": 1}),
            conversationId="cid123",
        )
        assert body.query == "test"
        assert body.model.modelName == "model1"
        assert body.resource.plugins == {"p": 1}
        assert body.conversationId == "cid123"


class TestEiCloudNl2AgentInfo:
    """EiCloudNl2AgentInfo 模型测试"""

    @staticmethod
    def _make_valid_data():
        return {
            "conversationId": "conv1",
            "query": "build agent",
            "agentType": "llm_agent",
            "modelInfo": {
                "model": "test-model",
                "model_source": "nl2_agentBuilder_model",
            },
        }

    @staticmethod
    def test_valid_data_passes_validation():
        """有效数据通过验证"""
        data = TestEiCloudNl2AgentInfo._make_valid_data()
        info = EiCloudNl2AgentInfo.model_validate(data)
        assert info.conversationId == "conv1"
        assert info.query == "build agent"
        assert info.agentType == "llm_agent"

    @staticmethod
    def test_missing_required_field_raises():
        """缺少必填字段时抛出 ValidationError"""
        from pydantic import ValidationError

        data = TestEiCloudNl2AgentInfo._make_valid_data()
        del data["query"]
        with pytest.raises(ValidationError):
            EiCloudNl2AgentInfo.model_validate(data)

    @staticmethod
    def test_invalid_agent_type_raises():
        """无效的 agentType 值抛出 ValidationError"""
        from pydantic import ValidationError

        data = TestEiCloudNl2AgentInfo._make_valid_data()
        data["agentType"] = "invalid_type"
        with pytest.raises(ValidationError):
            EiCloudNl2AgentInfo.model_validate(data)

    @staticmethod
    def test_empty_conversation_id_raises():
        """空 conversationId 抛出 ValidationError"""
        from pydantic import ValidationError

        data = TestEiCloudNl2AgentInfo._make_valid_data()
        data["conversationId"] = ""
        with pytest.raises(ValidationError):
            EiCloudNl2AgentInfo.model_validate(data)

    @staticmethod
    def test_workflow_agent_type_valid():
        """workflow 类型的 agentType 有效"""
        data = TestEiCloudNl2AgentInfo._make_valid_data()
        data["agentType"] = "workflow"
        info = EiCloudNl2AgentInfo.model_validate(data)
        assert info.agentType == "workflow"


class TestSSEEvent:
    """SSEEvent 模型测试"""

    @staticmethod
    def test_to_sse_string_correct_format():
        """to_sse_string 输出正确的 SSE 格式"""
        event = SSEEvent(
            data="hello",
            event="MESSAGE",
            conversation_id="conv1",
        )
        sse_str = event.to_sse_string()
        assert sse_str.startswith("data: ")
        assert sse_str.endswith("\n\n")
        parsed = json.loads(sse_str[len("data: "):].strip())
        assert parsed["event"] == "MESSAGE"
        assert parsed["data"] == "hello"

    @staticmethod
    def test_conversation_id_alias():
        """conversationId 别名在序列化时生效"""
        event = SSEEvent(
            data="test",
            event="START",
            conversation_id="conv1",
        )
        sse_str = event.to_sse_string()
        parsed = json.loads(sse_str[len("data: "):].strip())
        assert "conversationId" in parsed
        assert parsed["conversationId"] == "conv1"


class TestN2lJsonWapper:
    """_n2l_json_wapper 函数测试"""

    @staticmethod
    def _make_req_json():
        return {
            "model": {
                "modelName": "test-model",
                "modelExplicitName": "Test Model",
                "extension": {"authId": "auth123"},
                "modelType": "LLM",
                "modelInterfaceProtocol": "openai",
            }
        }

    @staticmethod
    def _make_mock_request():
        mock_request = MagicMock()
        mock_request.headers = {"x-auth-token": "token123"}
        mock_request.query_params = {"workspace_id": "ws1"}
        return mock_request

    @patch("agent_builder.nl_to_agent.nl2.request_json")
    @staticmethod
    def test_maps_agent_type_agents(self, mock_request_json):
        """agents 类型映射为 llm_agent"""
        mock_request_json.get.return_value = {}
        mock_request_json.set = MagicMock()
        req_json = TestN2lJsonWapper._make_req_json()
        result = _n2l_json_wapper(
            "proj1", "agents", "conv1", req_json, TestN2lJsonWapper._make_mock_request()
        )
        assert result["agentType"] == "llm_agent"

    @patch("agent_builder.nl_to_agent.nl2.request_json")
    @staticmethod
    def test_maps_agent_type_workflows(self, mock_request_json):
        """workflows 类型映射为 workflow"""
        mock_request_json.get.return_value = {}
        mock_request_json.set = MagicMock()
        req_json = TestN2lJsonWapper._make_req_json()
        result = _n2l_json_wapper(
            "proj1", "workflows", "conv1", req_json, TestN2lJsonWapper._make_mock_request()
        )
        assert result["agentType"] == "workflow"

    @patch("agent_builder.nl_to_agent.nl2.request_json")
    @staticmethod
    def test_adds_project_id_and_conversation_id(self, mock_request_json):
        """添加 projectId 和 conversationId"""
        mock_request_json.get.return_value = {}
        mock_request_json.set = MagicMock()
        req_json = TestN2lJsonWapper._make_req_json()
        result = _n2l_json_wapper(
            "proj1", "agents", "conv1", req_json, TestN2lJsonWapper._make_mock_request()
        )
        assert result["projectId"] == "proj1"
        assert result["conversationId"] == "conv1"

    @patch("agent_builder.nl_to_agent.nl2.request_json")
    @staticmethod
    def test_builds_model_info_structure(self, mock_request_json):
        """构建 modelInfo 结构"""
        mock_request_json.get.return_value = {}
        mock_request_json.set = MagicMock()
        req_json = TestN2lJsonWapper._make_req_json()
        result = _n2l_json_wapper(
            "proj1", "agents", "conv1", req_json, TestN2lJsonWapper._make_mock_request()
        )
        assert "modelInfo" in result
        assert result["modelInfo"]["model"] == "test-model"
        assert result["modelInfo"]["model_source"] == NL2_AGENT
        assert "headers" in result["modelInfo"]
        headers = result["modelInfo"]["headers"]
        assert headers["agentBuilder_model_name"] == "test-model"
        assert headers["project_id"] == "proj1"
        assert headers["x_auth_token"] == "token123"
        assert headers["auth_id"] == "auth123"

    @patch("agent_builder.nl_to_agent.nl2.request_json")
    @staticmethod
    def test_unknown_agent_type_not_mapped(self, mock_request_json):
        """未知 agent_type 不进行映射"""
        mock_request_json.get.return_value = {}
        mock_request_json.set = MagicMock()
        req_json = TestN2lJsonWapper._make_req_json()
        result = _n2l_json_wapper(
            "proj1", "unknown_type", "conv1", req_json, TestN2lJsonWapper._make_mock_request()
        )
        assert "agentType" not in result

    @patch("agent_builder.nl_to_agent.nl2.request_json")
    @staticmethod
    def test_conversation_id_synced_to_context(self, mock_request_json):
        """conversationId 同步到上下文变量"""
        mock_request_json.get.return_value = {}
        mock_request_json.set = MagicMock()
        req_json = TestN2lJsonWapper._make_req_json()
        _n2l_json_wapper("proj1", "agents", "conv1", req_json, TestN2lJsonWapper._make_mock_request())
        mock_request_json.set.assert_called_once()
        set_payload = mock_request_json.set.call_args[0][0]
        assert set_payload["conversationId"] == "conv1"


class TestErrorSseGenerator:
    """_error_sse_generator COM-03 五字段契约测试（P5-BLD-01）"""

    @staticmethod
    def _set_ctx(rid="rid-test", lang="zh-cn"):
        from agent_builder.adapter.request_context_bridge import (
            RequestContext,
            _request_ctx,
        )
        return _request_ctx.set(RequestContext(headers={"x-language": lang}, request_id=rid))

    @staticmethod
    def _reset_ctx(token):
        from agent_builder.adapter.request_context_bridge import _request_ctx
        _request_ctx.reset(token)

    @staticmethod
    def _error_data(results):
        return json.loads(results[1][len("data: "):].strip())["data"]

    def test_yields_start_error_no_end(self):
        """COM-03 唯一终态：START + error,无 END"""
        token = self._set_ctx()
        try:
            results = list(_error_sse_generator(Exception("SECRET-in-msg"), "task1"))
        finally:
            self._reset_ctx(token)
        assert len(results) == 2
        assert json.loads(results[0][6:].strip())["event"] == "START"
        assert json.loads(results[1][6:].strip())["event"] == "error"

    def test_start_event_contains_task_id(self):
        """START 事件包含 conversationId"""
        token = self._set_ctx()
        try:
            results = list(_error_sse_generator(Exception("err"), "my_task"))
        finally:
            self._reset_ctx(token)
        start = json.loads(results[0][len("data: "):].strip())
        assert start["conversationId"] == "my_task"

    def test_plain_exception_five_fields_internal(self):
        """普通异常→13100004 五字段 + 原始正文不外露"""
        token = self._set_ctx()
        try:
            results = list(_error_sse_generator(ValueError("SECRET-path/token"), "task1"))
        finally:
            self._reset_ctx(token)
        data = self._error_data(results)
        assert data["error_code"] == "openjiuwen.13100004"
        for f in ("error_msg", "error_reason", "error_suggestion", "request_id"):
            assert data.get(f), f"{f} non-empty"
        assert data["request_id"] == "rid-test"
        assert "SECRET-path/token" not in json.dumps(data)

    def test_100029_maps_to_13100014_deepseek(self):
        """100029→13100014 + DeepSeek suggestion（catalog/i18n 映射）"""
        from agent_builder.adapter.exception_bridge import JiuWenBaseException
        exc = JiuWenBaseException(error_code=100029, message="Model response error: foo")
        token = self._set_ctx()
        try:
            results = list(_error_sse_generator(exc, "task1"))
        finally:
            self._reset_ctx(token)
        data = self._error_data(results)
        assert data["error_code"] == "openjiuwen.13100014"
        assert "DeepSeek-V3" in data.get("error_suggestion", "")
        assert "foo" not in json.dumps(data)  # 原始 message 不外露

    def test_unregistered_code_fail_closed(self):
        """未登记码 12345→13100004（fail-closed,不透传裸码）"""
        from agent_builder.adapter.exception_bridge import JiuWenBaseException
        exc = JiuWenBaseException(error_code=12345, message="custom error")
        token = self._set_ctx()
        try:
            results = list(_error_sse_generator(exc, "task1"))
        finally:
            self._reset_ctx(token)
        data = self._error_data(results)
        assert data["error_code"] == "openjiuwen.13100004"
        assert "12345" not in data["error_code"]
        assert "custom error" not in json.dumps(data)


class TestGeneratePreStreamFailure:
    """P5-BLD-02: 建流前失败（await coroutine/__aiter__）→ START + canonical error,
    无 UnboundLocalError 二次异常（data_task 预初始化 None + finally 条件取消）。
    """

    @staticmethod
    def _set_ctx():
        from agent_builder.adapter.request_context_bridge import (
            RequestContext,
            _request_ctx,
        )
        return _request_ctx.set(RequestContext(headers={"x-language": "zh-cn"}, request_id="rid-bld02"))

    @staticmethod
    def _reset_ctx(token):
        from agent_builder.adapter.request_context_bridge import _request_ctx
        _request_ctx.reset(token)

    @pytest.mark.asyncio
    async def test_await_coroutine_failure_no_second_exception(self):
        """await coroutine 失败 → START + canonical error,无 UnboundLocalError"""
        async def _failing_coro():
            raise RuntimeError("SECRET-await-coro-fail")
        token = self._set_ctx()
        raised, events = None, []
        try:
            async for chunk in _generate(_failing_coro(), "task-bld02"):
                events.append(chunk)
        except BaseException as e:  # noqa: BLE001
            raised = e
        finally:
            self._reset_ctx(token)
        assert raised is None, f"建流前失败不应二次异常: {raised!r}"
        assert len(events) == 2, f"期望 START+error 2 事件, got {len(events)}"
        assert b"SECRET-await-coro-fail" not in events[1], "原始正文不得外露"

    @pytest.mark.asyncio
    async def test_aiter_failure_no_second_exception(self):
        """__aiter__ 失败 → START + canonical error,无 UnboundLocalError"""
        class _FailingAiter:
            def __aiter__(self):
                raise RuntimeError("SECRET-aiter-fail")
        token = self._set_ctx()
        raised, events = None, []
        try:
            async for chunk in _generate(_FailingAiter(), "task-bld02"):
                events.append(chunk)
        except BaseException as e:  # noqa: BLE001
            raised = e
        finally:
            self._reset_ctx(token)
        assert raised is None, f"建流前失败不应二次异常: {raised!r}"
        assert len(events) == 2, f"期望 START+error 2 事件, got {len(events)}"
        assert b"SECRET-aiter-fail" not in events[1], "原始正文不得外露"


class TestAgentTypeMap:
    """AGENT_TYPE_MAP 常量测试"""

    @staticmethod
    def test_agents_maps_to_llm_agent():
        """agents 映射为 llm_agent"""
        assert AGENT_TYPE_MAP["agents"] == "llm_agent"

    @staticmethod
    def test_workflows_maps_to_workflow():
        """workflows 映射为 workflow"""
        assert AGENT_TYPE_MAP["workflows"] == "workflow"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])