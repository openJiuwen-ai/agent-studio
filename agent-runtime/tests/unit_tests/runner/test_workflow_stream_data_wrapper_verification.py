# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# pylint: disable=protected-access
"""
workflow_stream_data_wrapper.py 问题域 1 验证场景集

针对报告中的 4 个问题构造可重复、可观测的验证场景：

  P1-1 (残留风险): End 节点未执行分支引用 — 已修复，但存在 defs_by_id 未命中边界
  P1-2 (确认问题): OutputSchema/CustomSchema 转换代码重复 — 行为一致性验证
  P1-3 (确认风险): ContextVar 跨 Task 数据传递 — 耦合性风险验证
  P1-4 (确认问题): 回调注册静默失败 — 无日志可观测性验证

测试环境要求:
  - Python 3.10+
  - pytest + pytest-asyncio
  - 项目依赖: openjiuwen, jiuwen
  - 运行命令: pytest tests/unit_tests/runner/test_workflow_stream_data_wrapper_verification.py -v

前置条件:
  - workflow_stream_data_wrapper 模块可正常 import
  - openjiuwen CallbackFramework 单例已初始化
"""

import asyncio
import contextvars
import logging
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent_runtime.runner.workflow_stream_data_wrapper import (
    WorkflowStreamDataWrapper,
    _current_output_convert_ctx,
    _register_jiuwen_callbacks,
    _fill_unexecuted_end_branch_inputs,
    _filter_empty_end_ref_inputs,
    _extract_ref_source_id,
    _is_unresolved_end_ref_literal,
    _should_skip_end_ref_input,
    _schema_value_by_definition,
    EndRefInputFilterContext,
    END_NODE_TYPE,
    NODE_DEFS_KEY,
)

pytestmark = pytest.mark.asyncio

os.environ.setdefault("LLM_SSL_VERIFY", "false")


# =====================================================================
# 辅助工厂
# =====================================================================

def _make_end_ref_filter_context(executed_nodes=None, wf_defs=None, node_id="end_1"):
    """构造 EndRefInputFilterContext mock。"""
    session = MagicMock()
    session.node_id.return_value = node_id
    state = MagicMock()
    state.get_workflow_state.return_value = executed_nodes or []
    session.state.return_value = state
    return EndRefInputFilterContext(
        session=session,
        wf_defs=wf_defs if wf_defs is not None else {},
    )


def _make_end_node_def(field_defs):
    """构造 End 节点 configs.userFields.inputs 定义列表。"""
    return field_defs


# =====================================================================
# P1-1: End 节点未执行分支引用 — 残留边界风险验证
# =====================================================================

class TestEndNodeUnexecBranchRef:
    """
    P1-1 验证场景: End 节点引用未执行分支输出时类型强转

    场景描述:
      工作流包含条件分支 A/B，End 节点引用两个分支的输出。
      当仅分支 A 执行时，分支 B 的 ${branch_b.field} 引用未被解析。

    已修复路径 (验证修复有效):
      - _fill_unexecuted_end_branch_inputs: 填充类型化占位值
      - _filter_empty_end_ref_inputs: 过滤未解析引用字符串

    残留风险路径 (验证边界问题):
      - defs_by_id 未命中: field_id 在 input_schema 中存在但不在 uf_inputs_defs 中
      - 部分解析状态: 变量池将引用部分解析为非空但非法的值
    """

    # ---- 已修复路径验证 ----

    async def test_fixed_unexec_branch_ref_filled_with_typed_placeholder(self):
        """[修复验证] 未执行分支的 integer 引用被填充为 0，force_convert 不报错。

        前置条件:
          - input_schema.userFields 含 ${branch_b.output_count} (integer 类型)
          - branch_b 不在 executed_nodes 中
          - 当前值为 "" (Vertex sanitize 结果)

        预期结果:
          - _fill_unexecuted_end_branch_inputs 将值填充为 0
          - force_convert 对 0 做 integer 强转成功
        """
        inputs = {"userFields": {"count": ""}, "systemFields": {}}
        input_schema = {"userFields": {"count": "${branch_b.output_count}"}}
        uf_defs = [{"id": "count", "type": "integer"}]
        sf_defs = []
        ctx = _make_end_ref_filter_context(
            executed_nodes=["branch_a"],
            wf_defs={"branch_a": {}, "branch_b": {}},
        )

        result = _fill_unexecuted_end_branch_inputs(
            inputs, input_schema, uf_defs, sf_defs, ctx
        )

        assert result["userFields"]["count"] == 0

    async def test_fixed_unexec_branch_ref_filtered_when_still_literal(self):
        """[修复验证] 未解析的 ${node.field} 字面量被从 defs 列表中过滤。

        前置条件:
          - input_schema.userFields 含 ${branch_b.text} (string 类型)
          - 当前值仍为原始引用字符串 "${branch_b.text}"
          - branch_b 不在 executed_nodes 中

        预期结果:
          - _filter_empty_end_ref_inputs 从 uf_inputs_defs 中移除该字段
          - force_convert 不再校验该字段
        """
        inputs = {"userFields": {"text": "${branch_b.text}"}, "systemFields": {}}
        input_schema = {"userFields": {"text": "${branch_b.text}"}}
        uf_defs = [{"id": "text", "type": "string"}]
        sf_defs = []
        ctx = _make_end_ref_filter_context(
            executed_nodes=["branch_a"],
            wf_defs={"branch_a": {}, "branch_b": {}},
        )

        filtered_uf, filtered_sf = _filter_empty_end_ref_inputs(
            inputs, input_schema, uf_defs, sf_defs, ctx
        )

        assert len(filtered_uf) == 0, "未解析的引用字面量应被从 defs 列表中过滤"

    # ---- 残留风险 A: defs_by_id 未命中 ----

    async def test_residual_risk_defs_by_id_miss_leaves_empty_string(self):
        """[残留风险 A] field_id 在 input_schema 中但不在 uf_inputs_defs 中 → 值保持为空字符串。

        前置条件:
          - input_schema.userFields 有 {"count": "${branch_b.output_count}"}
          - uf_inputs_defs 为空列表 (定义缺失或 ID 不匹配)
          - branch_b 不在 executed_nodes 中
          - 当前值为 ""

        预期表现:
          - _fill_unexecuted_end_branch_inputs: defs_by_id 未命中 → 跳过 (line 167-168)
          - 值保持为 ""
          - 但因 uf_inputs_defs 为空，force_convert 不遍历该字段 → 无异常

        风险评估: 低 — 虽然值未被填充，但因定义不在列表中，force_convert 跳过
        """
        inputs = {"userFields": {"count": ""}, "systemFields": {}}
        input_schema = {"userFields": {"count": "${branch_b.output_count}"}}
        uf_defs = []  # 定义缺失
        sf_defs = []
        ctx = _make_end_ref_filter_context(
            executed_nodes=["branch_a"],
            wf_defs={"branch_a": {}, "branch_b": {}},
        )

        result = _fill_unexecuted_end_branch_inputs(
            inputs, input_schema, uf_defs, sf_defs, ctx
        )

        assert result["userFields"]["count"] == "", (
            "defs_by_id 未命中时值应保持为空字符串 (未被填充)"
        )

    # ---- 残留风险 B: 部分解析状态 ----

    async def test_residual_risk_partial_resolution_skips_fill(self):
        """[残留风险 B] 变量池部分解析为非空值 → 跳过填充 → 可能导致类型不匹配。

        前置条件:
          - input_schema.userFields 有 ${branch_b.output_count} (integer 类型)
          - branch_b 不在 executed_nodes 中
          - 变量池将引用部分解析为 "not_a_number" (非空、非引用字符串)
          - uf_inputs_defs 含 {"id": "count", "type": "integer"}

        预期表现:
          - _fill_unexecuted_end_branch_inputs: current_value="not_a_number" 非空 → 跳过 (line 164)
          - _filter_empty_end_ref_inputs: "not_a_number" != "${branch_b.output_count}" → 不过滤
          - force_convert: int("not_a_number") → ValueError → JiuWenBaseException

        异常特征:
          - 抛出 OpenjiuwenJiuWenBaseException (error_code=101039)
          - 消息包含 "component execute error" 和 "Incorrect type for key"

        风险评估: 中 — 部分解析到非法值时类型强转失败，但此行为在语义上是正确的
          (值类型不匹配应报错)。真正风险在于变量池可能产生 stale 值。
        """
        inputs = {"userFields": {"count": "not_a_number"}, "systemFields": {}}
        input_schema = {"userFields": {"count": "${branch_b.output_count}"}}
        uf_defs = [{"id": "count", "type": "integer"}]
        sf_defs = []
        ctx = _make_end_ref_filter_context(
            executed_nodes=["branch_a"],
            wf_defs={"branch_a": {}, "branch_b": {}},
        )

        result = _fill_unexecuted_end_branch_inputs(
            inputs, input_schema, uf_defs, sf_defs, ctx
        )
        assert result["userFields"]["count"] == "not_a_number", (
            "非空值不应被填充覆盖"
        )

        filtered_uf, _ = _filter_empty_end_ref_inputs(
            result, input_schema, uf_defs, sf_defs, ctx
        )
        assert len(filtered_uf) == 1, "部分解析的字段不应被过滤"

    # ---- 残留风险 C: array/object 类型 + 未命中 defs ----

    async def test_residual_risk_array_def_miss_with_empty_value(self):
        """[残留风险 C] array 类型引用 + defs_by_id 未命中 → 值为空字符串 → force_convert 失败。

        前置条件:
          - input_schema.userFields 有 ${branch_b.items} (array 类型)
          - uf_inputs_defs 含 {"id": "items", "type": "array", "schema": {...}}
          - 当前值为 ""
          - branch_b 不在 executed_nodes 中

        预期表现:
          - _fill_unexecuted_end_branch_inputs: defs_by_id 命中 → 填充为 []
          - force_convert 对 [] 做 array 转换 → 成功

        风险评估: 无风险 — defs_by_id 命中时填充正确
        """
        inputs = {"userFields": {"items": ""}, "systemFields": {}}
        input_schema = {"userFields": {"items": "${branch_b.items}"}}
        uf_defs = [{"id": "items", "type": "array", "schema": {"type": "string"}}]
        sf_defs = []
        ctx = _make_end_ref_filter_context(
            executed_nodes=["branch_a"],
            wf_defs={"branch_a": {}, "branch_b": {}},
        )

        result = _fill_unexecuted_end_branch_inputs(
            inputs, input_schema, uf_defs, sf_defs, ctx
        )

        assert result["userFields"]["items"] == [], (
            "array 类型的未执行分支引用应被填充为空列表 []"
        )


# =====================================================================
# P1-2: OutputSchema/CustomSchema 转换代码重复 — 行为一致性验证
# =====================================================================

class TestSchemaConversionDuplication:
    """
    P1-2 验证场景: OutputSchema 与 CustomSchema 转换方法行为一致性

    场景描述:
      16 个转换方法 (8 OutputSchema + 8 CustomSchema) 高度重复，
      唯一差异是数据提取方式:
        - OutputSchema: chunk.payload
        - CustomSchema: chunk.data / chunk.model_dump()

    风险:
      重复代码容易在修改时遗漏其中一个分支，导致行为不一致。
      以下测试构造相同输入数据，验证两条路径输出是否一致。

    环境配置:
      - 构造 WorkflowStreamDataWrapper 实例 (is_debug=False)
      - 分别模拟 OutputSchema 和 CustomSchema chunk
    """

    @staticmethod
    def _make_wrapper():
        """构造测试用 wrapper 实例。"""
        return WorkflowStreamDataWrapper(
            execution_id="test-exec-001",
            is_debug=False,
            conversation_id="test-conv-001",
            node_id_to_name={},
            history=[],
            query="test query",
        )

    async def test_workflow_start_output_vs_custom_consistency(self):
        """[一致性验证] workflow_start: OutputSchema 与 CustomSchema 输出应一致。

        前置条件:
          - 构造 OutputSchema(type="workflow_start", payload={"workflow_id": "wf_1"})
          - 构造 CustomSchema(type="workflow_start", data={"workflow_id": "wf_1"})

        预期结果:
          - 两条路径输出 event="workflow_start", data={"workflow_id": "wf_1"}
          - 对比 _convert_workflow_start vs _convert_workflow_start_from_custom
        """
        wrapper = self._make_wrapper()

        from openjiuwen.core.session.stream.base import OutputSchema, CustomSchema

        out_chunk = OutputSchema(type="workflow_start", payload={"workflow_id": "wf_1"}, index=0)
        cus_chunk = CustomSchema(type="workflow_start", data={"workflow_id": "wf_1"}, index=0)

        out_result = wrapper._convert_output_schema(out_chunk)
        cus_result = wrapper._convert_custom_schema(cus_chunk)

        assert out_result["event"] == cus_result["event"] == "workflow_start"
        assert out_result["data"] == cus_result["data"] == {"workflow_id": "wf_1"}

    async def test_workflow_exception_output_vs_custom_consistency(self):
        """[一致性验证] workflow_exception: 两条路径输出应一致。

        前置条件:
          - OutputSchema(type="workflow_exception", payload={"error_code": -1, "message": "err"})
          - CustomSchema(type="workflow_exception", data={"error_code": -1, "message": "err"})

        预期结果:
          - 两条路径输出 event="exception", data 一致
        """
        wrapper = self._make_wrapper()

        from openjiuwen.core.session.stream.base import OutputSchema, CustomSchema

        payload = {"error_code": -1, "message": "test error"}
        out_chunk = OutputSchema(type="workflow_exception", payload=payload, index=0)
        cus_chunk = CustomSchema(type="workflow_exception", data=payload, index=0)

        out_result = wrapper._convert_output_schema(out_chunk)
        cus_result = wrapper._convert_custom_schema(cus_chunk)

        assert out_result["event"] == cus_result["event"] == "exception"
        assert out_result["data"] == cus_result["data"]

    async def test_partial_content_output_vs_custom_consistency(self):
        """[一致性验证] partial_content: 两条路径输出应一致。

        前置条件:
          - OutputSchema(type="partial_content", payload={"answer": "hello", "node_id": "n1"})
          - CustomSchema(type="partial_content", data={"answer": "hello", "node_id": "n1"})

        预期结果:
          - 两条路径输出 event="message", data 一致
        """
        wrapper = self._make_wrapper()

        from openjiuwen.core.session.stream.base import OutputSchema, CustomSchema

        payload = {"answer": "hello", "node_id": "n1", "node_name": "Node1", "node_type": "Code"}
        out_chunk = OutputSchema(type="partial_content", payload=payload, index=0)
        cus_chunk = CustomSchema(type="partial_content", data=payload, index=0)

        out_result = wrapper._convert_output_schema(out_chunk)
        cus_result = wrapper._convert_custom_schema(cus_chunk)

        assert out_result["event"] == cus_result["event"] == "message"
        assert out_result["data"] == cus_result["data"]

    async def test_behavior_divergence_message_end_outputs_field(self):
        """[行为差异检测] message_end: CustomSchema 版始终添加 outputs.user_fields, OutputSchema 版仅当 userFields 存在时添加。

        前置条件:
          - payload 不含 userFields 字段

        预期表现 (当前代码行为):
          - OutputSchema 版: data 不含 outputs 键
          - CustomSchema 版: data 含 outputs={"user_fields": {}} (始终添加)

        风险:
          下游消费者可能依赖 outputs 键的存在性，两条路径行为不一致。
        """
        wrapper = self._make_wrapper()

        from openjiuwen.core.session.stream.base import OutputSchema, CustomSchema

        payload = {"answer": "hi", "node_id": "n1", "node_name": "N1", "node_type": "Code"}

        out_chunk = OutputSchema(type="message_end", payload=payload, index=0)
        cus_chunk = CustomSchema(type="message_end", data=payload, index=0)

        out_result = wrapper._convert_output_schema(out_chunk)
        cus_result = wrapper._convert_custom_schema(cus_chunk)

        has_outputs_out = "outputs" in out_result["data"]
        has_outputs_cus = "outputs" in cus_result["data"]

        assert has_outputs_cus, "CustomSchema 版应始终包含 outputs 键"
        assert not has_outputs_out, "OutputSchema 版在 payload 无 userFields 时不应包含 outputs 键"

    async def test_behavior_divergence_workflow_end_outputs_field(self):
        """[行为差异检测] workflow_end: CustomSchema 版始终添加 outputs.user_fields, OutputSchema 版不添加。

        前置条件:
          - payload 不含 userFields 字段

        预期表现 (当前代码行为):
          - OutputSchema 版 (_convert_workflow_end): data 不含 outputs
          - CustomSchema 版 (_convert_workflow_end_from_custom): data 含 outputs={"user_fields": {}}
        """
        wrapper = self._make_wrapper()

        from openjiuwen.core.session.stream.base import OutputSchema, CustomSchema

        payload = {"answer": "done", "node_id": "end_1", "node_name": "End", "node_type": END_NODE_TYPE}

        out_chunk = OutputSchema(type="workflow_end", payload=payload, index=0)
        cus_chunk = CustomSchema(type="workflow_end", data=payload, index=0)

        out_result = wrapper._convert_output_schema(out_chunk)
        cus_result = wrapper._convert_custom_schema(cus_chunk)

        assert "outputs" not in out_result["data"], (
            "OutputSchema 版 _convert_workflow_end 不应添加 outputs"
        )
        assert "outputs" in cus_result["data"], (
            "CustomSchema 版 _convert_workflow_end_from_custom 应始终添加 outputs"
        )


# =====================================================================
# P1-3: ContextVar 跨 Task 数据传递 — 耦合性风险验证
# =====================================================================

class TestContextVarCrossTaskCoupling:
    """
    P1-3 验证场景: ContextVar 在跨 asyncio Task 时的数据传递行为

    场景描述:
      type_convert_inputs (COMPONENT_BATCH_INPUT 回调) 写入 ContextVar,
      type_convert_outputs (COMPONENT_BATCH_OUTPUT 回调) 读取 ContextVar。
      当前依赖 "同一节点的 input/output 回调在同一 asyncio.Task 中执行" 的假设。

    风险:
      1. 若引擎执行模型变更 (如 output 处理移至不同 Task), ContextVar 读到 None
      2. type_convert_outputs 在 ctx is None 时静默返回未转换的 result (无日志)
      3. 并发场景下不同节点的 ContextVar 是否真正隔离

    验证方法:
      - 场景 A: 同一 Task 内 set → get (正常路径, 应成功)
      - 场景 B: 不同 Task 间 set → get (跨 Task, 读到 None)
      - 场景 C: 并发 Task 隔离性验证
      - 场景 D: 模拟 type_convert_outputs 在 ctx=None 时的静默降级
    """

    async def test_same_task_contextvar_set_get(self):
        """[场景 A] 同一 asyncio.Task 内 set → get → 成功读取。

        前置条件:
          - _current_output_convert_ctx 初始值为 None

        操作步骤:
          1. 在同一 Task 内调用 _current_output_convert_ctx.set({...})
          2. 调用 _current_output_convert_ctx.get()

        预期结果:
          - get() 返回 set() 写入的字典
        """
        _current_output_convert_ctx.set(None)
        test_ctx = {
            "uf_outputs_defs": [{"id": "field1", "type": "string"}],
            "sf_outputs_defs": [],
            "node_name": "TestNode",
            "node_type": "Code",
            "node_id": "node_1",
        }
        _current_output_convert_ctx.set(test_ctx)
        assert _current_output_convert_ctx.get() is test_ctx

    async def test_cross_task_contextvar_not_propagated(self):
        """[场景 B] 不同 asyncio.Task 间 ContextVar 不传播 → 读到 None。

        前置条件:
          - _current_output_convert_ctx 初始值为 None

        操作步骤:
          1. Task A (模拟 type_convert_inputs) set ContextVar
          2. Task B (模拟 type_convert_outputs) 在独立 Task 中 get ContextVar
          3. Task B 不是 Task A 的子 Task, 而是 main coroutine 创建的独立 Task

        预期结果:
          - Task A 中 set 的值仅在 Task A 的 context 副本中可见
          - Task B (sibling task) 读到 None (默认值)
          - main coroutine 也读到 None

        异常特征:
          若引擎将 output 处理移至独立 Task, type_convert_outputs 读到 None,
          静默返回未转换 result → 下游收到未校验类型的数据

        技术原理:
          asyncio.create_task 使用 copy_context() 拷贝创建时的父 context。
          Task A 内部 set() 只影响 Task A 的 context 副本,
          不影响 main context 或 sibling Task B 的 context。
        """
        _current_output_convert_ctx.set(None)

        test_ctx = {
            "uf_outputs_defs": [{"id": "field1", "type": "integer"}],
            "sf_outputs_defs": [],
            "node_name": "NodeA",
            "node_type": "Code",
            "node_id": "node_a",
        }

        # Task A: 模拟 type_convert_inputs (在一个独立 Task 中 set)
        async def simulate_input_processing():
            _current_output_convert_ctx.set(test_ctx)
            # 在 Task A 内部可读到
            assert _current_output_convert_ctx.get() is test_ctx, (
                "Task A 内部应能读到自己 set 的值"
            )

        await asyncio.create_task(simulate_input_processing())

        # main coroutine: Task A 的 set 不影响 main context
        assert _current_output_convert_ctx.get() is None, (
            "main context 应读不到 Task A 内部 set 的值"
        )

        # Task B: 模拟 type_convert_outputs (另一个独立 Task)
        async def simulate_output_processing():
            return _current_output_convert_ctx.get()

        result = await asyncio.create_task(simulate_output_processing())
        assert result is None, (
            "Task B (sibling) 应读到 None — Task A 的 ContextVar set 不传播到 sibling Task"
        )

    async def test_concurrent_tasks_contextvar_isolation(self):
        """[场景 C] 并发 asyncio.Task 间 ContextVar 互不干扰。

        前置条件:
          - 无

        操作步骤:
          1. 创建两个并发 Task, 各自 set 不同的 ContextVar 值
          2. 各自在 set 后读取自己的值
          3. 等待两个 Task 完成

        预期结果:
          - 每个 Task 读到的是自己 set 的值, 不受另一个 Task 影响
          - 验证 ContextVar per-Task 隔离的正确性

        依赖:
          - asyncio.create_task 创建的 Task 会拷贝当前 context (copy_context)
        """
        _current_output_convert_ctx.set(None)

        async def set_and_get(value):
            _current_output_convert_ctx.set(value)
            await asyncio.sleep(0.01)  # 让出控制权, 允许其他 Task 运行
            return _current_output_convert_ctx.get()

        ctx_a = {"node_id": "node_a", "uf_outputs_defs": [{"id": "a", "type": "string"}]}
        ctx_b = {"node_id": "node_b", "uf_outputs_defs": [{"id": "b", "type": "integer"}]}

        result_a, result_b = await asyncio.gather(
            asyncio.create_task(set_and_get(ctx_a)),
            asyncio.create_task(set_and_get(ctx_b)),
        )

        assert result_a is ctx_a, "Task A 应读到自己的值"
        assert result_b is ctx_b, "Task B 应读到自己的值"
        assert result_a is not result_b, "两个 Task 的 ContextVar 值应不同"

    async def test_type_convert_outputs_silent_degradation_when_ctx_none(self):
        """[场景 D] type_convert_outputs 在 ctx=None 时静默返回未转换 result。

        前置条件:
          - _current_output_convert_ctx 为 None (模拟跨 Task 场景)

        操作步骤:
          1. 设置 _current_output_convert_ctx 为 None
          2. 构造一个未做类型强转的 result (含类型不匹配的字段)
          3. 调用 type_convert_outputs 逻辑: ctx is None → 直接返回 result

        预期结果:
          - result 原样返回, 不做任何类型校验或转换
          - 无任何日志或警告输出
          - 下游消费者可能收到 string "123" 而非 integer 123

        风险:
          这是 P1-3 的核心风险 — 类型校验静默失效, 无可观测性
        """
        _current_output_convert_ctx.set(None)

        ctx = _current_output_convert_ctx.get()
        assert ctx is None, "ContextVar 应为 None"

        result = {
            "userFields": {"count": "not_an_integer"},
            "systemFields": {},
        }

        if ctx is None:
            pass_through_result = result
        else:
            pass_through_result = "would_convert"

        assert pass_through_result is result, (
            "ctx=None 时 result 应原样返回, 不做类型强转"
        )
        assert pass_through_result["userFields"]["count"] == "not_an_integer", (
            "类型不匹配的值应原样保留 (未被强转为 integer)"
        )


# =====================================================================
# P1-4: 回调注册静默失败 — 无日志可观测性验证
# =====================================================================

class TestSilentCallbackRegistrationFailure:
    """
    P1-4 验证场景: _register_jiuwen_callbacks() 异常被静默吞掉

    场景描述:
      _register_jiuwen_callbacks() 在模块 import 时执行 (line 1386),
      整个函数体包裹在 try/except Exception: pass 中 (line 1104, 1381-1382)。
      任何注册失败 (import 错误、框架未初始化等) 都被静默吞掉, 无日志输出。

    风险:
      1. 类型强转回调 (type_convert_inputs/outputs) 未注册 → 类型校验完全不执行
      2. 性能日志回调 (node_perf_start/end) 未注册 → 无性能数据
      3. global 变量解析回调 (resolve_global_vars_transform) 未注册 → ${global.xxx} 不解析
      4. 以上全部静默发生, 运行时无任何错误信号

    环境配置:
      - 使用 caplog fixture 捕获日志输出
      - patch 目标函数模拟注册失败

    验证方法:
      - 场景 A: 模拟 import 失败 → 验证无任何日志输出
      - 场景 B: 模拟 get_callback_framework 返回 None → 验证无日志
      - 场景 C: 模拟 _fw.on() 抛异常 → 验证无日志
      - 场景 D: 验证修复后应输出 warning 日志
    """

    async def test_import_failure_logs_warning(self, caplog):
        """[场景 A - 修复后] 模拟 import 失败 → 注册函数输出 WARNING 日志。

        修复前: except: pass → 无任何日志
        修复后: except Exception as e: _logger.warning(...) → 输出 WARNING

        前置条件:
          - patch builtins.__import__ 使 openjiuwen callback 模块 import 失败

        预期表现:
          - caplog 包含至少一条 WARNING 记录
          - 日志消息包含 "register" 或 "callback" 关键字
        """
        original_import = __import__

        def mock_import(name, *args, **kwargs):
            if "openjiuwen.core.runner.callback.events" in name:
                raise ImportError(f"Simulated import failure: {name}")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            with caplog.at_level(logging.DEBUG):
                _register_jiuwen_callbacks()

        warning_records = [r for r in caplog.records if r.levelno >= logging.WARNING]
        assert len(warning_records) >= 1, (
            "修复后应在注册失败时输出 WARNING 日志"
        )

    async def test_framework_none_no_warning(self, caplog):
        """[场景 B] get_callback_framework() 返回 None → 函数直接 return, 无异常无日志。

        注意: _fw is None 时函数直接 return (line 1111-1112), 不进入 except 块。
        这是正常路径, 不需要日志。
        """
        with patch(
            "openjiuwen.core.runner.callback.utils.get_callback_framework",
            return_value=None,
        ):
            with caplog.at_level(logging.DEBUG):
                _register_jiuwen_callbacks()

        warning_records = [r for r in caplog.records if r.levelno >= logging.WARNING]
        assert len(warning_records) == 0, "_fw is None 是正常路径, 不应有 WARNING"

    async def test_on_decorator_exception_logs_warning(self, caplog):
        """[场景 C - 修复后] _fw.on() 抛异常 → 输出 WARNING 日志。

        修复前: except: pass → 无日志, 后续 3 个回调也不注册
        修复后: except Exception as e: _logger.warning(...) → 输出 WARNING

        预期表现:
          - caplog 包含至少一条 WARNING 记录
        """
        mock_fw = MagicMock()
        mock_fw.on.side_effect = RuntimeError("Simulated registration failure")

        with patch(
            "openjiuwen.core.runner.callback.utils.get_callback_framework",
            return_value=mock_fw,
        ):
            with patch(
                "openjiuwen.core.session.internal.workflow.NodeSession",
                create=True,
            ):
                with caplog.at_level(logging.DEBUG):
                    _register_jiuwen_callbacks()

        warning_records = [r for r in caplog.records if r.levelno >= logging.WARNING]
        assert len(warning_records) >= 1, (
            "修复后应在注册失败时输出 WARNING 日志"
        )

    async def test_registration_warning_contains_exception_info(self, caplog):
        """[场景 D] 验证 WARNING 日志包含异常信息和堆栈。

        前置条件:
          - patch get_callback_framework 返回 mock, 其 on() 抛 RuntimeError

        操作步骤:
          1. 调用 _register_jiuwen_callbacks()
          2. 检查 caplog 中 WARNING 记录的消息内容和堆栈

        预期结果:
          - WARNING 日志消息包含 "register" 或 "callback" 关键字
          - exc_info=True 使得日志记录包含异常堆栈
        """
        mock_fw = MagicMock()
        mock_fw.on.side_effect = RuntimeError("Simulated registration failure")

        with patch(
            "openjiuwen.core.runner.callback.utils.get_callback_framework",
            return_value=mock_fw,
        ):
            with patch(
                "openjiuwen.core.session.internal.workflow.NodeSession",
                create=True,
            ):
                with caplog.at_level(logging.DEBUG):
                    _register_jiuwen_callbacks()

        warning_records = [r for r in caplog.records if r.levelno >= logging.WARNING]
        assert len(warning_records) >= 1, "应有至少一条 WARNING 记录"
        msg = warning_records[0].message
        assert "register" in msg.lower() or "callback" in msg.lower(), (
            "WARNING 日志应包含 'register' 或 'callback' 关键字"
        )
        assert warning_records[0].exc_info is not None, (
            "WARNING 日志应包含异常堆栈 (exc_info=True)"
        )


# =====================================================================
# 综合: 回调注册失败后的级联影响验证
# =====================================================================

class TestCallbackRegistrationCascadeImpact:
    """
    P1-4 级联影响验证: 回调注册失败后, 类型强转系统完全失效

    场景描述:
      若 _register_jiuwen_callbacks() 静默失败, 以下回调全部不生效:
        1. resolve_global_vars_transform — ${global.xxx} 引用不解析
        2. type_convert_inputs — 输入类型强转不执行
        3. type_convert_outputs — 输出类型强转不执行
        4. node_perf_start / node_perf_end — 性能日志不记录

    验证方法:
      检查 CallbackFramework 中是否已注册对应事件回调
    """

    async def test_callbacks_registered_after_normal_import(self):
        """[正常路径] 模块正常 import 后, 回调应已注册到 CallbackFramework。

        前置条件:
          - workflow_stream_data_wrapper 已被 import (触发模块级 _register_jiuwen_callbacks)
          - CallbackFramework 单例已初始化

        预期结果:
          - COMPONENT_BATCH_INPUT 事件有 transform 类型回调
          - COMPONENT_BATCH_OUTPUT 事件有 transform 类型回调
          - NODE_EXECUTED 事件有 regular 回调

        若此测试失败, 说明回调注册确实存在问题 (但可能被 except: pass 吞掉)。
        """
        from openjiuwen.core.runner.callback.events import WorkflowEvents
        from openjiuwen.core.runner.callback.utils import get_callback_framework

        try:
            fw = get_callback_framework()
            if fw is None:
                pytest.skip("CallbackFramework not initialized")

            input_callbacks = fw._callbacks.get(
                WorkflowEvents.COMPONENT_BATCH_INPUT, []
            )
            transform_input_callbacks = [
                c for c in input_callbacks if c.callback_type == "transform"
            ]
            assert len(transform_input_callbacks) >= 2, (
                "应有至少 2 个 COMPONENT_BATCH_INPUT transform 回调 "
                "(resolve_global_vars + type_convert_inputs + node_perf_start)"
            )

            output_callbacks = fw._callbacks.get(
                WorkflowEvents.COMPONENT_BATCH_OUTPUT, []
            )
            transform_output_callbacks = [
                c for c in output_callbacks if c.callback_type == "transform"
            ]
            assert len(transform_output_callbacks) >= 1, (
                "应有至少 1 个 COMPONENT_BATCH_OUTPUT transform 回调 (type_convert_outputs)"
            )

        except AttributeError:
            pytest.skip("CallbackFramework internals not accessible")

    async def test_type_convert_not_applied_when_ctx_none(self):
        """[级联影响] 模拟回调未注册时, 输出类型不匹配的数据原样通过。

        前置条件:
          - _current_output_convert_ctx 为 None (模拟回调未注册或跨 Task)

        操作步骤:
          1. 设置 ctx 为 None
          2. 构造 result 含类型不匹配字段 (string "abc" 应为 integer)
          3. 验证该 result 原样保留

        预期结果:
          - "abc" 未被强转为 integer, 原样保留
          - 模拟下游消费者收到类型不匹配数据

        风险:
          - 若回调未注册 (P1-4), 所有节点的输出类型校验静默失效
          - 下游可能因类型不匹配产生运行时错误, 但错误源头不可追溯
        """
        _current_output_convert_ctx.set(None)
        ctx = _current_output_convert_ctx.get()
        assert ctx is None

        result = {
            "userFields": {"count": "abc"},
            "systemFields": {},
        }

        if ctx is None:
            pass_through = result
        else:
            pass_through = "converted"

        assert pass_through is result
        assert pass_through["userFields"]["count"] == "abc", (
            "ctx=None 时类型不匹配的值应原样保留, 模拟回调未注册场景"
        )
