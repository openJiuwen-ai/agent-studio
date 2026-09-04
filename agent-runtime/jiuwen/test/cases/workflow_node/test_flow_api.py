# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.

"""
FlowApi 组件工作流集成测试

完整工作流: Start -> FlowApi -> End

使用 mock 替代真实 HTTP 请求，确保测试稳定性。

运行方式:
    pytest jiuwen/test/cases/workflow_node/test_flow_api.py -v -s
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from jiuwen.extension.workflow_node.end import End
from jiuwen.extension.workflow_node.flow_api import FlowApi
from jiuwen.extension.workflow_node.start import Start
from jiuwen.extension.wrapper.restful_api_new import RestfulApiToolNew
from openjiuwen.core.common.logging import workflow_logger
from openjiuwen.core.workflow import (
    Workflow,
    WorkflowExecutionState,
    create_workflow_session,
)


@pytest.fixture(scope="function", autouse=True)
def ensure_event_loop():
    """
    解决：运行整个测试目录时，事件循环被关闭/不存在的问题
    每次测试都强制创建新 loop，彻底杜绝跨文件污染
    """
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

MOCK_WEATHER_DATA = {
    "latitude": 39.9,
    "longitude": 116.4,
    "current_weather": "true",
}

MOCK_API_SUCCESS = {
    "errCode": 0,
    "errMessage": "success",
    "data": MOCK_WEATHER_DATA,
}


async def _mock_stream_items():
    """模拟 astream 返回的异步生成器"""
    yield str("test mock restful stream")


# ---------- 配置工厂 ----------


def _make_start_conf() -> dict:
    """Start 组件配置（定义工作流输入变量）"""
    return {
        "userFields": {
            "inputs": [
                {
                    "id": "latitude",
                    "type": "number",
                    "required": True,
                    "description": "纬度，例如北京为 39.9042",
                },
                {
                    "id": "longitude",
                    "type": "number",
                    "required": True,
                    "description": "经度，例如北京为 116.4074",
                },
                {
                    "id": "current_weather",
                    "type": "string",
                    "required": False,
                    "description": "是否返回当前天气",
                },
            ],
            "outputs": [],
        },
        "systemFields": {
            "inputs": [],
            "outputs": [],
        },
    }


def _make_flow_api_ir_conf() -> dict:
    """FlowApi 组件的 IR 配置（无 apiId，直接从 IR 构建 RestfulApiToolNew）"""
    return {
        "id": "weather_api",
        "name": "get_weather",
        "description": "查询指定经纬度的当前天气信息",
        "url": "https://api.open-meteo.com/v1/forecast",
        "method": "GET",
        "headers": {"Accept": "application/json"},
        "auth": {},
        "arguments": [
            {
                "name": "latitude",
                "description": "纬度",
                "type": "number",
                "required": True,
                "method": "Query",
            },
            {
                "name": "longitude",
                "description": "经度",
                "type": "number",
                "required": True,
                "method": "Query",
            },
            {
                "name": "current_weather",
                "description": "是否返回当前天气",
                "type": "string",
                "required": False,
                "default_value": "true",
                "method": "Query",
            },
        ],
        "response": [
            {
                "name": "temperature",
                "description": "当前温度",
                "type": "number",
                "required": False,
            },
            {
                "name": "windspeed",
                "description": "风速",
                "type": "number",
                "required": False,
            },
        ],
        "pluginDependency": {},
        "asyncInvoke": {},
        "inputParameters": {},
        "userFields": {
            "outputs": [
                {"id": "weather_result", "required": True},
            ]
        },
    }


def _make_end_conf() -> dict:
    """End 组件配置"""
    return {
        "name": "output_node",
        "responseTemplate": "{{weather_data}}",
    }


# ---------- 工作流构建 ----------


def _build_weather_workflow(*, streaming: bool = False) -> Workflow:
    """构建 Start -> FlowApi -> End 工作流

    Args:
        streaming: 为 True 时 flow_api_node -> end_node 使用流式边，
                   FlowApi 将调用 stream() 而非 invoke()。
    """
    workflow = Workflow()

    start_comp = Start(_make_start_conf())
    flow_api_comp = FlowApi(_make_flow_api_ir_conf())
    end_comp = End(_make_end_conf())

    workflow.set_start_comp(
        "start_node",
        start_comp,
        inputs_schema={
            "latitude": "${latitude}",
            "longitude": "${longitude}",
            "current_weather": "${current_weather}",
        },
    )

    workflow.add_workflow_comp(
        "flow_api_node",
        flow_api_comp,
        inputs_schema={
            USER_FIELDS: "${start_node.userFields}",
            SYSTEM_FIELDS: "${start_node.systemFields}",
        },
    )

    if streaming:
        # 流式模式：End 组件配置 response_mode="streaming"，
        # flow_api_node -> end_node 使用流式边，FlowApi 调用 stream()
        workflow.set_end_comp(
            "end_node",
            end_comp,
            stream_inputs_schema={
                "weather_data": "${flow_api_node.userFields}",
            },
            response_mode="streaming",
        )
        workflow.add_connection("start_node", "flow_api_node")
        workflow.add_stream_connection("flow_api_node", "end_node")
    else:
        # 非流式模式：全部使用普通边，FlowApi 调用 invoke()
        workflow.set_end_comp(
            "end_node",
            end_comp,
            inputs_schema={
                "weather_data": "${flow_api_node.userFields}",
            },
        )
        workflow.add_connection("start_node", "flow_api_node")
        workflow.add_connection("flow_api_node", "end_node")

    return workflow


# ---------- 公共 fixture ----------


@pytest.fixture
def mock_api():
    """Mock RestfulApiToolNew 的 ainvoke 和 astream 方法，避免真实 HTTP 请求"""
    with patch.object(
        RestfulApiToolNew, "ainvoke", new_callable=AsyncMock
    ) as mock_ainvoke:
        mock_ainvoke.return_value = MOCK_API_SUCCESS
        with patch.object(RestfulApiToolNew, "astream") as mock_astream:
            mock_astream.return_value = _mock_stream_items()
            yield {"ainvoke": mock_ainvoke, "astream": mock_astream}


# ---------- 测试类 ----------


class TestFlowApiWorkflow:
    """FlowApi 工作流集成测试"""

    @pytest.fixture
    def invoke_workflow(self) -> Workflow:
        """非流式工作流：全部使用 add_connection，FlowApi 调用 invoke()"""
        return _build_weather_workflow(streaming=False)

    @pytest.fixture
    def stream_workflow(self) -> Workflow:
        """流式工作流：flow_api_node -> end_node 使用 add_stream_connection"""
        return _build_weather_workflow(streaming=True)

    @pytest.fixture
    def session(self):
        return create_workflow_session()

    @pytest.mark.asyncio
    async def test_invoke_weather_api(self, mock_api, invoke_workflow, session):
        """测试非流式调用: Start -> FlowApi(invoke) -> End"""
        inputs = {
            "latitude": 39.9042,
            "longitude": 116.4074,
            "current_weather": "true",
        }

        result = await invoke_workflow.invoke(inputs, session=session)

        assert result is not None
        assert result.state == WorkflowExecutionState.COMPLETED
        assert result.result is not None

        mock_api["ainvoke"].assert_awaited_once()

    @pytest.mark.asyncio
    async def test_stream_weather_api(self, mock_api, stream_workflow, session):
        """测试流式调用: Start -> FlowApi(stream) -> End

        流式工作流使用 add_stream_connection，引擎为 flow_api_node 分配 STREAM 能力，
        从而调用 FlowApi.stream() 而非 invoke()。
        """
        inputs = {
            "latitude": 39.9042,
            "longitude": 116.4074,
            "current_weather": "true",
        }

        chunks = []
        async for chunk in stream_workflow.stream(inputs, session=session):
            chunks.append(chunk)
        workflow_logger.info(f"chunks: {chunks}")

        assert len(chunks) > 0, "流式调用应该返回至少一个 chunk"
        # 验证 astream 被调用而非 ainvoke
        mock_api["astream"].assert_called_once()

    @pytest.mark.asyncio
    async def test_flow_api_direct_invoke(self, mock_api):
        """直接测试 FlowApi 组件（非工作流）的 invoke"""
        conf = _make_flow_api_ir_conf()
        flow_api = FlowApi(conf)
        flow_api.init(conf)

        session = create_workflow_session(
            session_id="test_direct_invoke",
            envs={"_REQUEST": {}},
        )

        inputs = {
            USER_FIELDS: {
                "latitude": 39.9042,
                "longitude": 116.4074,
                "current_weather": "true",
            }
        }

        result = await flow_api.invoke(inputs, session, None)

        assert USER_FIELDS in result
        # _format_api_outputs 返回 data 字段内容
        assert result[USER_FIELDS] == MOCK_WEATHER_DATA

    @pytest.mark.asyncio
    async def test_flow_api_init_with_ir(self):
        """测试 FlowApi 通过 IR 配置初始化"""
        conf = _make_flow_api_ir_conf()
        flow_api = FlowApi(conf)
        flow_api.init(conf)

        assert flow_api._api is not None
        assert flow_api._api.name == "get_weather"
        assert flow_api._api_id == "weather_api"
        assert len(flow_api._api.params) == 3
        assert flow_api._enable_validate is False
        assert flow_api._enable_confirm is False

    @pytest.mark.asyncio
    async def test_flow_api_format_outputs_error_code(self):
        """测试 _format_api_outputs 处理错误码"""
        conf = _make_flow_api_ir_conf()
        flow_api = FlowApi(conf)
        flow_api.init(conf)

        # 成功响应 → 返回 data 字段
        success_output = {"errCode": 0, "errMessage": "success", "data": {"temp": 25}}
        assert flow_api._format_api_outputs(success_output) == {"temp": 25}

        # 错误响应 → 抛出 JiuWenBaseException
        from jiuwen.extension.workflow_node.utils import JiuWenBaseException

        error_output = {"errCode": 105001, "errMessage": "internal error", "data": None}
        with pytest.raises(JiuWenBaseException) as exc_info:
            flow_api._format_api_outputs(error_output)
        assert exc_info.value.error_code == 105001

    @pytest.mark.asyncio
    async def test_flow_api_exception_suppression(self):
        """测试异常抑制功能"""
        conf = _make_flow_api_ir_conf()
        conf["exceptionEnable"] = True
        conf["exceptionSuppression"] = '{"fallback": "default_value"}'

        flow_api = FlowApi(conf)
        flow_api.init(conf)

        session = create_workflow_session(
            session_id="test_exception_suppression",
            envs={"_REQUEST": {}},
        )

        # 传入无效参数触发异常，异常抑制应返回默认值
        inputs = {USER_FIELDS: {"invalid_param": "value"}}
        result = await flow_api.invoke(inputs, session, None)

        assert USER_FIELDS in result
        assert result[USER_FIELDS].get("fallback") == "default_value"
