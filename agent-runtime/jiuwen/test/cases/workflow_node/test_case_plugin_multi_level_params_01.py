# coding=utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.

"""
FlowApi 组件多层级参数工作流测试

完整工作流: Start -> FlowApi(Plugin) -> End

测试 JSON 工作流: test_case_plugin.multi_level_params_01.json
工作流结构:
    - node_start: 开始节点，提供 query 输入
    - node_plugin: 插件节点，调用 mock_plugin_multi_level_param API
                   流式输出: content(string), param(number), ext{abc(number), string_text(string)}
    - node_end: 结束节点，格式化输出流式结果

运行方式:
    pytest jiuwen/test/cases/workflow_node/test_flow_api_multi_level_params.py -v -s
"""

import os

import pytest
from jiuwen.extension.workflow_node.end import End
from jiuwen.extension.workflow_node.flow_api import FlowApi
from jiuwen.extension.workflow_node.start import Start
from jiuwen.extension.wrapper.workflow_wrapper import WorkflowWrapper
from openjiuwen.core.runner.runner import Runner
from openjiuwen.core.workflow import ComponentAbility
from openjiuwen.core.workflow import Workflow, WorkflowCard

USER_FIELDS = "userFields"
SYSTEM_FIELDS = "systemFields"

workflow_id = "faef2c9f-97d3-46fe-a9e9-561726c7c61a"
agent_id = "39a8026s-2181-446f-8cf1-2887e9403h7c"
session_id = "e02b3673-1683-4a99-83b6-ecce9426bf0b"
os.environ["CLOSE_URL_JUDGE_SWITCH"] = "true"


def _make_start_conf() -> dict:
    """Start 组件配置"""
    return {
        USER_FIELDS: {"inputs": [], "outputs": []},
        SYSTEM_FIELDS: {
            "inputs": [
                {
                    "sourceType": "input",
                    "description": "用户输入",
                    "id": "query",
                    "type": "string",
                    "required": True,
                }
            ],
            "outputs": [
                {
                    "sourceType": "input",
                    "description": "用户输入",
                    "id": "query",
                    "type": "string",
                    "required": True,
                }
            ],
        },
    }


def _make_flow_api_conf() -> dict:
    """FlowApi 组件 IR 配置（对应 JSON 中的 node_plugin）"""
    return {
        "id": "62458ae8-46fe-46fe-9e9-561726c7c888",
        "name": "xhw_stream",
        "description": "流式结果",
        "url": "http://127.0.0.1:5001/mock_plugin_multi_level_param",
        "method": "GET",
        "auth": {},
        "headers": {"Content-Type": "application/json"},
        "pluginDependency": {
            "paramsWrapper": {"outputList": False, "inputList": False}
        },
        "response": [
            {
                "name": "content",
                "description": "流式结果",
                "type": "string",
                "required": True,
            },
            {
                "name": "param",
                "description": "流式结果",
                "type": "number",
                "required": True,
            },
            {
                "name": "ext",
                "description": "流式结果",
                "type": "object",
                "required": True,
                "schema": [
                    {
                        "name": "abc",
                        "sourceType": "null",
                        "description": "流式结果",
                        "id": "abc",
                        "type": "number",
                        "required": True,
                    },
                    {
                        "name": "string_text",
                        "sourceType": "null",
                        "description": "流式结果",
                        "id": "string_text",
                        "type": "string",
                        "required": True,
                    },
                ],
            },
        ],
        USER_FIELDS: {
            "inputs": [],
            "outputs": [
                {
                    "sourceType": "null",
                    "description": "流式结果",
                    "id": "content",
                    "type": "string",
                    "required": True,
                },
                {
                    "sourceType": "null",
                    "description": "流式结果",
                    "id": "param",
                    "type": "number",
                    "required": True,
                },
                {
                    "sourceType": "null",
                    "description": "流式结果",
                    "id": "ext",
                    "type": "object",
                    "required": True,
                    "schema": [
                        {
                            "sourceType": "null",
                            "description": "流式结果",
                            "id": "abc",
                            "type": "number",
                            "required": True,
                        },
                        {
                            "sourceType": "null",
                            "description": "流式结果",
                            "id": "string_text",
                            "type": "string",
                            "required": True,
                        },
                    ],
                },
            ],
        },
        SYSTEM_FIELDS: {"inputs": [], "outputs": []},
        "arguments": [],
        "streaming": True,
    }


def _make_end_conf() -> dict:
    """End 组件配置（对应 JSON 中的 node_end）"""
    return {
        "responseMode": "directResponse",
        USER_FIELDS: {
            "inputs": [
                {
                    "sourceType": "ref",
                    "description": "最终输出",
                    "id": "content",
                    "type": "string",
                    "required": False,
                },
                {
                    "sourceType": "ref",
                    "description": "最终输出",
                    "id": "param",
                    "type": "number",
                    "required": False,
                },
                {
                    "sourceType": "ref",
                    "description": "流式结果",
                    "id": "ext",
                    "type": "object",
                    "required": True,
                    "schema": [
                        {
                            "name": "abc",
                            "sourceType": "null",
                            "description": "流式结果",
                            "id": "abc",
                            "type": "number",
                            "required": True,
                        },
                        {
                            "name": "string_text",
                            "sourceType": "null",
                            "description": "流式结果",
                            "id": "string_text",
                            "type": "string",
                            "required": True,
                        },
                    ],
                },
                {
                    "sourceType": "ref",
                    "description": "",
                    "id": "abc",
                    "type": "number",
                    "required": True,
                },
                {
                    "sourceType": "ref",
                    "description": "",
                    "id": "string_text",
                    "type": "string",
                    "required": True,
                },
            ],
            "outputs": [],
        },
        "responseTemplate": "【ext:{{ext}}】\n【ext.abc:{{abc}}】\n【ext.string_text:{{string_text}}】",
        SYSTEM_FIELDS: {"inputs": [], "outputs": []},
        "isStreamOut": True,
    }


def create_flow_api_multi_level_workflow() -> tuple[Workflow, str]:
    """
    创建 FlowApi 多层级参数工作流

    结构: start -> plugin -> end

    返回:
        Workflow: 工作流实例
        workflow_id: 工作流ID
    """
    workflow_card = WorkflowCard(
        id=workflow_id,
        name="flow_api_multi_level_params",
        version="0.6.0",
        description="FlowApi 多层级参数工作流测试",
    )
    wf = Workflow(workflow_card)

    wf.set_start_comp(
        "node_start",
        Start(_make_start_conf()),
        inputs_schema={
            "query": "${query}",
        },
    )

    wf.add_workflow_comp(
        "node_plugin",
        FlowApi(_make_flow_api_conf()),
        inputs_schema={},
        comp_ability=[ComponentAbility.STREAM],
    )

    wf.set_end_comp(
        "node_end",
        End(_make_end_conf()),
        stream_inputs_schema={
            "content": "${node_plugin.userFields.content}",
            "param": "${node_plugin.userFields.param}",
            "ext": "${node_plugin.userFields.ext}",
            "abc": "${node_plugin.userFields.ext.abc}",
            "string_text": "${node_plugin.userFields.ext.string_text}",
        },
        response_mode="streaming",
    )

    wf.add_connection("node_start", "node_plugin")
    wf.add_stream_connection("node_plugin", "node_end")

    Runner.resource_mgr.add_workflow(
        workflow_card,
        lambda card=workflow_card: wf,
        tag=agent_id,
    )

    return wf, workflow_id


def _build_context(conversation_history: list):
    """从对话历史构建 ModelContext"""
    from openjiuwen.core.context_engine.context.context import SessionModelContext
    from openjiuwen.core.context_engine.schema.config import ContextEngineConfig

    model_context = SessionModelContext(
        context_id=f"{workflow_id}_context",
        session_id=session_id,
        config=ContextEngineConfig(),
        history_messages=[],
        processors=[],
    )
    return model_context


@pytest.mark.asyncio
@pytest.mark.skip
async def test_flow_api_multi_level_params_workflow_stream():
    """
    测试 FlowApi 多层级参数工作流（使用 astream 方式）

    流程:
    1. 用户输入 query
    2. 开始节点 -> 传递 query
    3. 插件节点调用 http://127.0.0.1:5001/mock_plugin_multi_level_param API
    4. 输出参数 (content, param)
    5. 结束节点格式化输出
    """
    params = {
        "global_variables": {
            "sys": {
                "conversationHistory": [],
                "currentTime": "2024-09-24 14:44:41",
                "userId": "test_user",
                "conversationId": session_id,
            }
        },
        "conversation_history": [],
        "CONTROLLER_MODE_SWITCH": False,
    }

    workflow, wf_id = create_flow_api_multi_level_workflow()
    wrapper = WorkflowWrapper()
    chunks = []

    async for chunk in wrapper.astream(
        query="测试插件流式使出支持多层级参数配置",
        workflow_id=wf_id,
        session_id=session_id,
        agent_id=agent_id,
        params=params,
        context=_build_context([]),
    ):
        chunks.append(chunk)
        print(f"收到 chunk: {chunk}")

    assert len(chunks) > 0
    print(f"共收到 {len(chunks)} 个 chunk")

    has_finish = False
    for chunk in chunks:
        if hasattr(chunk, "code") and chunk.code in [0, 4000, "FINISH"]:
            has_finish = True
            break
    assert has_finish, "工作流应该正常结束"


if __name__ == "__main__":
    import asyncio

    async def main():
        await test_flow_api_multi_level_params_workflow_stream()

    asyncio.run(main())
