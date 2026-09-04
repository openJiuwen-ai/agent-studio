#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2026. All rights reserved.
"""
测试 flow_input 和 flow_questioner 迁移
工作流: input -> 地图 MCP 工具 -> questioner
"""

from pathlib import Path

import pytest
from dotenv import load_dotenv
from jiuwen.extension.workflow_node.end import End
from jiuwen.extension.workflow_node.flow_input import (
    FlowInput,
    USER_FIELDS,
    ExecutionStatus,
)
from jiuwen.extension.workflow_node.questioner import (
    Questioner,
    QuestionerConfig,
    FieldInfo,
)
from openjiuwen.core.common.logging import logger
from openjiuwen.core.workflow import (
    Workflow,
    WorkflowCard,
    Start,
    create_workflow_session,
)
from openjiuwen.core.workflow.base import WorkflowExecutionState


@pytest.fixture(scope="module", autouse=True)
def load_env():
    """加载环境变量"""
    env_file = Path(__file__).parent.parent / "memory_env"
    if env_file.exists():
        load_dotenv(env_file)
        logger.info(f"环境变量加载成功: {env_file}")


def test_component_imports() -> None:
    """测试组件是否可以正常导入"""


def test_flow_input_initialization() -> None:
    """测试 FlowInput 初始化"""
    flow_input_config = {
        USER_FIELDS: {
            "inputs": [
                {
                    "id": "city1",
                    "type": "string",
                    "required": True,
                    "description": "起始城市",
                },
                {
                    "id": "city2",
                    "type": "string",
                    "required": True,
                    "description": "目标城市",
                },
            ]
        }
    }

    flow_input = FlowInput(flow_input_config)
    status = flow_input.get_node_status()
    assert status == ExecutionStatus.START


def test_questioner_initialization() -> None:
    """测试 Questioner 初始化"""
    questioner_config = QuestionerConfig(
        model_name="Qwen/Qwen3-32B",
        model_type="SiliconFlow",
        question_content="您对这个结果满意吗？",
        key_fields=[
            FieldInfo(
                field_name="satisfaction",
                description="满意度",
                cn_field_name="满意度",
                type="string",
                required=True,
            ),
            FieldInfo(
                field_name="feedback",
                description="反馈意见",
                cn_field_name="反馈意见",
                type="string",
                required=False,
            ),
        ],
    )

    questioner = Questioner(questioner_config)
    assert questioner.config is not None
    assert len(questioner.config.key_fields) == 2


@pytest.mark.asyncio
async def test_workflow_creation() -> None:
    """测试工作流创建"""
    workflow = Workflow(
        card=WorkflowCard(
            id="flow_input_questioner_test",
            name="FlowInput + Questioner 测试",
            version="1.0.0",
        )
    )

    workflow.set_start_comp("start", Start(), inputs_schema={"initial": "${initial}"})

    flow_input_config = {
        USER_FIELDS: {
            "inputs": [
                {
                    "id": "city1",
                    "type": "string",
                    "required": True,
                    "description": "起始城市",
                },
                {
                    "id": "city2",
                    "type": "string",
                    "required": True,
                    "description": "目标城市",
                },
            ]
        }
    }
    flow_input = FlowInput(flow_input_config)
    workflow.add_workflow_comp(
        "flow_input",
        flow_input,
        inputs_schema={"initial": "${start.initial}"},
    )

    end = End({"response_template": "测试完成！输入: {{result}}"})
    workflow.set_end_comp(
        "end",
        end,
        inputs_schema={
            "city1": "${flow_input.userFields.city1}",
            "city2": "${flow_input.userFields.city2}",
        },
    )

    workflow.add_connection("start", "flow_input")
    workflow.add_connection("flow_input", "end")

    assert workflow.card.id == "flow_input_questioner_test"
    assert workflow.card.name == "FlowInput + Questioner 测试"


@pytest.mark.skip(reason="需要配置真实 Model ")
@pytest.mark.asyncio
async def test_complete_workflow_with_mock() -> None:
    """构建完整的工作流（使用模拟的 MCP 工具）"""
    from openjiuwen.core.workflow.components.component import WorkflowComponent
    from openjiuwen.core.session.node import Session
    from openjiuwen.core.context_engine import ModelContext
    from typing import Dict, Any

    class MockMapTool(WorkflowComponent):
        """模拟地图工具"""

        def __init__(self, tool_name: str):
            super().__init__()
            self.tool_name = tool_name

        async def invoke(
            self, inputs: Dict[str, Any], session: Session, context: ModelContext
        ) -> Dict[str, Any]:
            if self.tool_name == "get_location":
                address = inputs.get("address", "")
                mock_locations = {
                    "北京": {
                        "lat": 39.9042,
                        "lon": 116.4074,
                        "city": "北京",
                        "country": "中国",
                    },
                    "上海": {
                        "lat": 31.2304,
                        "lon": 121.4737,
                        "city": "上海",
                        "country": "中国",
                    },
                    "广州": {
                        "lat": 23.1291,
                        "lon": 113.2644,
                        "city": "广州",
                        "country": "中国",
                    },
                    "深圳": {
                        "lat": 22.5431,
                        "lon": 114.0579,
                        "city": "深圳",
                        "country": "中国",
                    },
                }
                if address in mock_locations:
                    return {
                        "success": True,
                        "address": address,
                        **mock_locations[address],
                    }
                return {"success": False, "error": f"未找到地址: {address}"}

            elif self.tool_name == "calculate_distance":
                address1 = inputs.get("address1", "")
                address2 = inputs.get("address2", "")
                return {
                    "success": True,
                    "address1": address1,
                    "address2": address2,
                    "distance_km": 1234.56,
                    "location1": {"lat": 39.9042, "lon": 116.4074},
                    "location2": {"lat": 31.2304, "lon": 121.4737},
                    "response": f"{address1} 到 {address2} 的距离是 1234.56 公里。",
                }

            return {"success": False, "error": "未知工具"}

    workflow = Workflow(
        card=WorkflowCard(
            id="flow_input_map_questioner_complete",
            name="完整工作流: FlowInput + 地图 MCP + Questioner",
            version="1.0.0",
        )
    )

    workflow.set_start_comp("start", Start(), inputs_schema={"initial": "${initial}"})

    flow_input_config = {
        USER_FIELDS: {
            "inputs": [
                {
                    "id": "city1",
                    "type": "string",
                    "required": True,
                    "description": "起始城市",
                },
                {
                    "id": "city2",
                    "type": "string",
                    "required": True,
                    "description": "目标城市",
                },
            ]
        }
    }
    flow_input = FlowInput(flow_input_config)
    workflow.add_workflow_comp(
        "flow_input0",
        flow_input,
        inputs_schema={"initial": ""},
    )

    workflow.add_workflow_comp(
        "flow_input1",
        flow_input,
        inputs_schema={"initial": "${start.initial}"},
    )

    tool_comp1 = MockMapTool("get_location")
    workflow.add_workflow_comp(
        "get_loc1",
        tool_comp1,
        inputs_schema={"address": "${flow_input1.userFields.city1}"},
    )

    tool_comp2 = MockMapTool("get_location")
    workflow.add_workflow_comp(
        "get_loc2",
        tool_comp2,
        inputs_schema={"address": "${flow_input1.userFields.city2}"},
    )

    tool_comp3 = MockMapTool("calculate_distance")
    workflow.add_workflow_comp(
        "calc_dist",
        tool_comp3,
        inputs_schema={
            "address1": "${flow_input1.userFields.city1}",
            "address2": "${flow_input1.userFields.city2}",
        },
    )

    questioner_config = QuestionerConfig(
        model_name="Qwen/Qwen3-32B",
        model_type="SiliconFlow",
        question_content="您对这个距离计算结果满意吗？是否需要其他帮助？",
        key_fields=[
            FieldInfo(
                field_name="satisfaction",
                description="满意度",
                cn_field_name="满意度",
                type="string",
                required=True,
            ),
            FieldInfo(
                field_name="feedback",
                description="反馈意见",
                cn_field_name="反馈意见",
                type="string",
                required=False,
            ),
        ],
    )
    questioner = Questioner(questioner_config)
    workflow.add_workflow_comp(
        "questioner1",
        questioner,
        inputs_schema={"query": "${calc_dist.response}"},
    )

    workflow.add_workflow_comp(
        "questioner2",
        questioner,
        inputs_schema={"query": "满意度10分"},
    )

    end = End()
    workflow.set_end_comp(
        "end",
        end,
        inputs_schema={
            "city1": "${flow_input1.userFields.city1}",
            "city2": "${flow_input1.userFields.city2}",
            "distance": "${calc_dist.distance_km}",
            "satisfaction": "${questioner2.satisfaction}",
        },
    )

    workflow.add_connection("start", "flow_input0")
    workflow.add_connection("flow_input0", "flow_input1")
    workflow.add_connection("flow_input1", "get_loc1")
    workflow.add_connection("flow_input1", "get_loc2")
    workflow.add_connection("get_loc1", "calc_dist")
    workflow.add_connection("get_loc2", "calc_dist")
    workflow.add_connection("calc_dist", "questioner1")
    workflow.add_connection("questioner1", "questioner2")
    workflow.add_connection("questioner2", "end")

    result = await workflow.invoke(
        {"initial": "city1:北京\ncity2:上海"}, create_workflow_session()
    )
    assert result is not None
    assert result.state == WorkflowExecutionState.COMPLETED
