# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

"""
Aggregate (变量聚合) 组件 WorkflowWrapper 测试用例

对应旧框架 IR: test_ir/only_aggregation_2groups_2params.json
验证 Aggregate 通过 WorkflowWrapper.astream() 执行的输出与旧框架一致。

旧框架工作流图:
    graph TD
        A[开始 node_start] --> B[变量聚合 node_aggregation]
        B --> C[结束 node_end]

Aggregate 配置:
    - mode: first-non-null
    - group1: [group1_1, group1_2] ← param1, param2
    - group2: [group2_1, group2_2] ← param1, param2

End 模板: "变量聚合组件输出: result1: {{result1}}, result2: {{result2}}"

新框架适配说明:
- jiuwen.start      → jiuwen.extension.workflow_node.start.Start
- jiuwen.end        → jiuwen.extension.workflow_node.end.End
- jiuwen.aggregation → jiuwen.extension.workflow_node.flow_aggregate.Aggregate

测试入口: WorkflowWrapper.astream()
  - 使用 WorkflowWrapper 封装，与旧框架 WorkflowHandler 的调用模式对齐
  - 返回 StreamData 流式输出，便于对比新旧框架输出的等价性
  - 通过 Runner.resource_mgr 注册工作流

输出结构 (与旧框架一致的 StreamData):
  WORKFLOW_START(3000) → PARTIAL_CONTENT(1206) → MESSAGE_END(5000)
  → CONTROLLER_INTERMEDIATE_MESSAGE(7000) → WORKFLOW_END(4000) → FINISH(0)

覆盖的执行路径:
- param1="abc", param2="123" → first-non-null → group1=abc, group2=abc
- param1="", param2="123" → first-non-null 空值回退 → group1=123, group2=123
- StreamData 结构一致性验证
"""

import asyncio
import os

import pytest
from jiuwen.extension.workflow_node.end import End
from jiuwen.extension.workflow_node.flow_aggregate import Aggregate
from jiuwen.extension.workflow_node.start import Start
from jiuwen.extension.wrapper.workflow_wrapper import WorkflowWrapper
from jiuwen.orchestration.flow.stream.base import StreamData, StreamCode
from openjiuwen.core.common.logging import workflow_logger
from openjiuwen.core.runner.runner import Runner
from openjiuwen.core.workflow import Workflow
from openjiuwen.core.workflow.base import WorkflowCard

os.environ.setdefault("LLM_API_KEY", "mock-api-key-for-testing")


# ============================================================================
# 常量 & 辅助
# ============================================================================

_WORKFLOW_ID = "4af0ad3e"
_AGENT_ID = "test_agent_aggregation"


def _build_start_conf() -> dict:
    return {
        "userFields": {
            "inputs": [
                {
                    "sourceType": "null",
                    "description": "param1",
                    "id": "param1",
                    "type": "string",
                    "required": True,
                },
                {
                    "sourceType": "null",
                    "description": "param2",
                    "id": "param2",
                    "type": "string",
                    "required": True,
                },
            ],
            "outputs": [
                {
                    "sourceType": "null",
                    "description": "param1",
                    "id": "param1",
                    "type": "string",
                    "required": True,
                },
                {
                    "sourceType": "null",
                    "description": "param2",
                    "id": "param2",
                    "type": "string",
                    "required": True,
                },
            ],
        },
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


def _create_and_register_workflow(
    wf_id: str,
    param1: str,
    param2: str,
) -> Workflow:
    """创建并注册 Start → Aggregate → End 工作流。"""
    workflow_card = WorkflowCard(
        id=wf_id,
        name="test_flow_aggregation",
        version="0.6.0",
        description="Aggregate 组件测试",
    )
    wf = Workflow(workflow_card)

    # Start: 提供 param1/param2(用户字段) + query/sys(系统字段)
    wf.set_start_comp(
        "start",
        Start(_build_start_conf()),
        inputs_schema={
            "query": "${query}",
            "param1": param1,
            "param2": param2,
            "sys": {
                "conversationHistory": [],
                "currentTime": "2025-04-29 10:00:00",
                "userId": "testUser",
                "conversationId": "test-conv-id",
            },
        },
    )

    # Aggregate: first-non-null 模式, 2 个 group
    aggregate = Aggregate(
        {
            "mode": "first-non-null",
            "groups": {
                "group1": ["group1_1", "group1_2"],
                "group2": ["group2_1", "group2_2"],
            },
        }
    )
    wf.add_workflow_comp(
        "aggregate",
        aggregate,
        inputs_schema={
            "group1_1": "${start.userFields.param1}",
            "group1_2": "${start.userFields.param2}",
            "group2_1": "${start.userFields.param1}",
            "group2_2": "${start.userFields.param2}",
        },
    )

    # End: 模板渲染 Aggregate 的输出
    wf.set_end_comp(
        "end",
        End(
            {
                "responseTemplate": "变量聚合组件输出: result1: {{result1}}, result2: {{result2}}",
                "responseMode": "directResponse",
                "isStreamOut": True,
                "name": "结束",
            }
        ),
        inputs_schema={
            "result1": "${aggregate.userFields.group1}",
            "result2": "${aggregate.userFields.group2}",
        },
        response_mode="streaming",
    )

    # Connections
    wf.add_connection("start", "aggregate")
    wf.add_connection("aggregate", "end")

    Runner.resource_mgr.remove_workflow(workflow_id=wf_id, tag=_AGENT_ID)
    Runner.resource_mgr.add_workflow(workflow_card, lambda: wf, tag=_AGENT_ID)
    return wf


# ============================================================================
# 测试: Aggregate 通过 WorkflowWrapper
# ============================================================================


class TestAggregationWithWorkflowWrapper:
    """
    通过 WorkflowWrapper.astream() 验证 Aggregate 组件在 first-non-null 模式下的行为。

    IR 工作流结构:
        Start(param1, param2) → Aggregate(first-non-null, 2 groups) → End

    Aggregate 配置:
        - group1: [group1_1←param1, group1_2←param2]
        - group2: [group2_1←param1, group2_2←param2]
    """

    @pytest.fixture(autouse=True)
    def setup_workflow(self):
        # 确保 asyncio 事件循环存在（Vertex.__init__ 中 asyncio.Future() 需要事件循环）
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            asyncio.set_event_loop(asyncio.new_event_loop())
        _create_and_register_workflow(_WORKFLOW_ID, param1="abc", param2="123")
        yield
        Runner.resource_mgr.remove_workflow(workflow_id=_WORKFLOW_ID, tag=_AGENT_ID)

    @pytest.mark.asyncio
    async def test_aggregation_first_non_null(self):
        """
        param1="abc", param2="123"
        → first-non-null("abc", "123") = "abc"
        → group1=abc, group2=abc

        验证:
        - 完整 StreamCode 序列: WORKFLOW_START → ... → WORKFLOW_END → FINISH
        - StreamData 结构: WORKFLOW_START 含 workflow_id, WORKFLOW_END 含 answer/node_id/node_type
        - 最终 answer 包含 "abc" (first-non-null 选取第一个非空值)
        """
        wrapper = WorkflowWrapper()
        chunks: list[StreamData] = []
        async for chunk in wrapper.astream(
            query="你好",
            params=_build_params("你好"),
            workflow_id=_WORKFLOW_ID,
            session_id="test-session-a",
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
        final_answer = _extract_final_answer(chunks)
        workflow_logger.info(f"Aggregation final answer: {final_answer}")
        assert "abc" in final_answer, (
            f"应包含 first-non-null 值 'abc'，实际: {final_answer}"
        )

    @pytest.mark.asyncio
    async def test_aggregation_fallback_to_second(self):
        """
        param1="", param2="123"
        → first-non-null("", "123") = "123" (空字符串被跳过)
        → group1=123, group2=123

        验证: 当第一个参数为空时，first-non-null 回退到第二个参数。
        """
        wf_id = "4af0ad3e_fb"
        _create_and_register_workflow(wf_id, param1="", param2="123")
        try:
            wrapper = WorkflowWrapper()
            chunks: list[StreamData] = []
            async for chunk in wrapper.astream(
                query="你好",
                params=_build_params("你好"),
                workflow_id=wf_id,
                session_id="test-session-fallback",
                agent_id=_AGENT_ID,
            ):
                chunks.append(chunk)
                workflow_logger.info(chunk)

            codes = [c.code for c in chunks if isinstance(c, StreamData)]
            assert StreamCode.FINISH.value in codes

            final_answer = _extract_final_answer(chunks)
            workflow_logger.info(f"Aggregation fallback answer: {final_answer}")
            assert "123" in final_answer, f"应包含回退值 '123'，实际: {final_answer}"
        finally:
            Runner.resource_mgr.remove_workflow(workflow_id=wf_id, tag=_AGENT_ID)
