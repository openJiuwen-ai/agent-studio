# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Tests for app_run.py — trial run API endpoints."""

import asyncio
import sys
from typing import Optional, Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch

from pydantic import BaseModel

# Stub agent_builder modules to avoid import errors
if "agent_builder.app" not in sys.modules:
    from flask import Flask
    stub_mod = MagicMock()
    stub_mod.app = Flask(__name__)
    sys.modules["agent_builder.app"] = stub_mod

if "agent_builder.nl_to_agent.nl2" not in sys.modules:

    class _StubN2LResource(BaseModel):
        plugins: Optional[Dict[str, Any]] = None
        workflows: Optional[Dict[str, Any]] = None
        knowledge_base: Optional[Dict[str, Any]] = None

    class _StubN2LModel(BaseModel):
        modelName: Optional[str] = None
        modelExplicitName: Optional[str] = None
        extension: Optional[Dict[str, Any]] = None
        modelType: Optional[str] = None
        modelInterfaceProtocol: Optional[str] = None

    class _StubN2LRequestBody(BaseModel):
        query: str
        model: Optional[_StubN2LModel] = None
        resource: Optional[_StubN2LResource] = None
        conversationId: Optional[str] = None

    stub_nl2 = MagicMock()
    stub_nl2.N2LRequestBody = _StubN2LRequestBody
    stub_nl2.n2l_json_wapper = MagicMock()
    stub_nl2.chat = MagicMock()
    sys.modules["agent_builder.nl_to_agent.nl2"] = stub_nl2
    stub_nl_to_agent = MagicMock()
    stub_nl_to_agent.nl2 = stub_nl2
    sys.modules["agent_builder.nl_to_agent"] = stub_nl_to_agent

import pytest
from fastapi import Request
from fastapi.responses import StreamingResponse, JSONResponse

from agent_runtime.serve.apis.app_run import (
    build_workflow_ir_path,
    build_agent_ir_path,
    build_req_json_from_workflow,
    build_req_json_from_agent,
    _resolve_handler_type,
    _extract_instance_id,
    _encapsulate_response,
)
from agent_runtime.serve.apis.app_run_request import (
    WorkflowAppRunRequest,
    AgentAppRunRequest,
    ExecutionContext,
)


class TestBuildIRPath:
    """IR path builder tests."""

    @staticmethod
    def test_workflow_ir_path_with_version():
        path = build_workflow_ir_path("wf-123", "v1")
        assert path == "workflow/ir/wf-123/wf-123_v1.json"

    @staticmethod
    def test_workflow_ir_path_without_version():
        path = build_workflow_ir_path("wf-123", None)
        assert path == "workflow/ir/wf-123/wf-123.json"

    @staticmethod
    def test_workflow_ir_path_custom_prefix(monkeypatch):
        monkeypatch.setenv("WORKFLOW_IR_OBS_PATH", "custom/path")
        path = build_workflow_ir_path("wf-456", "v2")
        assert path == "custom/path/wf-456/wf-456_v2.json"

    @staticmethod
    def test_agent_ir_path_with_version():
        path = build_agent_ir_path("agent-789", "v3")
        assert path == "agent/ir/agent-789/agent-789_v3.json"

    @staticmethod
    def test_agent_ir_path_without_version():
        path = build_agent_ir_path("agent-789", None)
        assert path == "agent/ir/agent-789/agent-789.json"

    @staticmethod
    def test_agent_ir_path_custom_prefix(monkeypatch):
        monkeypatch.setenv("AGENT_IR_OBS_PATH", "my/agents")
        path = build_agent_ir_path("a1", None)
        assert path == "my/agents/a1/a1.json"


class TestBuildReqJsonFromWorkflow:
    """Workflow request builder tests."""

    @staticmethod
    def _make_ctx(**overrides):
        defaults = dict(
            conversation_id="conv-1", ir_path="ir/path",
            conversation_history=[], dialogue_count=1, user_id="anonymous",
        )
        defaults.update(overrides)
        return ExecutionContext(**defaults)

    @staticmethod
    def test_query_from_inputs():
        body = WorkflowAppRunRequest(inputs={"query": "hello"})
        result = build_req_json_from_workflow(body, TestBuildReqJsonFromWorkflow._make_ctx())
        assert result["query"] == "hello"

    @staticmethod
    def test_query_empty_when_not_in_inputs():
        body = WorkflowAppRunRequest(inputs={})
        result = build_req_json_from_workflow(body, TestBuildReqJsonFromWorkflow._make_ctx())
        assert result["query"] == ""

    @staticmethod
    def test_conversation_history_from_ctx():
        body = WorkflowAppRunRequest()
        ctx = TestBuildReqJsonFromWorkflow._make_ctx(
            conversation_history=[{"role": "user", "content": "hi"}],
            dialogue_count=5,
        )
        result = build_req_json_from_workflow(body, ctx)
        assert len(result["params"]["conversationHistory"]) == 1
        assert result["params"]["conversationHistory"][0]["role"] == "user"

    @staticmethod
    def test_empty_body_messages_use_history():
        body = WorkflowAppRunRequest()
        history = [{"role": "user", "content": "cached"}]
        ctx = TestBuildReqJsonFromWorkflow._make_ctx(conversation_history=history, dialogue_count=3)
        result = build_req_json_from_workflow(body, ctx)
        assert result["params"]["conversationHistory"] == history
        assert result["dialogueCount"] == 3

    @staticmethod
    def test_memory_inputs_merged_into_globals():
        body = WorkflowAppRunRequest(
            globals={"key1": "val1"},
            memory_inputs={"key2": "val2"},
        )
        result = build_req_json_from_workflow(body, TestBuildReqJsonFromWorkflow._make_ctx())
        assert result["params"]["globalVariables"]["key1"] == "val1"
        assert result["params"]["globalVariables"]["key2"] == "val2"

    @staticmethod
    def test_user_id_defaults_to_anonymous():
        body = WorkflowAppRunRequest()
        result = build_req_json_from_workflow(body, TestBuildReqJsonFromWorkflow._make_ctx())
        assert result["userId"] == "anonymous"

    @staticmethod
    def test_response_mode_always_streaming():
        body = WorkflowAppRunRequest()
        result = build_req_json_from_workflow(body, TestBuildReqJsonFromWorkflow._make_ctx())
        assert result["responseMode"] == "streaming"


class TestBuildReqJsonFromAgent:
    """Agent request builder tests."""

    @staticmethod
    def _make_ctx(**overrides):
        defaults = dict(
            conversation_id="conv-1", ir_path="ir/path",
            conversation_history=[], dialogue_count=1, user_id="",
        )
        defaults.update(overrides)
        return ExecutionContext(**defaults)

    @staticmethod
    def test_query_from_body():
        body = AgentAppRunRequest(query="test query")
        result = build_req_json_from_agent(body, TestBuildReqJsonFromAgent._make_ctx())
        assert result["query"] == "test query"

    @staticmethod
    def test_query_fallback_to_inputs():
        body = AgentAppRunRequest(inputs={"query": "from inputs"})
        result = build_req_json_from_agent(body, TestBuildReqJsonFromAgent._make_ctx())
        assert result["query"] == "from inputs"

    @staticmethod
    def test_query_body_takes_priority():
        body = AgentAppRunRequest(query="body query", inputs={"query": "inputs query"})
        result = build_req_json_from_agent(body, TestBuildReqJsonFromAgent._make_ctx())
        assert result["query"] == "body query"

    @staticmethod
    def test_query_empty_when_missing():
        body = AgentAppRunRequest()
        result = build_req_json_from_agent(body, TestBuildReqJsonFromAgent._make_ctx())
        assert result["query"] == ""

    @staticmethod
    def test_conversation_history_from_ctx():
        body = AgentAppRunRequest()
        ctx = TestBuildReqJsonFromAgent._make_ctx(
            conversation_history=[{"role": "user", "content": "new"}],
            dialogue_count=5,
        )
        result = build_req_json_from_agent(body, ctx)
        assert len(result["params"]["conversationHistory"]) == 1
        assert result["params"]["conversationHistory"][0]["role"] == "user"

    @staticmethod
    def test_empty_histories_use_redis():
        body = AgentAppRunRequest()
        history = [{"role": "user", "content": "redis"}]
        ctx = TestBuildReqJsonFromAgent._make_ctx(conversation_history=history, dialogue_count=2)
        result = build_req_json_from_agent(body, ctx)
        assert result["params"]["conversationHistory"] == history

    @staticmethod
    def test_user_id_defaults_to_empty():
        body = AgentAppRunRequest()
        result = build_req_json_from_agent(body, TestBuildReqJsonFromAgent._make_ctx())
        assert result["userId"] == ""


class TestResolveHandlerType:
    """Handler type resolver tests."""

    @pytest.mark.asyncio
    async def test_workflow_mode(self):
        with patch("agent_runtime.serve.apis.app_run.async_ir_load") as mock_load:
            mock_load.return_value = {"configs": {"mode": "workflow"}}
            result = await _resolve_handler_type("ir/path.json")
            assert result == "workflow"

    @pytest.mark.asyncio
    async def test_react_mode(self):
        with patch("agent_runtime.serve.apis.app_run.async_ir_load") as mock_load:
            mock_load.return_value = {"configs": {"mode": "react"}}
            result = await _resolve_handler_type("ir/path.json")
            assert result == "ReAct"

    @pytest.mark.asyncio
    async def test_controller_mode(self):
        with patch("agent_runtime.serve.apis.app_run.async_ir_load") as mock_load:
            mock_load.return_value = {"configs": {"mode": "controller"}}
            result = await _resolve_handler_type("ir/path.json")
            assert result == "Controller"

    @pytest.mark.asyncio
    async def test_planexecute_mode(self):
        with patch("agent_runtime.serve.apis.app_run.async_ir_load") as mock_load:
            mock_load.return_value = {"configs": {"mode": "PlanExecute"}}
            result = await _resolve_handler_type("ir/path.json")
            assert result == "PlanExecute"

    @pytest.mark.asyncio
    async def test_missing_configs_defaults_to_workflow(self):
        with patch("agent_runtime.serve.apis.app_run.async_ir_load") as mock_load:
            mock_load.return_value = {}
            result = await _resolve_handler_type("ir/path.json")
            assert result == "workflow"

    @pytest.mark.asyncio
    async def test_unknown_mode_defaults_to_workflow(self):
        with patch("agent_runtime.serve.apis.app_run.async_ir_load") as mock_load:
            mock_load.return_value = {"configs": {"mode": "unknown"}}
            result = await _resolve_handler_type("ir/path.json")
            assert result == "workflow"


class TestExtractInstanceId:
    """Instance ID extractor tests."""

    @staticmethod
    def test_extract_from_path_with_extension():
        result = _extract_instance_id("workflow/ir/wf-123/wf-123_v1.json")
        assert result == "wf-123_v1"

    @staticmethod
    def test_extract_from_path_without_extension():
        result = _extract_instance_id("path/to/instance")
        assert result == "instance"

    @staticmethod
    def test_extract_from_filename_only():
        result = _extract_instance_id("file.json")
        assert result == "file"


class TestEncapsulateResponse:
    """Response encapsulator tests."""

    @staticmethod
    @pytest.mark.asyncio
    async def test_json_response_passthrough():
        json_resp = JSONResponse(content={"key": "value"})
        request = MagicMock(spec=Request)
        result = await _encapsulate_response(
            json_resp, "Workflow", request, "ir/path.json"
        )
        assert result is json_resp

    @staticmethod
    @pytest.mark.asyncio
    async def test_stream_true_calls_stream_handler():
        mock_stream = MagicMock(spec=StreamingResponse)
        mock_stream.body_iterator = AsyncMock()
        request = MagicMock(spec=Request)
        request.path_params = {"conversation_id": "conv-1"}
        request.state = MagicMock(user_id="user-1", version_id="v1")
        request.headers = {"x-invoke-mode": "normal", "x-language": "en-us"}

        with patch(
            "agent_runtime.serve.apis.app_run.EventHandler.encapsulate_stream_response",
            new_callable=AsyncMock,
        ) as mock_handler:
            mock_handler.return_value = mock_stream
            result = await _encapsulate_response(
                mock_stream, "Workflow", request, "ir/path.json", stream=True
            )
            mock_handler.assert_awaited_once()
            assert result is mock_stream

    @staticmethod
    @pytest.mark.asyncio
    async def test_stream_false_calls_non_stream_handler():
        mock_stream = MagicMock(spec=StreamingResponse)
        mock_stream.body_iterator = AsyncMock()
        request = MagicMock(spec=Request)
        request.path_params = {"conversation_id": "conv-1"}
        request.state = MagicMock(user_id="user-1", version_id="v1")
        request.headers = {"x-invoke-mode": "normal", "x-language": "en-us"}

        with patch(
            "agent_runtime.serve.apis.app_run.EventHandler.encapsulate_non_stream_response",
            new_callable=AsyncMock,
        ) as mock_handler:
            mock_handler.return_value = JSONResponse(content={})
            result = await _encapsulate_response(
                mock_stream, "Workflow", request, "ir/path.json", stream=False
            )
            mock_handler.assert_awaited_once()
