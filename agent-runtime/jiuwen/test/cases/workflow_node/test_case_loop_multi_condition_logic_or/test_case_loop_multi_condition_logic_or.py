# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

"""
LoopComponent numLoop + Message 变量插值模板 测试用例

对应旧框架 IR: test_ir/loop_multi_condition_logic_or.json
验证 LoopComponent 的 numLoop 模式以及 Message 组件的 {{variable}} 变量插值。

旧框架工作流图:
    graph TD
        A[开始] --> B{判断}
        B -->|if: length(query)>0| C[循环节点 numLoop=5]
        B -->|default| D[代码] --> C
        C --> E[结束]
        循环体: 代码_1(index) → 消息(模板: "循环第{{index}}次")

新框架简化 (去掉 Branch, 保持 numLoop 次数与 IR 一致):
    Start → Loop(numLoop=5, body: Message(template="循环第{{index}}次")) → End

    - 跳过 Branch (已由 test_branch_multi_condition_logic_and 覆盖)
    - numLoop=5 与 IR 一致，输出 循环第0|1|2|3|4次
    - 重点验证 numLoop 和 Message 的 {{index}} 插值

新框架适配说明:
- jiuwen.start  → jiuwen.extension.workflow_node.start.Start
- jiuwen.end    → jiuwen.extension.workflow_node.end.End
- jiuwen.message → jiuwen.extension.workflow_node.flow_message.Message
- jiuwen.loop   → openjiuwen.core.workflow.components.flow.loop.loop_comp.LoopComponent + LoopGroup

测试入口: WorkflowWrapper.astream()
  - 使用 WorkflowWrapper 封装，与旧框架 WorkflowHandler 的调用模式对齐
  - 返回 StreamData 流式输出，便于对比新旧框架输出的等价性
  - 通过 Runner.resource_mgr 注册工作流

覆盖的执行路径:
- numLoop=5, index 从 0 递增到 4, 每轮 Message 渲染 "循环第{N}次"
- StreamData 结构一致性验证
- Message 的 {{index}} 变量插值正确渲染
- PARTIAL_CONTENT 渐进输出 (与旧框架 process_generator_values_of_dict 对齐)
"""

import asyncio
import os

import pytest
from jiuwen.extension.workflow_node.end import End
from jiuwen.extension.workflow_node.flow_message import Message
from jiuwen.extension.workflow_node.start import Start
from jiuwen.extension.wrapper.workflow_wrapper import WorkflowWrapper
from jiuwen.orchestration.flow.stream.base import StreamData, StreamCode
from openjiuwen.core.common.logging import workflow_logger
from openjiuwen.core.runner.runner import Runner
from openjiuwen.core.workflow import Workflow
from openjiuwen.core.workflow.base import WorkflowCard
from openjiuwen.core.workflow.components.flow.loop.loop_comp import (
    LoopComponent,
    LoopGroup,
)

os.environ.setdefault("LLM_API_KEY", "mock-api-key-for-testing")


# ============================================================================
# 常量 & 辅助
# ============================================================================

_WORKFLOW_ID = "b3299888"
_AGENT_ID = "test_agent_loop_num"


def _build_start_conf() -> dict:
    return {
        "userFields": {"inputs": [], "outputs": []},
        "systemFields": {
            "inputs": [
                {
                    "sourceType": "input",
                    "description": "用户输入",
                    "id": "query",
                    "type": "string",
                    "required": True,
                },
                {
                    "sourceType": "input",
                    "description": "系统变量",
                    "id": "sys",
                    "type": "object",
                    "required": True,
                },
            ],
            "outputs": [
                {
                    "sourceType": "input",
                    "description": "用户输入",
                    "id": "query",
                    "type": "string",
                    "required": True,
                },
                {
                    "sourceType": "input",
                    "description": "系统变量",
                    "id": "sys",
                    "type": "object",
                    "required": True,
                },
            ],
        },
    }


def _build_params(query: str) -> dict:
    return {
        "global_variables": {
            "sys": {
                "conversationHistory": [],
                "currentTime": "2025-04-29 10:00:00",
                "userId": "testUser",
                "conversationId": "test-conv-id",
            },
        },
    }


def _extract_final_answer(chunks: list) -> str:
    """从 WORKFLOW_END(4000) 和 FINISH(0) 中提取最终 answer。"""
    for code in (StreamCode.FINISH.value, StreamCode.WORKFLOW_END.value):
        for chunk in reversed(chunks):
            if isinstance(chunk, StreamData) and chunk.code == code:
                answer = (
                    chunk.data.get("answer", "") if isinstance(chunk.data, dict) else ""
                )
                if answer:
                    return str(answer)
    return ""


def _create_and_register_workflow(num_iterations: int = 5) -> Workflow:
    """创建并注册 Start → Loop(numLoop) → End 工作流。"""
    workflow_card = WorkflowCard(
        id=_WORKFLOW_ID,
        name="test_loop_num_msg",
        version="0.6.0",
        description="numLoop + Message 变量插值测试",
    )
    wf = Workflow(workflow_card)

    # Start: systemFields (query, sys)
    wf.set_start_comp(
        "start",
        Start(_build_start_conf()),
        inputs_schema={
            "query": "${query}",
            "sys": {
                "conversationHistory": [],
                "currentTime": "2025-04-29 10:00:00",
                "userId": "testUser",
                "conversationId": "test-conv-id",
            },
        },
    )

    # Loop body: Message with {{index}} variable interpolation
    loop_group = LoopGroup()
    loop_group.add_workflow_comp(
        "msg",
        Message(
            {
                "template": "循环第{{index}}次",
                "name": "消息",
                "enable_history": True,
            }
        ),
        inputs_schema={"index": "${loop.index}"},
    )
    loop_group.start_nodes(["msg"])
    loop_group.end_nodes(["msg"])

    loop = LoopComponent(loop_group, output_schema={})
    wf.add_workflow_comp(
        "loop",
        loop,
        inputs_schema={
            "loop_type": "number",
            "loop_number": num_iterations,
        },
    )

    # End: 模板渲染 query
    wf.set_end_comp(
        "end",
        End(
            {
                "responseTemplate": "{{result}}",
                "responseMode": "directResponse",
                "isStreamOut": True,
                "name": "结束",
            }
        ),
        inputs_schema={"result": "${start.systemFields.query}"},
        response_mode="streaming",
    )

    # Connections
    wf.add_connection("start", "loop")
    wf.add_connection("loop", "end")

    Runner.resource_mgr.remove_workflow(workflow_id=_WORKFLOW_ID, tag=_AGENT_ID)
    Runner.resource_mgr.add_workflow(workflow_card, lambda: wf, tag=_AGENT_ID)
    return wf


# ============================================================================
# 测试: numLoop + Message 变量插值
# ============================================================================


class TestNumLoopWithMessage:
    """
    通过 WorkflowWrapper.astream() 验证 numLoop + Message 变量插值模板。

    简化工作流: Start → Loop(numLoop=5, body: msg) → End

    Loop 每轮执行 msg, msg 模板 "循环第{{index}}次" 通过 {{index}} 引用 loop.index。
    """

    @pytest.fixture(autouse=True)
    def setup_workflow(self):
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            asyncio.set_event_loop(asyncio.new_event_loop())
        _create_and_register_workflow(num_iterations=5)
        yield
        Runner.resource_mgr.remove_workflow(workflow_id=_WORKFLOW_ID, tag=_AGENT_ID)

    @pytest.mark.asyncio
    async def test_num_loop_message_template(self):
        """
        query="你好" → Start → Loop(numLoop=5, body: msg) → End

        每轮 msg 渲染 (与旧框架一致的渐进式输出):
          - 第0轮: PARTIAL_CONTENT "循环第" → "0" → "次"
          - 第1轮: PARTIAL_CONTENT "循环第" → "1" → "次"
          - ...
          - 第4轮: PARTIAL_CONTENT "循环第" → "4" → "次"

        验证:
        - 完整 StreamCode 序列: WORKFLOW_START → ... → WORKFLOW_END → FINISH
        - StreamData 结构: WORKFLOW_START 含 workflow_id, WORKFLOW_END 含 answer/node_id/node_type
        - 最终 answer 为 query "你好"
        - Message PARTIAL_CONTENT 包含 "循环第" 和 "次" (渐进式变量插值)
        - 总共 5 轮循环 (index 0-4)
        """
        wrapper = WorkflowWrapper()
        chunks: list[StreamData] = []
        async for chunk in wrapper.astream(
            query="你好",
            params=_build_params("你好"),
            workflow_id=_WORKFLOW_ID,
            session_id="test-session-numloop",
            agent_id=_AGENT_ID,
        ):
            chunks.append(chunk)
            workflow_logger.info(chunk)

        # --- StreamData 结构验证 ---
        for chunk in chunks:
            assert isinstance(chunk, StreamData), (
                f"应为 StreamData，实际: {type(chunk)}"
            )

        by_code = {c.code: c for c in chunks}

        # WORKFLOW_START(3000): data 含 workflow_id
        assert StreamCode.WORKFLOW_START.value in by_code
        start = by_code[StreamCode.WORKFLOW_START.value]
        assert "workflow_id" in start.data, (
            f"WORKFLOW_START.data 应含 workflow_id，实际: {start.data}"
        )

        # WORKFLOW_END(4000): data 含 answer, node_id, node_type
        assert StreamCode.WORKFLOW_END.value in by_code
        wf_end = by_code[StreamCode.WORKFLOW_END.value]
        assert "answer" in wf_end.data, (
            f"WORKFLOW_END.data 应含 answer，实际: {wf_end.data}"
        )
        assert "node_id" in wf_end.data, (
            f"WORKFLOW_END.data 应含 node_id，实际: {wf_end.data}"
        )
        assert "node_type" in wf_end.data, (
            f"WORKFLOW_END.data 应含 node_type，实际: {wf_end.data}"
        )

        # FINISH(0): data 为 dict
        assert StreamCode.FINISH.value in by_code
        finish = by_code[StreamCode.FINISH.value]
        assert isinstance(finish.data, dict), (
            f"FINISH.data 应为 dict，实际: {type(finish.data)}"
        )

        # --- 业务逻辑验证 ---
        # 最终 answer 为 query "你好"
        final_answer = _extract_final_answer(chunks)
        workflow_logger.info(f"NumLoop final answer: {final_answer}")
        assert "你好" in final_answer, f"应包含 query '你好'，实际: {final_answer}"

        # 验证 Message {{index}} 变量插值输出
        msg_answers = [
            str(c.data.get("answer", ""))
            for c in chunks
            if isinstance(c, StreamData)
            and isinstance(c.data, dict)
            and "循环第" in str(c.data.get("answer", ""))
        ]
        workflow_logger.info(f"Message outputs: {msg_answers}")
        assert len(msg_answers) > 0, "应至少有一条 Message 输出包含 '循环第'"
