# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Tests for conversation_variable_api.py — 会话全局变量管理."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.responses import JSONResponse

from agent_runtime.serve.apis.conversation_variable_api import (
    VariableInfo,
    ConversationVariableRsp,
    UpdateVariableReq,
    _build_redis_key,
    _parse_variables_from_json,
    conversation_variable_router,
)
from agent_runtime.context.request_context import RequestContext


def _mock_request_ctx():
    """构造模拟的请求上下文."""
    ctx = RequestContext(headers={"x-language": "zh-cn"})
    return ctx


class TestBuildRedisKey:
    """Redis key 构建测试."""

    @staticmethod
    def test_key_format():
        key = _build_redis_key("agent-123", "conv-456")
        assert key == "global.vals.agent-123.conv-456"


class TestParseVariablesFromJson:
    """JSON 解析测试."""

    @staticmethod
    def test_normal_json():
        result = _parse_variables_from_json('{"aaa": "", "bbb": {"ccc": "hello"}}')
        assert len(result) == 2
        names = {v.name for v in result}
        assert "aaa" in names
        assert "bbb" in names

    @staticmethod
    def test_empty_string():
        result = _parse_variables_from_json("")
        assert result == []

    @staticmethod
    def test_none_input():
        result = _parse_variables_from_json(None)
        assert result == []

    @staticmethod
    def test_non_dict_json():
        result = _parse_variables_from_json("[1, 2, 3]")
        assert result == []

    @staticmethod
    def test_numeric_value():
        result = _parse_variables_from_json('{"count": 42}')
        assert result[0].name == "count"
        assert result[0].value == 42


class TestVariableInfo:
    """VariableInfo model tests."""

    @staticmethod
    def test_defaults():
        info = VariableInfo()
        assert info.name == ""
        assert info.value is None

    @staticmethod
    def test_with_values():
        info = VariableInfo(name="key1", value="val1")
        assert info.name == "key1"
        assert info.value == "val1"

    @staticmethod
    def test_complex_value():
        info = VariableInfo(name="nested", value={"inner": "data"})
        assert info.value == {"inner": "data"}


class TestConversationVariableRsp:
    """ConversationVariableRsp model tests."""

    @staticmethod
    def test_defaults():
        rsp = ConversationVariableRsp()
        assert rsp.status == "success"
        assert rsp.data == []

    @staticmethod
    def test_with_data():
        vars_list = [VariableInfo(name="k1", value="v1")]
        rsp = ConversationVariableRsp(data=vars_list)
        assert len(rsp.data) == 1
        assert rsp.data[0].name == "k1"


class TestGetConversationVariables:
    """GET 接口测试."""

    @pytest.mark.asyncio
    async def test_redis_returns_data(self):
        raw = json.dumps({"var1": "hello", "var2": 42}).encode("utf-8")
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=raw)

        with patch(
            "common_utils.redis_manager.get_redis_client",
            return_value=mock_client,
        ), patch(
            "agent_runtime.serve.apis.conversation_variable_api._request_ctx"
        ) as mock_ctx:
            mock_ctx.get.return_value = _mock_request_ctx()

            from agent_runtime.serve.apis.conversation_variable_api import (
                get_conversation_variables,
            )

            result = await get_conversation_variables(
                project_id="proj-1",
                agent_id="agent-123",
                conversation_id="conv-456",
            )
            assert isinstance(result, ConversationVariableRsp)
            assert result.status == "success"
            assert len(result.data) == 2

    @pytest.mark.asyncio
    async def test_redis_returns_none(self):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=None)

        with patch(
            "common_utils.redis_manager.get_redis_client",
            return_value=mock_client,
        ), patch(
            "agent_runtime.serve.apis.conversation_variable_api._request_ctx"
        ) as mock_ctx:
            mock_ctx.get.return_value = _mock_request_ctx()

            from agent_runtime.serve.apis.conversation_variable_api import (
                get_conversation_variables,
            )

            result = await get_conversation_variables(
                project_id="proj-1",
                agent_id="agent-123",
                conversation_id="conv-456",
            )
            assert isinstance(result, ConversationVariableRsp)
            assert result.data == []

    @pytest.mark.asyncio
    async def test_redis_returns_invalid_json(self):
        raw = b"not valid json"
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=raw)

        with patch(
            "common_utils.redis_manager.get_redis_client",
            return_value=mock_client,
        ), patch(
            "agent_runtime.serve.apis.conversation_variable_api.ErrorContextBuilder"
            ".get_language_context",
            return_value=("err", "msg", "reason", "suggestion"),
        ), patch(
            "agent_runtime.serve.apis.conversation_variable_api._request_ctx"
        ) as mock_ctx:
            mock_ctx.get.return_value = _mock_request_ctx()

            from agent_runtime.serve.apis.conversation_variable_api import (
                get_conversation_variables,
            )

            result = await get_conversation_variables(
                project_id="proj-1",
                agent_id="agent-123",
                conversation_id="conv-456",
            )
            assert isinstance(result, JSONResponse)
            assert result.status_code == 400


class TestUpdateConversationVariable:
    """PUT 接口测试."""

    @pytest.mark.asyncio
    async def test_update_existing_key(self):
        raw = json.dumps({"var1": "old", "var2": 42}).encode("utf-8")
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=raw)
        mock_client.set = AsyncMock()

        with patch(
            "common_utils.redis_manager.get_redis_client",
            return_value=mock_client,
        ), patch(
            "agent_runtime.serve.apis.conversation_variable_api._request_ctx"
        ) as mock_ctx:
            mock_ctx.get.return_value = _mock_request_ctx()
            body = UpdateVariableReq(value="new")

            from agent_runtime.serve.apis.conversation_variable_api import (
                update_conversation_variable,
            )

            result = await update_conversation_variable(
                body=body,
                project_id="proj-1",
                agent_id="agent-123",
                conversation_id="conv-456",
                var_id="var1",
            )
            assert isinstance(result, VariableInfo)
            assert result.name == "var1"
            assert result.value == "new"
            mock_client.set.assert_awaited_once()
            # 验证 set 调用包含 ex 参数（TTL）
            call_kwargs = mock_client.set.call_args[1]
            assert "ex" in call_kwargs
            assert call_kwargs["ex"] > 0

    @pytest.mark.asyncio
    async def test_add_new_key(self):
        raw = json.dumps({"var1": "old"}).encode("utf-8")
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=raw)
        mock_client.set = AsyncMock()

        with patch(
            "common_utils.redis_manager.get_redis_client",
            return_value=mock_client,
        ), patch(
            "agent_runtime.serve.apis.conversation_variable_api._request_ctx"
        ) as mock_ctx:
            mock_ctx.get.return_value = _mock_request_ctx()
            body = UpdateVariableReq(value="brand_new")

            from agent_runtime.serve.apis.conversation_variable_api import (
                update_conversation_variable,
            )

            result = await update_conversation_variable(
                body=body,
                project_id="proj-1",
                agent_id="agent-123",
                conversation_id="conv-456",
                var_id="new_key",
            )
            assert isinstance(result, VariableInfo)
            assert result.name == "new_key"
            assert result.value == "brand_new"

    @pytest.mark.asyncio
    async def test_redis_empty_returns_400(self):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=None)

        with patch(
            "common_utils.redis_manager.get_redis_client",
            return_value=mock_client,
        ), patch(
            "agent_runtime.serve.apis.conversation_variable_api.ErrorContextBuilder"
            ".get_language_context",
            return_value=("err", "msg", "reason", "suggestion"),
        ), patch(
            "agent_runtime.serve.apis.conversation_variable_api._request_ctx"
        ) as mock_ctx:
            mock_ctx.get.return_value = _mock_request_ctx()
            body = UpdateVariableReq(value="val")

            from agent_runtime.serve.apis.conversation_variable_api import (
                update_conversation_variable,
            )

            result = await update_conversation_variable(
                body=body,
                project_id="proj-1",
                agent_id="agent-123",
                conversation_id="conv-456",
                var_id="var1",
            )
            assert isinstance(result, JSONResponse)
            assert result.status_code == 400
