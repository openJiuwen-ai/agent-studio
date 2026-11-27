#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# pylint: disable=protected-access
"""FlowSql MANAGER_NOT_DEPLOYED 前置检查测试（bug005 #1）。

运行态未部署 manager（AGENT_MANAGER_ENDPOINT 为空）时，SQL 节点应在发起 HTTP 前抛
101755 友好提示，而非拼出空 host URL 导致连接错误。错误码 101755 的中英文 i18n
消息由 ErrorContextBuilder 按 code 查 runtime-msg_{lang}.properties 解析。

protected-access：本测试直接调用 _call_execute_api 以精确验证其内置前置检查
（MANAGER_NOT_DEPLOYED），与 test_cache_utils.py 同一约定；invoke 会包装异常与
输出格式，无法精确断言前置检查行为。
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from jiuwen.extension.workflow_node.flow_sql import FlowSql, FlowSqlStatusCode
from jiuwen.extension.workflow_node.utils import JiuWenBaseException


class TestFlowSqlManagerNotDeployed:
    @pytest.mark.asyncio
    async def test_empty_endpoint_raises_101755(self):
        flow_sql = FlowSql(conf={"id": "ds-1", "sql": "SELECT 1"})
        with patch("jiuwen.extension.workflow_node.flow_sql.MANAGER_ENDPOINT", ""):
            with pytest.raises(JiuWenBaseException) as exc_info:
                await flow_sql._call_execute_api({})
            assert exc_info.value.error_code == FlowSqlStatusCode.MANAGER_NOT_DEPLOYED.value[0]
            assert exc_info.value.error_code == 101755

    @pytest.mark.asyncio
    async def test_whitespace_endpoint_raises_101755(self):
        flow_sql = FlowSql(conf={"id": "ds-1", "sql": "SELECT 1"})
        with patch("jiuwen.extension.workflow_node.flow_sql.MANAGER_ENDPOINT", "   "):
            with pytest.raises(JiuWenBaseException) as exc_info:
                await flow_sql._call_execute_api({})
            assert exc_info.value.error_code == FlowSqlStatusCode.MANAGER_NOT_DEPLOYED.value[0]
            assert exc_info.value.error_code == 101755

    @pytest.mark.asyncio
    async def test_valid_endpoint_proceeds_past_precheck(self):
        """有 endpoint 时前置检查放行，进入 HTTP 调用（mock 200 返回），不抛 101755。"""
        flow_sql = FlowSql(conf={"id": "ds-1", "sql": "SELECT 1"})
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value={"outputList": [], "rowNum": 0})
        # http_session.post(url, json=body) -> async ctx manager -> resp
        post_ctx = MagicMock()
        post_ctx.__aenter__ = AsyncMock(return_value=mock_resp)
        post_ctx.__aexit__ = AsyncMock(return_value=False)
        http_session = MagicMock()
        http_session.post.return_value = post_ctx
        # async with aiohttp.ClientSession(...) as http_session
        session_ctx = MagicMock()
        session_ctx.__aenter__ = AsyncMock(return_value=http_session)
        session_ctx.__aexit__ = AsyncMock(return_value=False)
        with patch("jiuwen.extension.workflow_node.flow_sql.MANAGER_ENDPOINT", "http://manager:8080"), \
             patch("aiohttp.ClientSession", return_value=session_ctx):
            result = await flow_sql._call_execute_api({})
        assert result == {"outputList": [], "rowNum": 0}
