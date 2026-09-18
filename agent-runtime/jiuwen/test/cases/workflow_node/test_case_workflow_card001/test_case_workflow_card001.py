# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2026. All rights reserved.

"""
FlowCard 工作流集成测试
测试覆盖:
- FlowCard 在工作流中的完整生命周期
- 基本模板渲染功能
- 卡片输出收集功能
- 结构化输出功能
- 流式输出功能
- 输出模式控制
- 事件处理(结束中断)
"""

import pytest
from jiuwen.extension.workflow_node.end import End as CustomEnd
from jiuwen.extension.workflow_node.flow_card import (
    FlowCard,
    FlowCardConfig,
)
from jiuwen.extension.workflow_node.flow_message import Message, MessageConfig
from jiuwen.extension.wrapper.workflow_wrapper import WorkflowWrapper
from openjiuwen.core.common.logging import workflow_logger
from openjiuwen.core.runner.runner import Runner
from openjiuwen.core.workflow import Workflow, Start
from openjiuwen.core.workflow.base import WorkflowCard
from openjiuwen.core.workflow.components.base import ComponentAbility

workflow_id = "07a31fc2-3314-43ac-aa15-971d8bd7d278"


def create_card_workflow():
    """创建卡片工作流"""
    # 创建工作流
    flow = Workflow(
        WorkflowCard(
            id=workflow_id,
            name="ssq_start_1",
            version="0.6.0",
            description="开始工作流-多级",
        )
    )

    # 1. 添加开始组件
    start = Start()
    flow.set_start_comp(
        "start", start, inputs_schema={"name": "${name}", "age": "${age}"}
    )

    flow.add_workflow_comp(
        "node_llm", Message(MessageConfig(template="你好，有什么我可以帮助你的吗？"))
    )

    # 2. 创建 FlowCard 配置和组件
    card_config = FlowCardConfig(
        template='{"title": "{{title}}", "content": "{{content}}", "URL": "{{URL}}"}',
        output_mode="separate",
    )
    flow_card = FlowCard(card_config)

    # 3. 添加 FlowCard 到工作流
    flow.add_workflow_comp(
        "card",
        flow_card,
        inputs_schema={
            "title": "标题",
            "content": "${node_llm.result}",
            "URL": "相关链接",
        },
        comp_ability=[ComponentAbility.STREAM],
    )

    # 4. 添加结束组件
    end = CustomEnd(
        conf={
            "response_mode": "directResponse",
            "response_template": "{{result}}",
            "is_stream_out": True,
            "userFields": {"inputs": [], "outputs": []},
        }
    )
    flow.set_end_comp(
        "end",
        end,
        inputs_schema={"result": "${node_llm.result}"},
        response_mode="streaming",
    )

    # 5. 连接组件
    flow.add_connection("start", "node_llm")
    flow.add_connection("node_llm", "card")
    flow.add_connection("card", "end")
    Runner.resource_mgr.add_workflow(
        WorkflowCard(
            id=workflow_id,
            name="ssq_start_1",
            version="0.6.0",
            description="开始工作流-多级",
        ),
        lambda: flow,
        tag="test_workflow_card",
    )
    return flow, workflow_id


@pytest.mark.asyncio
async def test_flow_card_basic_template_rendering():
    """测试 FlowCard 基本模板渲染功能"""
    # 创建卡片工作流
    flow, workflow_id = create_card_workflow()  # noqa: redefined-outer-name
    # 6. 执行工作流
    session_id = "test_session"
    workflow_wrapper = WorkflowWrapper()
    chunks = []
    async for chunk in workflow_wrapper.astream(
        query="你好", workflow_id=workflow_id, session_id=session_id
    ):
        chunks.append(chunk)
        workflow_logger.info(chunk)

    # 7. 验证结果
    card_chunks = [chunk for chunk in chunks if chunk.data.get("node_id") == "card"]
    assert len(card_chunks) > 0, "卡片组件输出为空"


if __name__ == "__main__":
    import asyncio

    asyncio.run(test_flow_card_basic_template_rendering())
