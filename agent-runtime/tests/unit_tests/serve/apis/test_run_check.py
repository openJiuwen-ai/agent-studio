# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Tests for run_check.py — checkBeforeRun logic."""

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

from agent_runtime.serve.apis.run_check import (
    RunCheckContext,
    check_query_length,
    check_chat_workflow_query,
    check_project_permission,
    check_version_freshness,
    check_before_workflow_run,
    check_before_agent_run,
    _MAX_QUERY_LENGTH,
    _CODE_METHOD_ARGUMENT,
    _CODE_WORKFLOW_PERMISSION,
    _CODE_AGENT_PERMISSION,
    _CODE_NOT_LATEST,
)


class TestCheckQueryLength:
    """校验1: Query长度."""

    @staticmethod
    @pytest.mark.asyncio
    async def test_short_query_passes():
        result = await check_query_length("hello")
        assert result is None

    @staticmethod
    @pytest.mark.asyncio
    async def test_none_query_passes():
        result = await check_query_length(None)
        assert result is None

    @staticmethod
    @pytest.mark.asyncio
    async def test_empty_query_passes():
        result = await check_query_length("")
        assert result is None

    @staticmethod
    @pytest.mark.asyncio
    async def test_exceed_max_length_rejected():
        long_query = "a" * (_MAX_QUERY_LENGTH + 1)
        result = await check_query_length(long_query)
        assert result is not None
        assert result.status_code == 400
        body = result.body.decode()
        assert _CODE_METHOD_ARGUMENT in body

    @staticmethod
    @pytest.mark.asyncio
    async def test_exact_max_length_passes():
        query = "a" * _MAX_QUERY_LENGTH
        result = await check_query_length(query)
        assert result is None


class TestCheckChatWorkflowQuery:
    """校验2: Chat工作流query必填."""

    @staticmethod
    @pytest.mark.asyncio
    async def test_chat_with_query_passes():
        with patch(
            "agent_runtime.serve.apis.orchestration.async_ir_load",
            new_callable=AsyncMock,
        ) as mock_load:
            mock_load.return_value = {"metadata": {"type": "chat"}}
            result = await check_chat_workflow_query("hello", "ir/path.json")
            assert result is None

    @staticmethod
    @pytest.mark.asyncio
    async def test_chat_with_empty_query_rejected():
        with patch(
            "agent_runtime.serve.apis.orchestration.async_ir_load",
            new_callable=AsyncMock,
        ) as mock_load:
            mock_load.return_value = {"metadata": {"type": "chat"}}
            result = await check_chat_workflow_query("", "ir/path.json")
            assert result is not None
            assert result.status_code == 400
            assert _CODE_METHOD_ARGUMENT in result.body.decode()

    @staticmethod
    @pytest.mark.asyncio
    async def test_chat_with_none_query_rejected():
        with patch(
            "agent_runtime.serve.apis.orchestration.async_ir_load",
            new_callable=AsyncMock,
        ) as mock_load:
            mock_load.return_value = {"metadata": {"type": "chat"}}
            result = await check_chat_workflow_query(None, "ir/path.json")
            assert result is not None
            assert result.status_code == 400

    @staticmethod
    @pytest.mark.asyncio
    async def test_task_type_with_empty_query_passes():
        with patch(
            "agent_runtime.serve.apis.orchestration.async_ir_load",
            new_callable=AsyncMock,
        ) as mock_load:
            mock_load.return_value = {"metadata": {"type": "task"}}
            result = await check_chat_workflow_query("", "ir/path.json")
            assert result is None

    @staticmethod
    @pytest.mark.asyncio
    async def test_node_execute_skips_check():
        result = await check_chat_workflow_query(
            "", "ir/path.json", is_node_execute=True
        )
        assert result is None


class TestCheckProjectPermission:
    """校验3: 项目权限."""

    @staticmethod
    @pytest.mark.asyncio
    async def test_matching_project_passes():
        with patch(
            "agent_runtime.serve.apis.orchestration.async_ir_load",
            new_callable=AsyncMock,
        ) as mock_load:
            mock_load.return_value = {"metadata": {"projectId": "proj-1"}}
            result = await check_project_permission("proj-1", "ir/path.json")
            assert result is None

    @staticmethod
    @pytest.mark.asyncio
    async def test_mismatching_project_rejected():
        with patch(
            "agent_runtime.serve.apis.orchestration.async_ir_load",
            new_callable=AsyncMock,
        ) as mock_load:
            mock_load.return_value = {"metadata": {"projectId": "proj-1"}}
            result = await check_project_permission("proj-2", "ir/path.json")
            assert result is not None
            assert result.status_code == 403
            body = result.body.decode()
            assert _CODE_WORKFLOW_PERMISSION in body

    @staticmethod
    @pytest.mark.asyncio
    async def test_agent_mismatch_uses_agent_error_code():
        with patch(
            "agent_runtime.serve.apis.orchestration.async_ir_load",
            new_callable=AsyncMock,
        ) as mock_load:
            mock_load.return_value = {"metadata": {"projectId": "proj-1"}}
            result = await check_project_permission(
                "proj-2", "ir/path.json", is_agent=True
            )
            assert result is not None
            body = result.body.decode()
            assert _CODE_AGENT_PERMISSION in body


class TestCheckVersionFreshness:
    """校验4: 版本新鲜度."""

    @staticmethod
    @pytest.mark.asyncio
    async def test_none_body_version_skips():
        result = await check_version_freshness(None, "ir/path.json")
        assert result is None

    @staticmethod
    @pytest.mark.asyncio
    async def test_matching_version_passes():
        with patch(
            "agent_runtime.serve.apis.orchestration.async_ir_load",
            new_callable=AsyncMock,
        ) as mock_load:
            mock_load.return_value = {"metadata": {"updatedAt": 1781166449466}}
            result = await check_version_freshness(1781166449466, "ir/path.json")
            assert result is None

    @staticmethod
    @pytest.mark.asyncio
    async def test_mismatching_version_rejected():
        with patch(
            "agent_runtime.serve.apis.orchestration.async_ir_load",
            new_callable=AsyncMock,
        ) as mock_load:
            mock_load.return_value = {"metadata": {"updatedAt": 1781166449466}}
            result = await check_version_freshness(1781166449000, "ir/path.json")
            assert result is not None
            assert result.status_code == 403
            body = result.body.decode()
            assert _CODE_NOT_LATEST in body

    @staticmethod
    @pytest.mark.asyncio
    async def test_string_updated_at_comparison():
        """Agent IR中updatedAt为string类型."""
        with patch(
            "agent_runtime.serve.apis.orchestration.async_ir_load",
            new_callable=AsyncMock,
        ) as mock_load:
            mock_load.return_value = {"metadata": {"updatedAt": "1753068651707"}}
            result = await check_version_freshness("1753068651707", "ir/path.json")
            assert result is None

    @staticmethod
    @pytest.mark.asyncio
    async def test_int_body_vs_string_ir():
        """body.version为int，IR updatedAt为string，值相同应通过."""
        with patch(
            "agent_runtime.serve.apis.orchestration.async_ir_load",
            new_callable=AsyncMock,
        ) as mock_load:
            mock_load.return_value = {"metadata": {"updatedAt": "1753068651707"}}
            result = await check_version_freshness(1753068651707, "ir/path.json")
            assert result is None

    @staticmethod
    @pytest.mark.asyncio
    async def test_no_updated_at_in_metadata():
        with patch(
            "agent_runtime.serve.apis.orchestration.async_ir_load",
            new_callable=AsyncMock,
        ) as mock_load:
            mock_load.return_value = {"metadata": {}}
            result = await check_version_freshness(12345, "ir/path.json")
            assert result is None


class TestCheckBeforeWorkflowRun:
    """工作流综合校验 — 合并IR加载."""

    @staticmethod
    @pytest.mark.asyncio
    async def test_all_checks_pass():
        with patch(
            "agent_runtime.serve.apis.orchestration.async_ir_load",
            new_callable=AsyncMock,
        ) as mock_load:
            mock_load.return_value = {
                "metadata": {"type": "task", "projectId": "proj-1", "updatedAt": 1000}
            }
            result = await check_before_workflow_run(RunCheckContext(
                query="hello",
                project_id="proj-1",
                ir_path="ir/path.json",
                body_version=1000,
                has_published_version=False,
            ))
            assert result is None

    @staticmethod
    @pytest.mark.asyncio
    async def test_query_length_rejected_before_ir_load():
        """query长度校验在IR加载之前，不需要mock."""
        long_query = "a" * (_MAX_QUERY_LENGTH + 1)
        result = await check_before_workflow_run(RunCheckContext(
            query=long_query,
            project_id="proj-1",
            ir_path="ir/path.json",
            body_version=None,
            has_published_version=False,
        ))
        assert result is not None
        assert result.status_code == 400

    @staticmethod
    @pytest.mark.asyncio
    async def test_chat_empty_query_rejected():
        with patch(
            "agent_runtime.serve.apis.orchestration.async_ir_load",
            new_callable=AsyncMock,
        ) as mock_load:
            mock_load.return_value = {
                "metadata": {"type": "chat", "projectId": "proj-1"}
            }
            result = await check_before_workflow_run(RunCheckContext(
                query="",
                project_id="proj-1",
                ir_path="ir/path.json",
                body_version=None,
                has_published_version=False,
            ))
            assert result is not None
            assert result.status_code == 400

    @staticmethod
    @pytest.mark.asyncio
    async def test_project_permission_rejected():
        with patch(
            "agent_runtime.serve.apis.orchestration.async_ir_load",
            new_callable=AsyncMock,
        ) as mock_load:
            mock_load.return_value = {
                "metadata": {"type": "task", "projectId": "proj-1"}
            }
            result = await check_before_workflow_run(RunCheckContext(
                query="hello",
                project_id="proj-2",
                ir_path="ir/path.json",
                body_version=None,
                has_published_version=False,
            ))
            assert result is not None
            assert result.status_code == 403

    @staticmethod
    @pytest.mark.asyncio
    async def test_version_freshness_rejected():
        with patch(
            "agent_runtime.serve.apis.orchestration.async_ir_load",
            new_callable=AsyncMock,
        ) as mock_load:
            mock_load.return_value = {
                "metadata": {
                    "type": "task",
                    "projectId": "proj-1",
                    "updatedAt": 2000,
                }
            }
            result = await check_before_workflow_run(RunCheckContext(
                query="hello",
                project_id="proj-1",
                ir_path="ir/path.json",
                body_version=1000,
                has_published_version=False,
            ))
            assert result is not None
            assert result.status_code == 403

    @staticmethod
    @pytest.mark.asyncio
    async def test_published_version_skips_freshness():
        """已发布版本(has_published_version=True)跳过新鲜度校验."""
        with patch(
            "agent_runtime.serve.apis.orchestration.async_ir_load",
            new_callable=AsyncMock,
        ) as mock_load:
            mock_load.return_value = {
                "metadata": {
                    "type": "task",
                    "projectId": "proj-1",
                    "updatedAt": 2000,
                }
            }
            result = await check_before_workflow_run(RunCheckContext(
                query="hello",
                project_id="proj-1",
                ir_path="ir/path.json",
                body_version=1000,
                has_published_version=True,
            ))
            assert result is None

    @staticmethod
    @pytest.mark.asyncio
    async def test_node_execute_skips_chat_check():
        with patch(
            "agent_runtime.serve.apis.orchestration.async_ir_load",
            new_callable=AsyncMock,
        ) as mock_load:
            mock_load.return_value = {
                "metadata": {"type": "chat", "projectId": "proj-1"}
            }
            result = await check_before_workflow_run(RunCheckContext(
                query="",
                project_id="proj-1",
                ir_path="ir/path.json",
                body_version=None,
                has_published_version=False,
                is_node_execute=True,
            ))
            assert result is None

    @staticmethod
    @pytest.mark.asyncio
    async def test_i18n_response_contains_error_fields():
        """错误响应包含error_code/error_msg/error_reason/error_suggestion."""
        with patch(
            "agent_runtime.serve.apis.orchestration.async_ir_load",
            new_callable=AsyncMock,
        ) as mock_load:
            mock_load.return_value = {
                "metadata": {"type": "task", "projectId": "proj-1", "updatedAt": 2000}
            }
            result = await check_before_workflow_run(RunCheckContext(
                query="hello",
                project_id="proj-1",
                ir_path="ir/path.json",
                body_version=1000,
                has_published_version=False,
            ))
            assert result is not None
            import json
            body = json.loads(result.body.decode())
            assert "error_code" in body
            assert "error_msg" in body
            assert "error_reason" in body
            assert "error_suggestion" in body
            assert body["error_code"] == f"openjiuwen.{_CODE_NOT_LATEST}"


class TestCheckBeforeAgentRun:
    """智能体综合校验."""

    @staticmethod
    @pytest.mark.asyncio
    async def test_all_checks_pass():
        with patch(
            "agent_runtime.serve.apis.orchestration.async_ir_load",
            new_callable=AsyncMock,
        ) as mock_load:
            mock_load.return_value = {
                "metadata": {"projectId": "proj-1", "updatedAt": "1000"}
            }
            result = await check_before_agent_run(RunCheckContext(
                query="hello",
                project_id="proj-1",
                ir_path="ir/path.json",
                body_version="1000",
                has_published_version=False,
            ))
            assert result is None

    @staticmethod
    @pytest.mark.asyncio
    async def test_project_permission_uses_agent_code():
        with patch(
            "agent_runtime.serve.apis.orchestration.async_ir_load",
            new_callable=AsyncMock,
        ) as mock_load:
            mock_load.return_value = {"metadata": {"projectId": "proj-1"}}
            result = await check_before_agent_run(RunCheckContext(
                query="hello",
                project_id="proj-2",
                ir_path="ir/path.json",
                body_version=None,
                has_published_version=False,
            ))
            assert result is not None
            body = result.body.decode()
            assert _CODE_AGENT_PERMISSION in body

    @staticmethod
    @pytest.mark.asyncio
    async def test_version_freshness_with_string_updated_at():
        with patch(
            "agent_runtime.serve.apis.orchestration.async_ir_load",
            new_callable=AsyncMock,
        ) as mock_load:
            mock_load.return_value = {
                "metadata": {"projectId": "proj-1", "updatedAt": "2000"}
            }
            result = await check_before_agent_run(RunCheckContext(
                query="hello",
                project_id="proj-1",
                ir_path="ir/path.json",
                body_version="1000",
                has_published_version=False,
            ))
            assert result is not None
            assert result.status_code == 403
