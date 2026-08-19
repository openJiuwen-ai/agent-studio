# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from jiuwen.extension.workflow_node.flow_mcp import FlowMcp
from jiuwen.extension.wrapper.mcp_tool_wrapper import JIUWEN_RUNTIME_KWARGS
from openjiuwen.core.foundation.tool.mcp.base import McpToolCard
from openjiuwen.core.workflow import create_workflow_session


USER_FIELDS = "userFields"


# ─── helpers ──────────────────────────────────────────────────────────


def _make_flow_mcp_conf(*, older_version: bool = False) -> dict:
    """FlowMcp 组件的 IR 配置"""
    conf = {
        "type": "sse",
        "url": "http://localhost:3000/mcp",
        "name": "weather_mcp_server",
        "tool_name": "mock_tool",
        "description": "A mock MCP tool for testing",
        "headers": {"Authorization": "Bearer test-token"},
        "auth": {
            "headers": {},
            "query": {"key": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx==="},
            "scope": "SERVICE",
        },
        "pluginDependency": {},
    }
    if not older_version:
        conf["arguments"] = [
            {
                "name": "query",
                "description": "查询内容",
                "type": "string",
                "required": True,
                "method": "Body",
            },
        ]
    return conf


def _make_mock_card() -> McpToolCard:
    """构造供 list_tools 返回的 Mock McpToolCard"""
    return McpToolCard(
        name="mock_tool",
        server_name="weather_mcp_server",
        description="",
        input_params={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                JIUWEN_RUNTIME_KWARGS: {"type": "object"},
            },
            "additionalProperties": True,
        },
    )


# ─── fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def mock_mcp_client():
    """Mock SSEClientNew 的 list_tools 和 call_tool 方法，避免真实网络请求"""
    with patch(
        "jiuwen.extension.wrapper.sse_client_new.SSEClientNew.list_tools",
        new_callable=AsyncMock,
    ) as mock_list_tools:
        mock_list_tools.return_value = [_make_mock_card()]

        with patch(
            "jiuwen.extension.wrapper.sse_client_new.SSEClientNew.call_tool",
            new_callable=AsyncMock,
        ) as mock_call_tool:
            mock_call_tool.return_value = [
                {
                    "model_dump": lambda: {
                        "type": "text",
                        "text": "mock mcp response",
                    }
                }
            ]
            yield {
                "list_tools": mock_list_tools,
                "call_tool": mock_call_tool,
            }


# ─── 测试类 ───────────────────────────────────────────────────────────


class TestFlowMcpConcurrentInit:
    """FlowMcp 并发初始化锁测试

    守护修复目标：_init_api 双重检查锁保证高并发 invoke 下
    MCPTool 只创建一次、list_tools 只调用一次，且不引入死锁/异常吞没。
    """

    @pytest.mark.asyncio
    async def test_concurrent_invoke_initializes_only_once(self, mock_mcp_client):
        """并发 invoke 时 list_tools / MCPTool 只初始化一次"""
        conf = _make_flow_mcp_conf(older_version=True)  # 旧版路径，走 list_tools
        flow_mcp = FlowMcp(conf)
        session = create_workflow_session()

        # list_tools 内真正 await，强制让出协程以复现竞态
        async def _slow_list_tools():
            await asyncio.sleep(0.01)
            return [_make_mock_card()]

        mock_mcp_client["list_tools"].side_effect = _slow_list_tools

        inputs = {USER_FIELDS: {"query": "hello"}}
        results = await asyncio.gather(
            *(flow_mcp.invoke(inputs, session, None) for _ in range(20))
        )

        assert mock_mcp_client["list_tools"].await_count == 1  # 无锁时会远大于 1
        assert mock_mcp_client["call_tool"].await_count == 20
        assert all(r[USER_FIELDS]["isError"] is False for r in results)
        assert flow_mcp.api is not None

    @pytest.mark.asyncio
    async def test_second_waiter_skips_init_after_lock_release(self, mock_mcp_client):
        """等锁协程拿锁后 double-check 命中，不再 init"""
        conf = _make_flow_mcp_conf(older_version=True)
        flow_mcp = FlowMcp(conf)
        session = create_workflow_session()

        entered = asyncio.Event()
        release = asyncio.Event()

        async def _gated_list_tools():
            entered.set()  # 第一个协程已进入 list_tools（持有锁）
            await release.wait()  # 阻塞，让第二个协程排队抢锁
            return [_make_mock_card()]

        mock_mcp_client["list_tools"].side_effect = _gated_list_tools

        inputs = {USER_FIELDS: {"query": "hello"}}
        t1 = asyncio.create_task(flow_mcp.invoke(inputs, session, None))
        await entered.wait()
        t2 = asyncio.create_task(flow_mcp.invoke(inputs, session, None))
        await asyncio.sleep(0.01)  # 让 t2 排到锁上
        release.set()  # 放行第一个

        r1, r2 = await asyncio.gather(t1, t2)

        assert mock_mcp_client["list_tools"].await_count == 1  # 第二个 double-check 跳过
        assert r1[USER_FIELDS]["isError"] is False
        assert r2[USER_FIELDS]["isError"] is False

    @pytest.mark.asyncio
    async def test_serial_invoke_does_not_re_initialize(self, mock_mcp_client):
        """初始化完成后，后续串行 invoke 不再调 list_tools（锁外快速路径）"""
        conf = _make_flow_mcp_conf(older_version=True)
        flow_mcp = FlowMcp(conf)
        session = create_workflow_session()

        inputs = {USER_FIELDS: {"query": "hello"}}
        await flow_mcp.invoke(inputs, session, None)
        await flow_mcp.invoke(inputs, session, None)
        await flow_mcp.invoke(inputs, session, None)

        assert mock_mcp_client["list_tools"].await_count == 1
        assert mock_mcp_client["call_tool"].await_count == 3

    @pytest.mark.asyncio
    async def test_concurrent_invoke_all_succeed_without_deadlock(self, mock_mcp_client):
        """并发调用不死锁，结果全部成功"""
        conf = _make_flow_mcp_conf(older_version=True)
        flow_mcp = FlowMcp(conf)
        session = create_workflow_session()

        async def _fast_list_tools():
            await asyncio.sleep(0)
            return [_make_mock_card()]

        mock_mcp_client["list_tools"].side_effect = _fast_list_tools

        inputs = {USER_FIELDS: {"query": "hello"}}
        results = await asyncio.wait_for(
            asyncio.gather(
                *(flow_mcp.invoke(inputs, session, None) for _ in range(50))
            ),
            timeout=5.0,
        )
        assert len(results) == 50
        assert all(r[USER_FIELDS]["isError"] is False for r in results)

    @pytest.mark.asyncio
    async def test_init_failure_releases_lock_and_propagates(self, mock_mcp_client):
        """_init_api 抛异常时锁被释放、异常透传，后续可重试"""
        conf = _make_flow_mcp_conf(older_version=True)
        flow_mcp = FlowMcp(conf)
        session = create_workflow_session()

        call_count = {"n": 0}

        async def _fail_then_ok():
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise RuntimeError("list_tools boom")
            return [_make_mock_card()]

        mock_mcp_client["list_tools"].side_effect = _fail_then_ok

        inputs = {USER_FIELDS: {"query": "hello"}}

        # 第一次：异常透传，锁已释放，api 仍为 None
        with pytest.raises(Exception, match="list_tools boom"):
            await flow_mcp.invoke(inputs, session, None)
        assert flow_mcp.api is None

        # 第二次：锁可用，重试成功
        r = await asyncio.wait_for(
            flow_mcp.invoke(inputs, session, None), timeout=3.0
        )
        assert r[USER_FIELDS]["isError"] is False
        assert flow_mcp.api is not None

    @pytest.mark.asyncio
    async def test_new_version_concurrent_skips_list_tools(self, mock_mcp_client):
        """新版（有 arguments）并发 invoke 不调 list_tools（对照路径）"""
        conf = _make_flow_mcp_conf()  # 默认带 arguments
        flow_mcp = FlowMcp(conf)
        session = create_workflow_session()

        inputs = {USER_FIELDS: {"query": "hello"}}
        results = await asyncio.gather(
            *(flow_mcp.invoke(inputs, session, None) for _ in range(20))
        )

        mock_mcp_client["list_tools"].assert_not_awaited()
        assert mock_mcp_client["call_tool"].await_count == 20
        assert all(r[USER_FIELDS]["isError"] is False for r in results)
