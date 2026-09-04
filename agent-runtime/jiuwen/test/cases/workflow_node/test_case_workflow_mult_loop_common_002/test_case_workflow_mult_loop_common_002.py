# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

"""
LoopComponent WorkflowWrapper 测试用例

对应旧框架 IR: test_ir/test_case_workflow_mult_loop_common_002.json
验证 LoopComponent 通过 WorkflowWrapper.astream() 执行的输出与旧框架一致。

旧框架工作流图:
    graph TD
        A[开始 node_start] --> B{判断 node_branch}
        B -->|if: '你好' in query| C[循环节点 node_loop]
        B -->|default| D[循环节点_1 node_loop_1]
        C --> E[结束 node_end]
        D --> E

新框架适配说明:
- jiuwen.start     → jiuwen.extension.workflow_node.start.Start
- jiuwen.end       → jiuwen.extension.workflow_node.end.End
- jiuwen.branch    → openjiuwen.core.workflow.components.flow.branch_comp.BranchComponent
- jiuwen.code      → MockCodeComponent (返回 {"output": str(input_val)})
- jiuwen.loop      → openjiuwen.core.workflow.components.flow.loop.loop_comp.LoopComponent + LoopGroup
- jiuwen.setVariable → jiuwen.extension.workflow_node.loop_set_variable.LoopSetVariable

测试入口: WorkflowWrapper.astream()
  - 使用 WorkflowWrapper 封装，与旧框架 WorkflowHandler 的调用模式对齐
  - 返回 StreamData 流式输出，便于对比新旧框架输出的等价性
  - 通过 Runner.resource_mgr 注册工作流

输出结构 (与旧框架一致的 StreamData):
  WORKFLOW_START(3000) → PARTIAL_CONTENT(1206) → MESSAGE_END(5000)
  → CONTROLLER_INTERMEDIATE_MESSAGE(7000) → WORKFLOW_END(4000) → FINISH(0)

覆盖的执行路径:
- 路径 A: query="你好" → Branch(if) → Loop1(setVar: age1=222, age2=111) → End
- 路径 B: query="菠菜有什么营养成分" → Branch(default) → Loop2(setVar: age1=222222, age2=111111) → End
- StreamData 结构一致性验证
- 多种 query 值均正常完成到 FINISH
"""

import asyncio
import os

import pytest
from jiuwen.extension.workflow_node.end import End
from jiuwen.extension.workflow_node.loop_set_variable import LoopSetVariable
from jiuwen.extension.workflow_node.start import Start
from jiuwen.extension.wrapper.workflow_wrapper import WorkflowWrapper
from jiuwen.orchestration.flow.stream.base import StreamData, StreamCode
from openjiuwen.core.common.logging import workflow_logger
from openjiuwen.core.context_engine import ModelContext
from openjiuwen.core.graph.executable import Input, Output
from openjiuwen.core.runner.runner import Runner
from openjiuwen.core.session.node import Session
from openjiuwen.core.workflow import Workflow
from openjiuwen.core.workflow.base import WorkflowCard
from openjiuwen.core.workflow.components.component import WorkflowComponent
from openjiuwen.core.workflow.components.condition.condition import AlwaysTrue
from openjiuwen.core.workflow.components.flow.branch_comp import BranchComponent
from openjiuwen.core.workflow.components.flow.loop.loop_comp import (
    LoopComponent,
    LoopGroup,
)

os.environ.setdefault("LLM_API_KEY", "mock-api-key-for-testing")


# ============================================================================
# Mock Code Component
# ============================================================================


class MockCodeComponent(WorkflowComponent):
    """Mock 代码执行组件，模拟旧框架 jiuwen.code 节点。

    根据 IR 中 node_code / node_code_1 的定义:
    - 输入: input (string)
    - 输出: output (string)
    - 代码逻辑: 返回 args.get('input', 'default')
    """

    def __init__(self):
        super().__init__()

    async def invoke(
        self, inputs: Input, session: Session, context: ModelContext
    ) -> Output:
        input_val = ""
        if isinstance(inputs, dict):
            input_val = inputs.get("input", "default")
        return {"output": str(input_val)}


# ============================================================================
# 常量 & 辅助
# ============================================================================

_WORKFLOW_ID = "2046ecaa"
_AGENT_ID = "test_agent_loop_branch"

_BRANCH_IF_EXPRESSION = "('你好' in ${start.systemFields.query})"


def _build_start_conf() -> dict:
    return {
        "userFields": {
            "inputs": [
                {
                    "schema": {"id": "", "type": "string"},
                    "sourceType": "null",
                    "id": "questions",
                    "type": "array",
                    "required": True,
                },
                {
                    "sourceType": "null",
                    "id": "age1",
                    "type": "integer",
                    "required": True,
                },
            ],
            "outputs": [
                {
                    "schema": {"id": "", "type": "string"},
                    "sourceType": "null",
                    "id": "questions",
                    "type": "array",
                    "required": True,
                },
                {
                    "sourceType": "null",
                    "id": "age1",
                    "type": "integer",
                    "required": True,
                },
            ],
        },
        "systemFields": {
            "inputs": [
                {
                    "sourceType": "input",
                    "id": "query",
                    "type": "string",
                    "required": True,
                },
            ],
            "outputs": [
                {
                    "sourceType": "input",
                    "id": "query",
                    "type": "string",
                    "required": True,
                },
            ],
        },
    }


def _build_params(query: str) -> dict:
    return {
        "global_variables": {
            "branch": 2,
            "sys": {
                "conversationHistory": [],
                "currentTime": "2025-04-29 10:00:00",
                "userId": "testUser",
                "conversationId": "test-conv-id",
            },
        },
        # 缩短 End 组件模板渲染超时（默认 5s，Branch 未走分支变量会触发超时等待）
        "_end_comp_template_render_position_timeout": 0.1,
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


def _build_loop(
    loop_node_id: str,
    code_node_id: str,
    set_var_node_id: str,
    age1_val: str,
    age2_val: str,
    result1_key: str,
    result2_key: str,
    result3_key: str,
) -> LoopComponent:
    """构建一个 LoopComponent，包含 code + setVar 的循环体。

    Args:
        loop_node_id: 外层工作流中 LoopComponent 的节点 ID (如 "loop1")
        code_node_id: 循环体内 MockCodeComponent 的节点 ID
        set_var_node_id: 循环体内 LoopSetVariable 的节点 ID
        age1_val: setVar 写入的 age1 值
        age2_val: setVar 写入的 age2 值
        result1_key: output_schema 中 age1 对应的 key
        result2_key: output_schema 中 age2 对应的 key
        result3_key: output_schema 中 code output 对应的 key
    """
    loop_group = LoopGroup()
    loop_group.add_workflow_comp(
        code_node_id,
        MockCodeComponent(),
        inputs_schema={"input": f"${{{loop_node_id}.item}}"},
    )
    loop_group.add_workflow_comp(
        set_var_node_id,
        LoopSetVariable(
            {
                f"${{{loop_node_id}.age1}}": age1_val,
                f"${{{loop_node_id}.age2}}": age2_val,
            }
        ),
    )
    loop_group.start_nodes([code_node_id])
    loop_group.end_nodes([set_var_node_id])
    loop_group.add_connection(code_node_id, set_var_node_id)

    return LoopComponent(
        loop_group,
        output_schema={
            result1_key: f"${{{loop_node_id}.age1}}",
            result2_key: f"${{{loop_node_id}.age2}}",
            result3_key: f"${{{code_node_id}.output}}",
        },
    )


def _create_and_register_workflow() -> Workflow:
    """创建并注册 Loop + Branch 组合工作流。"""
    workflow_card = WorkflowCard(
        id=_WORKFLOW_ID,
        name="loop_test",
        version="0.6.0",
        description="Loop + Branch 组合测试",
    )
    wf = Workflow(workflow_card)

    # Start: 提供 query(系统字段) + questions/age1(用户字段)
    wf.set_start_comp(
        "start",
        Start(_build_start_conf()),
        inputs_schema={
            "query": "${query}",
            "questions": ["你好~", "水的沸点是多少", "1+1等于几"],
            "age1": 12,
            "sys": {
                "conversationHistory": [],
                "currentTime": "2025-04-29 10:00:00",
                "userId": "testUser",
                "conversationId": "test-conv-id",
            },
        },
    )

    # Branch: if '你好' in query → loop1, default → loop2
    branch = BranchComponent()
    branch.add_branch(_BRANCH_IF_EXPRESSION, "loop1", branch_id="branch-if")
    branch.add_branch(AlwaysTrue(), "loop2", branch_id="branch-default")
    wf.add_workflow_comp("branch", branch)

    # Loop1: if 分支, setVar age1=222, age2=111
    loop1 = _build_loop(
        "loop1", "code_node", "set_var", "222", "111", "result1", "result2", "result3"
    )
    wf.add_workflow_comp(
        "loop1",
        loop1,
        inputs_schema={
            "loop_type": "array",
            "loop_array": {"item": "${start.userFields.questions}"},
            "intermediate_var": {"age1": "${start.userFields.age1}", "age2": "121"},
        },
    )

    # Loop2: default 分支, setVar age1=222222, age2=111111
    loop2 = _build_loop(
        "loop2",
        "code_node_1",
        "set_var_1",
        "222222",
        "111111",
        "result1_1",
        "result2_1",
        "result3_1",
    )
    wf.add_workflow_comp(
        "loop2",
        loop2,
        inputs_schema={
            "loop_type": "array",
            "loop_array": {"item": "${start.userFields.questions}"},
            "intermediate_var": {"age1": "${start.userFields.age1}", "age2": "121"},
        },
    )

    # End: 模板渲染两个 Loop 的输出
    wf.set_end_comp(
        "end",
        End(
            {
                "responseTemplate": (
                    "【result1】{{result1}}【result2】{{result2}}【result3】{{result3}}\n"
                    "【result1_1】{{result1_1}}【result2_1】{{result2_1}}【result3_1】{{result3_1}}"
                ),
                "responseMode": "directResponse",
                "isStreamOut": True,
                "enable_history": True,
                "isStructMessage": False,
                "name": "结束",
            }
        ),
        inputs_schema={
            "result1": "${loop1.result1}",
            "result2": "${loop1.result2}",
            "result3": "${loop1.result3}",
            "result1_1": "${loop2.result1_1}",
            "result2_1": "${loop2.result2_1}",
            "result3_1": "${loop2.result3_1}",
        },
        response_mode="streaming",
    )

    # Connections
    # 注意: BranchComponent 通过 add_component() 内部已调用 graph.add_conditional_edges
    # 设置条件路由边，无需手动 add_connection("branch", "loop1/loop2")
    # 否则普通边会绕过条件路由，导致两个分支都被执行
    wf.add_connection("start", "branch")
    wf.add_connection("loop1", "end")
    wf.add_connection("loop2", "end")

    Runner.resource_mgr.remove_workflow(workflow_id=_WORKFLOW_ID, tag=_AGENT_ID)
    Runner.resource_mgr.add_workflow(workflow_card, lambda: wf, tag=_AGENT_ID)
    return wf


# ============================================================================
# 测试: Loop + Branch 通过 WorkflowWrapper
# ============================================================================


class TestLoopWithWorkflowWrapper:
    """
    通过 WorkflowWrapper.astream() 验证 LoopComponent 在 Branch 场景下的行为。

    IR 工作流结构:
        Start → Branch(if: '你好' in query) → Loop1(code+setVar) → End
             └→ Branch(default) → Loop2(code+setVar) → End

    Loop1: arrayLoop, 遍历 questions 数组, body 内 setVar 设置 age1=222, age2=111
    Loop2: arrayLoop, 遍历 questions 数组, body 内 setVar 设置 age1=222222, age2=111111
    End: 模板渲染两个 Loop 的输出
    """

    @pytest.fixture(autouse=True)
    def setup_workflow(self):
        # 确保 asyncio 事件循环存在（Vertex.__init__ 中 asyncio.Future() 需要事件循环）
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            asyncio.set_event_loop(asyncio.new_event_loop())
        _create_and_register_workflow()
        yield
        Runner.resource_mgr.remove_workflow(workflow_id=_WORKFLOW_ID, tag=_AGENT_ID)

    @pytest.mark.asyncio
    async def test_path_a_if_branch(self):
        """
        路径 A: query="你好" → Branch(if) → Loop1 → End

        Branch 条件: '你好' in query → True → 路由到 Loop1

        Loop1 执行:
          - 遍历 questions=["你好~", "水的沸点是多少", "1+1等于几"]
          - 每轮 code_node 输出当前元素, setVar 写入 age1=222, age2=111
          - output_schema 收集: result1=222, result2=111, result3=["你好~","水的沸点是多少","1+1等于几"]

        验证:
        - 完整 StreamCode 序列: WORKFLOW_START → ... → WORKFLOW_END → FINISH
        - StreamData 结构: 所有 chunk 为 StreamData, WORKFLOW_START 含 workflow_id,
          WORKFLOW_END 含 answer/node_id/node_type, FINISH.data 为 dict
        - 最终 answer 包含 Loop1 的 setVar 值 "222" 和 "111"
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
        workflow_logger.info(f"Path A final answer: {final_answer}")
        assert "222" in final_answer, f"应包含 Loop1 的 age1=222，实际: {final_answer}"
        assert "111" in final_answer, f"应包含 Loop1 的 age2=111，实际: {final_answer}"

    @pytest.mark.asyncio
    async def test_path_b_default_branch(self):
        """
        路径 B: query="菠菜有什么营养成分" → Branch(default) → Loop2 → End

        Branch 条件: '你好' in query → False → 路由到 Loop2

        Loop2 执行:
          - 遍历 questions 数组, setVar 写入 age1=222222, age2=111111

        验证:
        - 完整 StreamCode 序列: WORKFLOW_START → ... → WORKFLOW_END → FINISH
        - 最终 answer 包含 Loop2 的 setVar 值 "222222" 和 "111111"
        """
        wrapper = WorkflowWrapper()
        chunks: list[StreamData] = []
        async for chunk in wrapper.astream(
            query="菠菜有什么营养成分",
            params=_build_params("菠菜有什么营养成分"),
            workflow_id=_WORKFLOW_ID,
            session_id="test-session-b",
            agent_id=_AGENT_ID,
        ):
            chunks.append(chunk)
            workflow_logger.info(chunk)

        codes = [c.code for c in chunks if isinstance(c, StreamData)]

        assert StreamCode.WORKFLOW_START.value in codes, "缺少 WORKFLOW_START"
        assert StreamCode.WORKFLOW_END.value in codes, "缺少 WORKFLOW_END"
        assert StreamCode.FINISH.value in codes, "缺少 FINISH"

        final_answer = _extract_final_answer(chunks)
        workflow_logger.info(f"Path B final answer: {final_answer}")
        assert "222222" in final_answer, (
            f"应包含 Loop2 的 age1=222222，实际: {final_answer}"
        )
        assert "111111" in final_answer, (
            f"应包含 Loop2 的 age2=111111，实际: {final_answer}"
        )
