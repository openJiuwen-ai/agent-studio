# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.

"""
FlowMcp 组件工作流集成测试

完整工作流: Start -> FlowMcp -> End

使用 mock 替代真实 MCP Server 请求，确保测试稳定性。
另有真实服务集成测试，需要本地启动 MCP Server。

运行方式:
    # Mock 测试
    pytest jiuwen/test/cases/workflow_node/test_flow_mcp.py -v -s

    # 真实服务测试（需先启动 MCP Server）
    python -m mcp_weather_server --mode streamable-http --host localhost --port 3000 --debug
    pytest jiuwen/test/cases/workflow_node/test_flow_mcp.py -v -s -k "real"
"""

import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from jiuwen.extension.workflow_node.end import End
from jiuwen.extension.workflow_node.flow_mcp import FlowMcp
from jiuwen.extension.workflow_node.start import Start
from jiuwen.extension.workflow_node.utils import JiuWenBaseException
from jiuwen.extension.wrapper.mcp_tool_wrapper import JIUWEN_RUNTIME_KWARGS
from openjiuwen.core.foundation.tool.mcp.base import McpToolCard
from openjiuwen.core.workflow import (
    Workflow,
    WorkflowExecutionState,
    create_workflow_session,
)


@pytest.fixture(scope="function", autouse=True)
def ensure_event_loop():
    """解决运行整个测试目录时，事件循环被关闭/不存在的问题"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    yield loop


@pytest.fixture(scope="session")
def event_loop():
    """覆盖 pytest-asyncio 默认循环，防止被关闭"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


USER_FIELDS = "userFields"
SYSTEM_FIELDS = "systemFields"

# ---------- Mock 数据 ----------

MOCK_MCP_TOOL_INPUTS = {"query": "hello world"}

MOCK_MCP_CONTENT_ITEMS = [
    MagicMock(
        **{
            "model_dump": MagicMock(
                return_value={"type": "text", "text": "mock mcp response"}
            )
        }
    ),
]

ERR_CODE = "errCode"
ERR_MESSAGE = "errMessage"
RESTFUL_DATA = "data"

MOCK_MCP_SUCCESS_RESULT = {
    ERR_CODE: 0,
    RESTFUL_DATA: MOCK_MCP_CONTENT_ITEMS,
    ERR_MESSAGE: "success",
}

MOCK_MCP_DICT_RESULT = {
    ERR_CODE: 0,
    RESTFUL_DATA: {"structured_key": "structured_value"},
    ERR_MESSAGE: "success",
}

MOCK_MCP_NONE_RESULT = {ERR_CODE: 0, RESTFUL_DATA: None, ERR_MESSAGE: "success"}


# ---------- 配置工厂 ----------


def _make_start_conf() -> dict:
    """Start 组件配置"""
    return {
        "userFields": {
            "inputs": [
                {
                    "id": "query",
                    "type": "string",
                    "required": True,
                    "description": "查询内容",
                },
            ],
            "outputs": [],
        },
        "systemFields": {
            "inputs": [],
            "outputs": [],
        },
    }


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


def _make_end_conf() -> dict:
    """End 组件配置"""
    return {
        "name": "output_node",
        "responseTemplate": "{{mcp_result}}",
    }


# ---------- 工作流构建 ----------


def _build_mcp_workflow() -> Workflow:
    """构建 Start -> FlowMcp -> End 工作流"""
    workflow = Workflow()

    start_comp = Start(_make_start_conf())
    flow_mcp_comp = FlowMcp(_make_flow_mcp_conf())
    end_comp = End(_make_end_conf())

    workflow.set_start_comp(
        "start_node",
        start_comp,
        inputs_schema={
            "query": "${query}",
        },
    )

    workflow.add_workflow_comp(
        "flow_mcp_node",
        flow_mcp_comp,
        inputs_schema={
            USER_FIELDS: "${start_node.userFields}",
            SYSTEM_FIELDS: "${start_node.systemFields}",
        },
    )

    workflow.set_end_comp(
        "end_node",
        end_comp,
        inputs_schema={
            "mcp_result": "${flow_mcp_node.userFields}",
        },
    )

    workflow.add_connection("start_node", "flow_mcp_node")
    workflow.add_connection("flow_mcp_node", "end_node")

    return workflow


# ---------- 公共 fixture ----------


@pytest.fixture
def mock_mcp_client():
    """Mock SSEClientNew 的 list_tools 和 call_tool 方法，避免真实网络请求"""
    tool_card = McpToolCard(
        name="mock_tool",
        server_name="mock_mcp_server",
        description="A mock MCP tool for testing",
        input_params={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                JIUWEN_RUNTIME_KWARGS: {"type": "object"},
            },
            "additionalProperties": True,
        },
    )

    with patch(
        "jiuwen.extension.wrapper.sse_client_new.SSEClientNew.list_tools",
        new_callable=AsyncMock,
    ) as mock_list_tools:
        mock_list_tools.return_value = [tool_card]

        with patch(
            "jiuwen.extension.wrapper.sse_client_new.SSEClientNew.call_tool",
            new_callable=AsyncMock,
        ) as mock_call_tool:
            mock_call_tool.return_value = MOCK_MCP_CONTENT_ITEMS
            yield {
                "list_tools": mock_list_tools,
                "call_tool": mock_call_tool,
            }


@pytest.fixture
def session():
    return create_workflow_session()


# ---------- 测试类 ----------


class TestFlowMcpWorkflow:
    """FlowMcp 工作流集成测试"""

    @pytest.fixture
    def invoke_workflow(self) -> Workflow:
        """非流式工作流"""
        return _build_mcp_workflow()

    @pytest.mark.asyncio
    async def test_start_to_flow_mcp_to_end(
        self, mock_mcp_client, invoke_workflow, session
    ):
        """测试完整工作流: Start -> FlowMcp(invoke) -> End"""
        inputs = {"query": "hello world"}

        result = await invoke_workflow.invoke(inputs, session=session)

        assert result is not None
        assert result.state == WorkflowExecutionState.COMPLETED
        assert result.result is not None

        # 新版本（有 arguments）不调 list_tools，只调 call_tool
        mock_mcp_client["list_tools"].assert_not_awaited()
        mock_mcp_client["call_tool"].assert_awaited_once()

    @pytest.mark.asyncio
    async def test_flow_mcp_direct_invoke(self, mock_mcp_client):
        """直接测试 FlowMcp 组件（非工作流）的 invoke"""
        conf = _make_flow_mcp_conf()
        flow_mcp = FlowMcp(conf)

        session = create_workflow_session(
            session_id="test_direct_invoke",
            envs={"_REQUEST": {}},
        )

        inputs = {
            USER_FIELDS: {"query": "hello world"},
        }

        result = await flow_mcp.invoke(inputs, session, None)

        assert USER_FIELDS in result
        assert result[USER_FIELDS]["isError"] is False
        assert "content" in result[USER_FIELDS]
        mock_mcp_client["call_tool"].assert_awaited_once()

    @pytest.mark.asyncio
    async def test_flow_mcp_init(self, mock_mcp_client):
        """测试 FlowMcp 初始化"""
        conf = _make_flow_mcp_conf()
        flow_mcp = FlowMcp(conf)

        assert flow_mcp._client is not None
        assert flow_mcp._is_older_version is False

    @pytest.mark.asyncio
    async def test_flow_mcp_init_older_version(self, mock_mcp_client):
        """测试旧版本 IR 初始化（无 arguments）"""
        conf = _make_flow_mcp_conf(older_version=True)
        flow_mcp = FlowMcp(conf)

        assert flow_mcp._is_older_version is True

    @pytest.mark.asyncio
    async def test_flow_mcp_format_outputs_list(self, mock_mcp_client):
        """测试 _format_api_outputs 处理 list 类型返回"""
        conf = _make_flow_mcp_conf()
        flow_mcp = FlowMcp(conf)

        result = flow_mcp._format_api_outputs(MOCK_MCP_SUCCESS_RESULT)
        assert result["isError"] is False
        assert "content" in result
        assert len(result["content"]) == 1
        assert result["content"][0] == {"type": "text", "text": "mock mcp response"}

    @pytest.mark.asyncio
    async def test_flow_mcp_format_outputs_dict(self, mock_mcp_client):
        """测试 _format_api_outputs 处理 dict 类型返回（structuredContent）"""
        conf = _make_flow_mcp_conf()
        flow_mcp = FlowMcp(conf)

        result = flow_mcp._format_api_outputs(MOCK_MCP_DICT_RESULT)
        assert result == {"structured_key": "structured_value"}

    @pytest.mark.asyncio
    async def test_flow_mcp_format_outputs_none(self, mock_mcp_client):
        """测试 _format_api_outputs 处理 None 返回"""
        conf = _make_flow_mcp_conf()
        flow_mcp = FlowMcp(conf)

        result = flow_mcp._format_api_outputs(MOCK_MCP_NONE_RESULT)
        assert result == {"content": [], "isError": False}

    @pytest.mark.asyncio
    async def test_flow_mcp_format_outputs_unexpected_type(self, mock_mcp_client):
        """测试 _format_api_outputs 处理意外类型返回"""
        conf = _make_flow_mcp_conf()
        flow_mcp = FlowMcp(conf)

        with pytest.raises(JiuWenBaseException):
            flow_mcp._format_api_outputs({"result": "unexpected_string"})

    @pytest.mark.asyncio
    async def test_flow_mcp_format_api_inputs(self, mock_mcp_client):
        """测试 _format_api_inputs 参数类型转换"""
        conf = _make_flow_mcp_conf()
        flow_mcp = FlowMcp(conf)

        inputs = {"query": "hello"}
        result = flow_mcp._format_api_inputs(inputs)
        assert result == {"query": "hello"}

    @pytest.mark.asyncio
    async def test_flow_mcp_format_api_inputs_unknown_param(self, mock_mcp_client):
        """测试 _format_api_inputs 未知参数报错"""
        conf = _make_flow_mcp_conf()
        flow_mcp = FlowMcp(conf)

        with pytest.raises(JiuWenBaseException):
            flow_mcp._format_api_inputs({"unknown_param": "value"})

    @pytest.mark.asyncio
    async def test_flow_mcp_validate_configs_unsupported_type(self):
        """测试不支持的服务类型"""
        conf = _make_flow_mcp_conf()
        conf["type"] = "unsupported"
        with pytest.raises(JiuWenBaseException):
            FlowMcp(conf)

    @pytest.mark.asyncio
    async def test_flow_mcp_validate_configs_missing_url(self):
        """测试缺少 url 字段"""
        conf = _make_flow_mcp_conf()
        conf.pop("url")
        with pytest.raises(JiuWenBaseException):
            FlowMcp(conf)

    @pytest.mark.asyncio
    async def test_flow_mcp_validate_configs_missing_tool_name(self):
        """测试缺少 tool_name 字段"""
        conf = _make_flow_mcp_conf()
        conf.pop("tool_name")
        with pytest.raises(JiuWenBaseException):
            FlowMcp(conf)

    @pytest.mark.asyncio
    async def test_flow_mcp_no_api_returns_default(self, mock_mcp_client):
        """测试 type 为 stdio 时不创建 api，invoke 返回默认值"""
        conf = _make_flow_mcp_conf()
        conf["type"] = "stdio"
        flow_mcp = FlowMcp(conf)

        session = create_workflow_session()
        result = await flow_mcp.invoke({USER_FIELDS: {"query": "test"}}, session, None)

        assert USER_FIELDS in result
        assert result[USER_FIELDS]["isError"] is False
        assert "not contain mcp api" in result[USER_FIELDS]["content"]

    @pytest.mark.asyncio
    async def test_flow_mcp_runtime_auth_injection(self, mock_mcp_client):
        """测试 runtime_auth 从 session 注入到 JIUWEN_RUNTIME_KWARGS"""
        conf = _make_flow_mcp_conf()
        flow_mcp = FlowMcp(conf)

        session = create_workflow_session()
        # 模拟 session 中存在 runtime_auth_headers
        session.get_global_state = MagicMock(
            return_value={
                "mock_tool": {"X-Custom-Auth": "token123"},
                "default": {"X-Default": "default_token"},
            }
        )

        inputs = {USER_FIELDS: {"query": "hello"}}
        await flow_mcp.invoke(inputs, session, None)

        # 验证 call_tool 被调用，且 JIUWEN_RUNTIME_KWARGS 已从 arguments 中被 pop
        call_args = mock_mcp_client["call_tool"].call_args
        arguments = (
            call_args[1]
            if len(call_args) > 1
            else call_args.kwargs.get("arguments", {})
        )
        # arguments 中不应包含 _jiuwen_runtime_kwargs（已被 pop）
        assert "_jiuwen_runtime_kwargs" not in arguments

    @pytest.mark.asyncio
    async def test_flow_mcp_older_version_skip_format(self, mock_mcp_client):
        """测试旧版本 IR 跳过参数格式化，直接透传 inputs"""
        conf = _make_flow_mcp_conf(older_version=True)
        flow_mcp = FlowMcp(conf)

        session = create_workflow_session()
        inputs = {USER_FIELDS: {"query": "raw_input", "extra_field": "extra_value"}}

        result = await flow_mcp.invoke(inputs, session, None)

        # 旧版本不会因 extra_field 报错
        assert USER_FIELDS in result
        # 旧版本通过 list_tools 获取 card
        mock_mcp_client["list_tools"].assert_awaited()
        mock_mcp_client["call_tool"].assert_awaited_once()

    @pytest.mark.asyncio
    async def test_flow_mcp_new_version_skips_list_tools(self, mock_mcp_client):
        """测试新版本（有 arguments）跳过 list_tools，从 arguments 生成 input_params"""
        conf = _make_flow_mcp_conf()
        flow_mcp = FlowMcp(conf)

        session = create_workflow_session()
        inputs = {USER_FIELDS: {"query": "hello"}}

        await flow_mcp.invoke(inputs, session, None)

        # 新版本不调 list_tools
        mock_mcp_client["list_tools"].assert_not_awaited()
        mock_mcp_client["call_tool"].assert_awaited_once()
        # api 已初始化，且 card 的 input_params 由 arguments 生成
        assert flow_mcp.api is not None

    @pytest.mark.asyncio
    async def test_flow_mcp_older_version_calls_list_tools(self, mock_mcp_client):
        """测试旧版本（无 arguments）通过 list_tools 获取 card"""
        conf = _make_flow_mcp_conf(older_version=True)
        flow_mcp = FlowMcp(conf)

        session = create_workflow_session()
        inputs = {USER_FIELDS: {"query": "hello"}}

        await flow_mcp.invoke(inputs, session, None)

        mock_mcp_client["list_tools"].assert_awaited()
        mock_mcp_client["call_tool"].assert_awaited_once()
        assert flow_mcp.api is not None


# ---------- 真实 MCP Server 配置 ----------

WEATHER_SERVER_URL = "http://localhost:3000/mcp"
WEATHER_SERVER_NAME = "weather_mcp_server"


def _make_real_weather_mcp_conf(*, tool_name: str = "get_current_weather") -> dict:
    """真实 weather MCP Server 的 IR 配置（streamable_http）

    不传 arguments（params=[]），参数格式化由 MCPTool 层的 schema 完成，
    与 real_service_test_mcp_server.py 中 _make_valid_mcp_ir_data 的配置一致。
    """
    return {
        "url": WEATHER_SERVER_URL,
        "name": WEATHER_SERVER_NAME,
        "type": "streamable_http",
        "tool_name": tool_name,
        "description": "Weather MCP Server tool",
        "headers": {},
        "auth": {
            "headers": {},
            "query": {"key": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx=="},
            "scope": "SERVICE",
        },
        "pluginDependency": {},
        "arguments": [],
    }


def _make_real_weather_mcp_conf_with_args(
    *, tool_name: str = "get_current_weather"
) -> dict:
    """真实 weather MCP Server 的 IR 配置（带 arguments，新版本路径）

    带 arguments 时走新版本路径：从 arguments 生成 input_params，跳过 list_tools。
    """
    return {
        "url": WEATHER_SERVER_URL,
        "name": WEATHER_SERVER_NAME,
        "type": "streamable_http",
        "tool_name": tool_name,
        "description": "Weather MCP Server tool",
        "headers": {},
        "auth": {},
        "pluginDependency": {},
        "arguments": [
            {
                "name": "city",
                "description": "The name of the city",
                "type": "string",
                "required": True,
                "method": "Body",
            },
        ],
    }


def _make_real_start_conf() -> dict:
    """真实测试用的 Start 组件配置"""
    return {
        "userFields": {
            "inputs": [
                {
                    "id": "city",
                    "type": "string",
                    "required": True,
                    "description": "城市名称",
                },
            ],
            "outputs": [],
        },
        "systemFields": {
            "inputs": [],
            "outputs": [],
        },
    }


def _build_real_weather_workflow() -> Workflow:
    """构建 Start -> FlowMcp(weather) -> End 真实工作流"""
    workflow = Workflow()

    start_comp = Start(_make_real_start_conf())
    flow_mcp_comp = FlowMcp(_make_real_weather_mcp_conf())
    end_comp = End(_make_end_conf())

    workflow.set_start_comp(
        "start_node",
        start_comp,
        inputs_schema={
            "city": "${city}",
        },
    )

    workflow.add_workflow_comp(
        "flow_mcp_node",
        flow_mcp_comp,
        inputs_schema={
            USER_FIELDS: "${start_node.userFields}",
            SYSTEM_FIELDS: "${start_node.systemFields}",
        },
    )

    workflow.set_end_comp(
        "end_node",
        end_comp,
        inputs_schema={
            "mcp_result": "${flow_mcp_node.userFields}",
        },
    )

    workflow.add_connection("start_node", "flow_mcp_node")
    workflow.add_connection("flow_mcp_node", "end_node")

    return workflow


# ---------- 真实服务测试类 ----------


@pytest.mark.skip(reason="真实服务测试需要手动启动 mcp_weather_server 服务")
class TestFlowMcpRealService:
    """FlowMcp 真实 MCP Server 集成测试

    前置条件:
    - pip install mcp_weather_server starlette uvicorn
    - python -m mcp_weather_server --mode streamable-http --host localhost --port 3000 --debug
    """

    @pytest.mark.asyncio
    async def test_real_flow_mcp_direct_invoke(self):
        """真实服务: 直接调用 FlowMcp 组件 invoke"""
        conf = _make_real_weather_mcp_conf()
        flow_mcp = FlowMcp(conf)

        assert flow_mcp._client is not None

        session = create_workflow_session(session_id="real_test_direct")

        inputs = {USER_FIELDS: {"city": "shanghai"}}
        result = await flow_mcp.invoke(inputs, session, None)

        assert USER_FIELDS in result
        user_data = result[USER_FIELDS]
        assert user_data.get("isError") is False
        print(f"真实 invoke 结果: {user_data}")

    @pytest.mark.asyncio
    async def test_real_flow_mcp_workflow(self):
        """真实服务: 完整工作流 Start -> FlowMcp -> End"""
        workflow = _build_real_weather_workflow()
        session = create_workflow_session(session_id="real_test_workflow")

        inputs = {"city": "beijing"}
        result = await workflow.invoke(inputs, session=session)

        assert result is not None
        assert result.state == WorkflowExecutionState.COMPLETED
        assert result.result is not None
        print(f"真实工作流结果: {result.result}")

    @pytest.mark.asyncio
    async def test_real_flow_mcp_init_and_list_tools(self):
        """真实服务: 验证旧版本（无 arguments）通过 list_tools 初始化"""
        conf = _make_real_weather_mcp_conf()
        flow_mcp = FlowMcp(conf)

        assert flow_mcp._client is not None
        assert flow_mcp.api is None  # 延迟初始化，invoke 前为 None
        assert flow_mcp._is_older_version is True

        session = create_workflow_session(session_id="real_test_init")
        await flow_mcp.invoke({USER_FIELDS: {"city": "shanghai"}}, session, None)

        # invoke 后 api 应已初始化
        assert flow_mcp.api is not None
        print(f"旧版本 api 初始化完成: {flow_mcp.api}")

    @pytest.mark.asyncio
    async def test_real_flow_mcp_with_arguments_direct_invoke(self):
        """真实服务: 新版本（有 arguments）直接 invoke，跳过 list_tools"""
        conf = _make_real_weather_mcp_conf_with_args()
        flow_mcp = FlowMcp(conf)

        assert flow_mcp._client is not None
        assert flow_mcp._is_older_version is False

        session = create_workflow_session(session_id="real_test_with_args")
        inputs = {USER_FIELDS: {"city": "shanghai"}}
        result = await flow_mcp.invoke(inputs, session, None)

        assert USER_FIELDS in result
        user_data = result[USER_FIELDS]
        assert user_data.get("isError") is False
        assert flow_mcp.api is not None
        print(f"新版本带 arguments invoke 结果: {user_data}")

    @pytest.mark.asyncio
    async def test_real_flow_mcp_with_arguments_workflow(self):
        """真实服务: 新版本（有 arguments）完整工作流 Start -> FlowMcp -> End"""
        workflow = Workflow()

        start_comp = Start(_make_real_start_conf())
        flow_mcp_comp = FlowMcp(_make_real_weather_mcp_conf_with_args())
        end_comp = End(_make_end_conf())

        workflow.set_start_comp(
            "start_node",
            start_comp,
            inputs_schema={"city": "${city}"},
        )
        workflow.add_workflow_comp(
            "flow_mcp_node",
            flow_mcp_comp,
            inputs_schema={
                USER_FIELDS: "${start_node.userFields}",
                SYSTEM_FIELDS: "${start_node.systemFields}",
            },
        )
        workflow.set_end_comp(
            "end_node",
            end_comp,
            inputs_schema={"mcp_result": "${flow_mcp_node.userFields}"},
        )
        workflow.add_connection("start_node", "flow_mcp_node")
        workflow.add_connection("flow_mcp_node", "end_node")

        session = create_workflow_session(session_id="real_test_with_args_workflow")
        result = await workflow.invoke({"city": "beijing"}, session=session)

        assert result is not None
        assert result.state == WorkflowExecutionState.COMPLETED
        assert result.result is not None
        print(f"新版本带 arguments 工作流结果: {result.result}")
