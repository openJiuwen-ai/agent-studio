# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Tests for web_run.py — web workflow/agent run endpoints."""

import sys
from unittest.mock import AsyncMock, MagicMock, patch

# Stub agent_builder modules to avoid import errors (same pattern as test_app_run.py)
if "agent_builder.app" not in sys.modules:
    from flask import Flask

    stub_mod = MagicMock()
    stub_mod.app = Flask(__name__)
    sys.modules["agent_builder.app"] = stub_mod

if "agent_builder.nl_to_agent.nl2" not in sys.modules:
    stub_nl2 = MagicMock()
    sys.modules["agent_builder.nl_to_agent.nl2"] = stub_nl2
    stub_nl_to_agent = MagicMock()
    stub_nl_to_agent.nl2 = stub_nl2
    sys.modules["agent_builder.nl_to_agent"] = stub_nl_to_agent

import pytest
from fastapi import Request
from fastapi.responses import JSONResponse, StreamingResponse

from agent_runtime.serve.apis.app_release import ReleaseInfo
from agent_runtime.serve.apis.app_run_request import (
    WorkflowAppRunRequest,
    AgentAppRunRequest,
)
from agent_runtime.serve.apis.web_run import run_web_workflow, run_web_agent


def _make_request(path_params: dict, language: str = "zh-cn") -> MagicMock:
    """Build a FastAPI Request mock with given path_params and headers."""
    request = MagicMock(spec=Request)
    request.path_params = path_params
    request.headers = {"x-language": language}
    return request


def _make_release_info(
    app_id: str = "wf-001",
    version_id: str = "v1",
    project_id: str = "proj-1",
    app_type: str = "workflow",
) -> ReleaseInfo:
    return ReleaseInfo(
        app_id=app_id,
        app_type=app_type,
        version_id=version_id,
        project_id=project_id,
        short_code="abc123",
    )


class TestRunWebWorkflow:
    """POST /v1/workflows/chat/{short_code}/conversations/{conversation_id} tests."""

    @pytest.mark.asyncio
    async def test_success(self):
        """正常执行：查询 ReleaseInfo 后复用 _execute_workflow_run."""
        release_info = _make_release_info()
        expected_response = StreamingResponse(iter([b"data"]))
        body = WorkflowAppRunRequest(inputs={"query": "hello"})
        request = _make_request(
            {"short_code": "abc123", "conversation_id": "conv-1"}
        )

        with (
            patch(
                "agent_runtime.serve.apis.web_run._release_service"
            ) as mock_service,
            patch(
                "agent_runtime.serve.apis.web_run._execute_workflow_run",
                new_callable=AsyncMock,
                return_value=expected_response,
            ) as mock_exec,
        ):
            mock_service.get_release_info = AsyncMock(return_value=release_info)
            result = await run_web_workflow(body=body, request=request)

        assert result is expected_response
        mock_service.get_release_info.assert_awaited_once_with("abc123", "zh-cn")
        mock_exec.assert_awaited_once()
        # Verify WorkflowRunContext passed to _execute_workflow_run
        call_args = mock_exec.await_args
        ctx = call_args.args[0]
        assert ctx.project_id == "proj-1"
        assert ctx.workflow_id == "wf-001"
        assert ctx.conversation_id == "conv-1"
        assert ctx.version == "v1"

    @pytest.mark.asyncio
    async def test_release_info_not_found_returns_error(self):
        """ReleaseInfo 查询返回 JSONResponse 错误时直接透传."""
        error_response = JSONResponse(status_code=404, content={"error": "not found"})
        body = WorkflowAppRunRequest()
        request = _make_request(
            {"short_code": "missing", "conversation_id": "conv-1"}
        )

        with patch(
            "agent_runtime.serve.apis.web_run._release_service"
        ) as mock_service:
            mock_service.get_release_info = AsyncMock(return_value=error_response)
            result = await run_web_workflow(body=body, request=request)

        assert result is error_response
        mock_service.get_release_info.assert_awaited_once_with("missing", "zh-cn")

    @pytest.mark.asyncio
    async def test_release_info_500_error_passthrough(self):
        """ReleaseInfo 查询返回 500 错误时直接透传."""
        error_response = JSONResponse(status_code=500, content={"error": "redis down"})
        body = WorkflowAppRunRequest()
        request = _make_request(
            {"short_code": "abc123", "conversation_id": "conv-1"}
        )

        with patch(
            "agent_runtime.serve.apis.web_run._release_service"
        ) as mock_service:
            mock_service.get_release_info = AsyncMock(return_value=error_response)
            result = await run_web_workflow(body=body, request=request)

        assert result is error_response

    @pytest.mark.asyncio
    async def test_version_none_when_release_info_version_empty(self):
        """version_id 为空时 WorkflowRunContext.version 为 None."""
        release_info = _make_release_info(version_id="")
        expected_response = JSONResponse(content={})
        body = WorkflowAppRunRequest()
        request = _make_request(
            {"short_code": "abc123", "conversation_id": "conv-1"}
        )

        with (
            patch(
                "agent_runtime.serve.apis.web_run._release_service"
            ) as mock_service,
            patch(
                "agent_runtime.serve.apis.web_run._execute_workflow_run",
                new_callable=AsyncMock,
                return_value=expected_response,
            ) as mock_exec,
        ):
            mock_service.get_release_info = AsyncMock(return_value=release_info)
            await run_web_workflow(body=body, request=request)

        ctx = mock_exec.await_args.args[0]
        assert ctx.version is None

    @pytest.mark.asyncio
    async def test_language_from_header_default(self):
        """未传 x-language 时默认 zh-cn."""
        release_info = _make_release_info()
        expected_response = JSONResponse(content={})
        body = WorkflowAppRunRequest()
        request = MagicMock(spec=Request)
        request.path_params = {"short_code": "abc123", "conversation_id": "conv-1"}
        request.headers = {}  # No x-language header

        with (
            patch(
                "agent_runtime.serve.apis.web_run._release_service"
            ) as mock_service,
            patch(
                "agent_runtime.serve.apis.web_run._execute_workflow_run",
                new_callable=AsyncMock,
                return_value=expected_response,
            ),
        ):
            mock_service.get_release_info = AsyncMock(return_value=release_info)
            await run_web_workflow(body=body, request=request)

        # Default language zh-cn passed to get_release_info
        mock_service.get_release_info.assert_awaited_once_with("abc123", "zh-cn")

    @pytest.mark.asyncio
    async def test_language_from_header_en_us(self):
        """x-language=en-us 时传递给 get_release_info."""
        release_info = _make_release_info()
        expected_response = JSONResponse(content={})
        body = WorkflowAppRunRequest()
        request = _make_request(
            {"short_code": "abc123", "conversation_id": "conv-1"},
            language="en-us",
        )

        with (
            patch(
                "agent_runtime.serve.apis.web_run._release_service"
            ) as mock_service,
            patch(
                "agent_runtime.serve.apis.web_run._execute_workflow_run",
                new_callable=AsyncMock,
                return_value=expected_response,
            ),
        ):
            mock_service.get_release_info = AsyncMock(return_value=release_info)
            await run_web_workflow(body=body, request=request)

        mock_service.get_release_info.assert_awaited_once_with("abc123", "en-us")


class TestRunWebAgent:
    """POST /v1/agents/chat/{short_code} tests."""

    @pytest.mark.asyncio
    async def test_success(self):
        """正常执行：查询 ReleaseInfo 后复用 _execute_agent_run."""
        release_info = _make_release_info(app_id="agent-001", app_type="agent")
        expected_response = StreamingResponse(iter([b"data"]))
        body = AgentAppRunRequest(query="hello")
        request = _make_request({"short_code": "abc123"})

        with (
            patch(
                "agent_runtime.serve.apis.web_run._release_service"
            ) as mock_service,
            patch(
                "agent_runtime.serve.apis.web_run._execute_agent_run",
                new_callable=AsyncMock,
                return_value=expected_response,
            ) as mock_exec,
        ):
            mock_service.get_release_info = AsyncMock(return_value=release_info)
            result = await run_web_agent(
                body=body,
                request=request,
                workspace_id="ws-1",
                conversation_id="conv-1",
            )

        assert result is expected_response
        mock_service.get_release_info.assert_awaited_once_with("abc123", "zh-cn")
        mock_exec.assert_awaited_once()
        ctx = mock_exec.await_args.args[0]
        assert ctx.project_id == "proj-1"
        assert ctx.agent_id == "agent-001"
        assert ctx.conversation_id == "conv-1"
        assert ctx.version == "v1"

    @pytest.mark.asyncio
    async def test_release_info_not_found_returns_error(self):
        """ReleaseInfo 查询返回 JSONResponse 错误时直接透传."""
        error_response = JSONResponse(status_code=404, content={"error": "not found"})
        body = AgentAppRunRequest()
        request = _make_request({"short_code": "missing"})

        with patch(
            "agent_runtime.serve.apis.web_run._release_service"
        ) as mock_service:
            mock_service.get_release_info = AsyncMock(return_value=error_response)
            result = await run_web_agent(
                body=body,
                request=request,
                workspace_id="",
                conversation_id="conv-1",
            )

        assert result is error_response

    @pytest.mark.asyncio
    async def test_conversation_id_generated_when_empty(self):
        """conversation_id 为空时自动生成 UUID."""
        release_info = _make_release_info(app_id="agent-001")
        expected_response = JSONResponse(content={})
        body = AgentAppRunRequest()
        request = _make_request({"short_code": "abc123"})

        with (
            patch(
                "agent_runtime.serve.apis.web_run._release_service"
            ) as mock_service,
            patch(
                "agent_runtime.serve.apis.web_run._execute_agent_run",
                new_callable=AsyncMock,
                return_value=expected_response,
            ) as mock_exec,
        ):
            mock_service.get_release_info = AsyncMock(return_value=release_info)
            await run_web_agent(
                body=body,
                request=request,
                workspace_id="",
                conversation_id="",  # Empty → should generate UUID
            )

        ctx = mock_exec.await_args.args[0]
        # conversation_id should be a non-empty UUID-like string
        assert ctx.conversation_id
        assert len(ctx.conversation_id) == 36  # UUID4 string length

    @pytest.mark.asyncio
    async def test_conversation_id_preserved_when_provided(self):
        """conversation_id 非空时保留原值."""
        release_info = _make_release_info(app_id="agent-001")
        expected_response = JSONResponse(content={})
        body = AgentAppRunRequest()
        request = _make_request({"short_code": "abc123"})

        with (
            patch(
                "agent_runtime.serve.apis.web_run._release_service"
            ) as mock_service,
            patch(
                "agent_runtime.serve.apis.web_run._execute_agent_run",
                new_callable=AsyncMock,
                return_value=expected_response,
            ) as mock_exec,
        ):
            mock_service.get_release_info = AsyncMock(return_value=release_info)
            await run_web_agent(
                body=body,
                request=request,
                workspace_id="",
                conversation_id="existing-conv-id",
            )

        ctx = mock_exec.await_args.args[0]
        assert ctx.conversation_id == "existing-conv-id"

    @pytest.mark.asyncio
    async def test_version_none_when_release_info_version_empty(self):
        """version_id 为空时 AgentRunContext.version 为 None."""
        release_info = _make_release_info(app_id="agent-001", version_id="")
        expected_response = JSONResponse(content={})
        body = AgentAppRunRequest()
        request = _make_request({"short_code": "abc123"})

        with (
            patch(
                "agent_runtime.serve.apis.web_run._release_service"
            ) as mock_service,
            patch(
                "agent_runtime.serve.apis.web_run._execute_agent_run",
                new_callable=AsyncMock,
                return_value=expected_response,
            ) as mock_exec,
        ):
            mock_service.get_release_info = AsyncMock(return_value=release_info)
            await run_web_agent(
                body=body,
                request=request,
                workspace_id="",
                conversation_id="conv-1",
            )

        ctx = mock_exec.await_args.args[0]
        assert ctx.version is None
