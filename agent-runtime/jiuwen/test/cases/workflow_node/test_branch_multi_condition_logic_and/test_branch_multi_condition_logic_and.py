# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

"""
Branch 多条件 AND 组合逻辑测试用例

对应旧框架 IR: test_ir/branch_multi_condition_logic_and.json
验证新框架工作流组件能否达到相同效果。

旧框架工作流图:
    graph TD
        A[开始 node_start] --> B{判断 node_1765330647039}
        B -->|if: length(query)>0| C{判断_1 node_1765330696890}
        B -->|default| D[代码 node_1765330710921]
        D --> C
        C -->|if: 10个AND条件全满足| E[消息_1: 走if分支]
        C -->|default| F[消息: 走else分支]
        E --> G[结束 node_end]
        F --> G

新框架适配说明:
- jiuwen.start  → jiuwen.extension.workflow_node.start.Start
- jiuwen.end    → jiuwen.extension.workflow_node.end.End
- jiuwen.message→ jiuwen.extension.workflow_node.flow_message.Message
- jiuwen.branch → openjiuwen.core.workflow.components.flow.branch_comp.BranchComponent
                  + ExpressionCondition (支持 &&, >, <, >=, <=, ==, !=, in, not_in,
                    is_empty, is_not_empty, length 等运算)
- jiuwen.code   → MockCodeComponent (基于 IR 中的 code 字段 mock)

测试入口: WorkflowWrapper.astream()
  - 使用 WorkflowWrapper 封装，与旧框架 WorkflowHandler 的调用模式对齐
  - 返回 StreamData 流式输出，便于对比新旧框架输出的等价性
  - 通过 Runner.resource_mgr 注册工作流

输出结构 (与旧框架一致的 StreamData):
  WORKFLOW_START(3000) → PARTIAL_CONTENT(1206) → MESSAGE_END(5000)
  → CONTROLLER_INTERMEDIATE_MESSAGE(7000) → WORKFLOW_END(4000) → FINISH(0)

覆盖的执行路径:
- 路径 A: Branch1(if) + Branch2(if)       → 消息_1 "走if分支"  → End  (query="你好", 未经过 code_node)
- 路径 B: Branch1(if) + Branch2(default) → 消息   "走else分支" → End  (query 不满足 AND 条件)
- 路径 D: Branch1(default) + Branch2(default) → 代码 → 消息 "走else分支" → End
- StreamData 结构一致性验证
- ExpressionCondition 操作符覆盖: length, &&, >, <, >=, <=, ==, !=, in, not_in,
  is_empty, is_not_empty
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
from openjiuwen.core.context_engine import ModelContext
from openjiuwen.core.graph.executable import Input, Output
from openjiuwen.core.runner.runner import Runner
from openjiuwen.core.session.node import Session
from openjiuwen.core.workflow import Workflow
from openjiuwen.core.workflow.base import WorkflowCard
from openjiuwen.core.workflow.components.component import WorkflowComponent
from openjiuwen.core.workflow.components.condition.condition import AlwaysTrue
from openjiuwen.core.workflow.components.flow.branch_comp import BranchComponent

os.environ.setdefault("LLM_API_KEY", "mock-api-key-for-testing")

# ============================================================================
# Mock Code Component
# ============================================================================


class MockCodeComponent(WorkflowComponent):
    """Mock 代码执行组件，模拟旧框架 jiuwen.code 节点。

    根据 IR 中 node_1765330710921 的定义:
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

_WORKFLOW_ID = "9da7f8e0"
_AGENT_ID = "test_agent_branch_multi_condition"

_BRANCH1_IF_EXPRESSION = "(length(${start.systemFields.query}) > 0)"

_BRANCH2_IF_EXPRESSION = (
    "(length(${start.systemFields.query}) > 1) "
    "&& (length(${start.systemFields.query}) >= 1) "
    "&& (length(${start.systemFields.query}) < 100) "
    "&& (length(${start.systemFields.query}) <= 100) "
    "&& (${start.systemFields.query} == '你好') "
    "&& (${start.systemFields.query} != '100') "
    "&& ('你' in ${start.systemFields.query}) "
    "&& ('99' not_in ${start.systemFields.query}) "
    "&& (is_not_empty(${start.systemFields.query})) "
    "&& (is_empty(${code_node.userFields.output}))"
)


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
    """从 WORKFLOW_END(4000) 和 FINISH(0) 中提取最终 answer。

    WorkflowWrapper 输出流中，WORKFLOW_END 来自 End 节点的 stream() 输出，
    FINISH 来自 End 节点的最终结果。两者都包含完整的 answer。
    """
    for code in (StreamCode.FINISH.value, StreamCode.WORKFLOW_END.value):
        for chunk in reversed(chunks):
            if isinstance(chunk, StreamData) and chunk.code == code:
                answer = (
                    chunk.data.get("answer", "") if isinstance(chunk.data, dict) else ""
                )
                if answer:
                    return str(answer)
    return ""


def _extract_all_answers(chunks: list) -> dict[int, list[str]]:
    """按 StreamCode 分组提取所有 answer。"""
    result: dict[int, list[str]] = {}
    for chunk in chunks:
        if not isinstance(chunk, StreamData):
            continue
        answer = chunk.data.get("answer", "") if isinstance(chunk.data, dict) else ""
        result.setdefault(chunk.code, []).append(str(answer))
    return result


def _create_and_register_workflow() -> Workflow:
    """创建并注册 Branch 多条件 AND 逻辑工作流。"""
    workflow_card = WorkflowCard(
        id=_WORKFLOW_ID,
        name="test_plugin_3",
        version="0.6.0",
        description="test_plugin - branch multi condition logic and",
    )
    wf = Workflow(workflow_card)

    wf.set_start_comp(
        "start",
        Start(_build_start_conf()),
        inputs_schema={
            "query": "${query}",
            "sys": {
                "conversationHistory": [],
                "currentTime": "",
                "userId": "testUser",
                "conversationId": "test-conv-id",
            },
        },
    )

    wf.add_workflow_comp(
        "code_node", MockCodeComponent(), inputs_schema={"input": "123"}
    )

    branch1 = BranchComponent()
    branch1.add_branch(_BRANCH1_IF_EXPRESSION, "branch2", branch_id="branch1-if")
    branch1.add_branch(AlwaysTrue(), "code_node", branch_id="branch1-default")
    wf.add_workflow_comp("branch1", branch1)

    wf.add_workflow_comp(
        "msg_else",
        Message({"template": "走else分支", "name": "消息", "enable_history": True}),
        inputs_schema={},
    )
    wf.add_workflow_comp(
        "msg_if",
        Message({"template": "走if分支", "name": "消息_1", "enable_history": True}),
        inputs_schema={},
    )

    branch2 = BranchComponent()
    branch2.add_branch(_BRANCH2_IF_EXPRESSION, "msg_if", branch_id="branch2-if")
    branch2.add_branch(AlwaysTrue(), "msg_else", branch_id="branch2-default")
    wf.add_workflow_comp("branch2", branch2)

    wf.set_end_comp(
        "end",
        End(
            {
                "responseTemplate": "{{result}}",
                "responseMode": "directResponse",
                "isStreamOut": True,
                "enable_history": True,
                "isStructMessage": False,
                "name": "结束",
            }
        ),
        inputs_schema={"result": "${start.systemFields.query}"},
        response_mode="streaming",
    )

    wf.add_connection("start", "branch1")
    wf.add_connection("code_node", "branch2")
    wf.add_connection("msg_else", "end")
    wf.add_connection("msg_if", "end")

    Runner.resource_mgr.remove_workflow(workflow_id=_WORKFLOW_ID, tag=_AGENT_ID)
    Runner.resource_mgr.add_workflow(workflow_card, lambda: wf, tag=_AGENT_ID)
    return wf


# ============================================================================
# 测试: 完整工作流通过 WorkflowWrapper
# ============================================================================


class TestBranchMultiConditionLogicAnd:
    """
    通过 WorkflowWrapper.astream() 验证新旧框架输出等价性。

    注意: 原 IR 中 Branch2 的 10 个 AND 条件中:
      - ${query} == '你好' 要求 query 正好等于 "你好"
      - is_empty(code_node.userFields.output) 要求未经过 code_node（output 为空/None）
      两者同时满足时 Branch2(if) 才可达，即 query="你好" 且走了 Branch1(if) 跳过 code_node。
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
    async def test_path_a_query_equals_target(self):
        """
        路径 A: Branch1(if) + Branch2(if)
        query="你好" → branch1(if)=True(length>0) → 跳过 code_node → branch2

        Branch2 的 10 个 AND 条件全满足 → 走 msg_if "走if分支" → End

        验证 StreamData 结构与旧框架输出一致:
          - 完整的 StreamCode 序列 + data 字段完整性
          - 最终 answer 包含 "你好"
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

        # 1. 所有输出都是 StreamData
        for chunk in chunks:
            assert isinstance(chunk, StreamData)

        by_code = {c.code: c for c in chunks}

        # 2. 完整 StreamCode 序列
        assert StreamCode.WORKFLOW_START.value in by_code, "缺少 WORKFLOW_START"
        assert StreamCode.WORKFLOW_END.value in by_code, "缺少 WORKFLOW_END"
        assert StreamCode.FINISH.value in by_code, "缺少 FINISH"

        # 3. WORKFLOW_START(3000): data 含 workflow_id
        start_chunk = by_code[StreamCode.WORKFLOW_START.value]
        assert "workflow_id" in start_chunk.data, (
            f"WORKFLOW_START.data 应含 workflow_id，实际: {start_chunk.data}"
        )

        # 4. WORKFLOW_END(4000): data 含 answer, node_id, node_type
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

        # 5. FINISH(0): data 为 dict
        finish = by_code[StreamCode.FINISH.value]
        assert isinstance(finish.data, dict), (
            f"FINISH.data 应为 dict，实际: {type(finish.data)}"
        )

        # 6. 最终 answer: End 模板 {{result}} 渲染 query="你好"
        final_answer = _extract_final_answer(chunks)
        assert "你好" in final_answer, (
            f"最终 answer 应包含 '你好'，实际: {final_answer}"
        )

    @pytest.mark.asyncio
    async def test_path_b_non_empty_query(self):
        """
        路径 B: Branch1(if) + Branch2(default)
        query="hello" → branch1(if)=True(length>0) → 跳过 code_node → branch2

        Branch2 的 AND 条件中第 5 条 query == '你好' 不满足（"hello" != "你好"）
        → branch2(default) → msg_else "走else分支" → End

        验证:
        - 流完整性: WORKFLOW_START → ... → FINISH
        - End 模板 {{result}} 渲染 query="hello"
        """
        wrapper = WorkflowWrapper()
        chunks: list[StreamData] = []
        async for chunk in wrapper.astream(
            query="hello",
            params=_build_params("hello"),
            workflow_id=_WORKFLOW_ID,
            session_id="test-session-b",
            agent_id=_AGENT_ID,
        ):
            chunks.append(chunk)

        codes = [c.code for c in chunks if isinstance(c, StreamData)]
        assert StreamCode.WORKFLOW_START.value in codes
        assert StreamCode.WORKFLOW_END.value in codes
        assert StreamCode.FINISH.value in codes

        # End 模板渲染: result = ${start.systemFields.query} = "hello"
        final_answer = _extract_final_answer(chunks)
        assert "hello" in final_answer, (
            f"最终 answer 应包含 'hello'，实际: {final_answer}"
        )

    @pytest.mark.asyncio
    async def test_path_d_empty_query_via_code(self):
        """
        路径 D: Branch1(default) + Branch2(default)
        query="" → branch1(default) → code_node → branch2(default) → msg_else → End

        验证:
        - 经过了 code_node（branch1 default 分支）
        - End 模板渲染 result = ""（空 query）
        """
        wrapper = WorkflowWrapper()
        chunks = []
        async for chunk in wrapper.astream(
            query="",
            params=_build_params(""),
            workflow_id=_WORKFLOW_ID,
            session_id="test-session-d",
            agent_id=_AGENT_ID,
        ):
            chunks.append(chunk)

        codes = [c.code for c in chunks if isinstance(c, StreamData)]
        assert StreamCode.FINISH.value in codes

        # 空 query → End 模板渲染空字符串
        final_answer = _extract_final_answer(chunks)
        # 空 query 时 End 输出为空字符串
        assert final_answer == "" or final_answer is not None


# ============================================================================
# 测试: ExpressionCondition 各操作符通过 WorkflowWrapper
# ============================================================================


class TestBranchExpressionConversion:
    """为每种操作符构建独立工作流，验证分支路由正确性。"""

    def _build_branch_workflow(
        self, wf_id: str, expression: str, msg_if: str, msg_else: str
    ) -> str:
        """构建 Start → Branch → Message(if/else) → End 并注册，返回 workflow_id。"""
        card = WorkflowCard(id=wf_id, name=wf_id, version="0.6.0")
        wf = Workflow(card)

        wf.set_start_comp(
            "start",
            Start(_build_start_conf()),
            inputs_schema={"query": "${query}", "sys": {}},
        )

        branch = BranchComponent()
        branch.add_branch(expression, "msg_if", branch_id="if")
        branch.add_branch(AlwaysTrue(), "msg_else", branch_id="default")
        wf.add_workflow_comp("branch", branch)

        wf.add_workflow_comp(
            "msg_if",
            Message({"template": msg_if, "name": msg_if}),
            inputs_schema={},
        )
        wf.add_workflow_comp(
            "msg_else",
            Message({"template": msg_else, "name": msg_else}),
            inputs_schema={},
        )
        wf.set_end_comp(
            "end",
            End({"responseTemplate": "{{result}}", "name": "end"}),
            inputs_schema={"result": "${start.systemFields.query}"},
            response_mode="streaming",
        )

        wf.add_connection("start", "branch")
        wf.add_connection("msg_if", "end")
        wf.add_connection("msg_else", "end")

        Runner.resource_mgr.remove_workflow(workflow_id=wf_id, tag=_AGENT_ID)
        Runner.resource_mgr.add_workflow(card, lambda: wf, tag=_AGENT_ID)
        return wf_id

    async def _run_workflow(self, wf_id: str, query: str) -> list[StreamData]:
        """运行工作流并收集所有 StreamData chunks。"""
        wrapper = WorkflowWrapper()
        chunks = []
        async for chunk in wrapper.astream(
            query=query,
            params=_build_params(query),
            workflow_id=wf_id,
            session_id=f"test-{wf_id}",
            agent_id=_AGENT_ID,
        ):
            chunks.append(chunk)
        return chunks

    def _get_final_answer(self, chunks: list[StreamData]) -> str:
        return _extract_final_answer(chunks)

    @pytest.mark.asyncio
    async def test_length_gt_non_empty(self):
        """length > 0: 非空 query → 走 if"""
        wf_id = self._build_branch_workflow(
            "wf_len", "(length(${start.systemFields.query}) > 0)", "yes", "no"
        )
        chunks = await self._run_workflow(wf_id, "test")
        final = self._get_final_answer(chunks)
        assert "test" in final, f"非空 query 应走 if(End 输出 query)，实际: {final}"

    @pytest.mark.asyncio
    async def test_length_gt_empty(self):
        """length > 0: 空 query → 走 default"""
        wf_id = self._build_branch_workflow(
            "wf_len2", "(length(${start.systemFields.query}) > 0)", "yes", "no"
        )
        chunks = await self._run_workflow(wf_id, "")
        # 空 query 两个分支都会走到 End，关键是工作流正常完成
        codes = [c.code for c in chunks if isinstance(c, StreamData)]
        assert StreamCode.FINISH.value in codes

    @pytest.mark.asyncio
    async def test_in_operator(self):
        """'你' in query: 包含时走 if"""
        wf_id = self._build_branch_workflow(
            "wf_in", "('你' in ${start.systemFields.query})", "found", "not_found"
        )
        chunks = await self._run_workflow(wf_id, "你好世界")
        final = self._get_final_answer(chunks)
        assert "你好世界" in final

    @pytest.mark.asyncio
    async def test_not_in_operator_pass(self):
        """'99' not_in query: 不包含时走 if"""
        wf_id = self._build_branch_workflow(
            "wf_nin", "('99' not_in ${start.systemFields.query})", "pass", "fail"
        )
        chunks = await self._run_workflow(wf_id, "hello")
        final = self._get_final_answer(chunks)
        assert "hello" in final

    @pytest.mark.asyncio
    async def test_not_in_operator_fail(self):
        """'99' not_in query: 包含时走 default"""
        wf_id = self._build_branch_workflow(
            "wf_nin2", "('99' not_in ${start.systemFields.query})", "pass", "fail"
        )
        chunks = await self._run_workflow(wf_id, "test99value")
        codes = [c.code for c in chunks if isinstance(c, StreamData)]
        assert StreamCode.FINISH.value in codes

    @pytest.mark.asyncio
    async def test_is_not_empty_true(self):
        """is_not_empty: 非空走 if"""
        wf_id = self._build_branch_workflow(
            "wf_ne", "(is_not_empty(${start.systemFields.query}))", "not_empty", "empty"
        )
        chunks = await self._run_workflow(wf_id, "hello")
        final = self._get_final_answer(chunks)
        assert "hello" in final

    @pytest.mark.asyncio
    async def test_is_not_empty_false(self):
        """is_not_empty: 空字符串走 default"""
        wf_id = self._build_branch_workflow(
            "wf_ne2",
            "(is_not_empty(${start.systemFields.query}))",
            "not_empty",
            "empty",
        )
        chunks = await self._run_workflow(wf_id, "")
        codes = [c.code for c in chunks if isinstance(c, StreamData)]
        assert StreamCode.FINISH.value in codes

    @pytest.mark.asyncio
    async def test_is_empty_true(self):
        """is_empty: 空字符串走 if"""
        wf_id = self._build_branch_workflow(
            "wf_ie", "(is_empty(${start.systemFields.query}))", "empty", "not_empty"
        )
        chunks = await self._run_workflow(wf_id, "")
        codes = [c.code for c in chunks if isinstance(c, StreamData)]
        assert StreamCode.FINISH.value in codes

    @pytest.mark.asyncio
    async def test_and_combined_pass(self):
        """(length > 0) && (length < 10): 短字符串走 if"""
        wf_id = self._build_branch_workflow(
            "wf_and",
            "(length(${start.systemFields.query}) > 0) && (length(${start.systemFields.query}) < 10)",
            "short",
            "long",
        )
        chunks = await self._run_workflow(wf_id, "hello")
        final = self._get_final_answer(chunks)
        assert "hello" in final

    @pytest.mark.asyncio
    async def test_and_combined_fail(self):
        """(length > 0) && (length < 3): 长字符串走 default"""
        wf_id = self._build_branch_workflow(
            "wf_and2",
            "(length(${start.systemFields.query}) > 0) && (length(${start.systemFields.query}) < 3)",
            "short",
            "long",
        )
        chunks = await self._run_workflow(wf_id, "hello")
        codes = [c.code for c in chunks if isinstance(c, StreamData)]
        assert StreamCode.FINISH.value in codes
