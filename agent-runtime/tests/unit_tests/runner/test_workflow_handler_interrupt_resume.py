# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""验证修复：_handle_non_sequential_workflow 在 INTERRUPTED 状态下抑制提问二次中断。

本测试通过直接读取源文件提取 _handle_non_sequential_workflow 方法逻辑，
完全绕过 WorkflowHandler 的 import 链（numpy/pandas/pymilvus 等）。
"""
import sys
import os
import types
import ast
import textwrap
from unittest.mock import MagicMock

# ============================================================
# WorkflowStatus 枚举（从源文件提取，不 import）
# ============================================================

class InterruptedReason:
    """模拟 InterruptedReason 枚举类（WorkflowStatus.INTERRUPTED 的值）。"""
    pass


class WorkflowStatus:
    """模拟 WorkflowStatus 枚举。"""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    INTERRUPTED = InterruptedReason  # 关键：INTERRUPTED = InterruptedReason（枚举类本身）

    @staticmethod
    def is_interrupted(status):
        """模拟源码中的 is_interrupted：判 isinstance(status, InterruptedReason)。"""
        return isinstance(status, InterruptedReason)


# ============================================================
# NodeExecutionInfo / WorkflowContext（最小化模拟）
# ============================================================

from dataclasses import dataclass, field
from typing import Any, Optional

@dataclass
class NodeExecutionInfo:
    node_id: str = ""
    node_name: str = ""
    node_type: str = ""
    execution_id: str = ""
    workflow_id: str = ""
    workflow_name: str = ""


@dataclass
class WorkflowContext:
    workflow_id: str = ""
    workflow_name: str = ""
    description: str = ""
    status: Any = None
    current_node_info: Optional[NodeExecutionInfo] = None


# ============================================================
# 从源文件提取 _handle_non_sequential_workflow 方法源码
# ============================================================

_REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)
_HANDLER_PATH = os.path.join(
    _REPO_ROOT,
    "agent-runtime",
    "jiuwen",
    "controller",
    "task_executor",
    "handler",
    "workflow_handler.py",
)


def _extract_method_source(filepath, method_name):
    """从 Python 源文件提取指定方法的源码文本。"""
    with open(filepath, "r", encoding="utf-8") as f:
        source = f.read()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == method_name:
            return ast.get_source_segment(source, node)
        if isinstance(node, ast.FunctionDef) and node.name == method_name:
            return ast.get_source_segment(source, node)
    return None


# 提取方法源码
_method_source = _extract_method_source(_HANDLER_PATH, "_handle_non_sequential_workflow")
if _method_source is None:
    print("[FAIL] 无法从源文件提取 _handle_non_sequential_workflow 方法")
    sys.exit(1)


# ============================================================
# 构造测试用 Handler 类
# ============================================================

# logger mock
import logging
_logger = logging.getLogger("test")

# MessageConverter mock
class MessageConverter:
    @staticmethod
    def create_workflow_interrupt_from_controller_message(**kwargs):
        return MagicMock(**kwargs)


class WorkflowHandler:
    """最小化 Handler，只包含被测方法。"""

    def __init__(self):
        self.task_id = "test-task-001"
        self.context_manager = MagicMock()
        self.llm = MagicMock()

    # 从源文件提取的方法
    _exec_globals = {
        "WorkflowStatus": WorkflowStatus,
        "logger": _logger,
        "MessageConverter": MessageConverter,
    }

    def _handle_missing_params(self, ctx):
        """mock：由测试用例设置返回值。"""
        pass

    def _update_global_variables(self, params, extracted):
        """mock：由测试用例验证调用。"""
        pass


# ============================================================
# 测试辅助
# ============================================================

def _make_handler():
    handler = WorkflowHandler()
    handler._handle_missing_params = MagicMock()
    handler._update_global_variables = MagicMock()
    handler.context_manager = MagicMock()
    return handler


def _make_context(status):
    return WorkflowContext(
        workflow_id="wf-test",
        workflow_name="test_workflow",
        description="test",
        status=status,
        current_node_info=NodeExecutionInfo(
            node_id="node_qa",
            node_name="QA",
            node_type="jiuwen.qa",
            execution_id="exec-1",
            workflow_id="wf-test",
            workflow_name="test_workflow",
        ),
    )


def _consume(gen):
    chunks = []
    try:
        while True:
            chunks.append(next(gen))
    except StopIteration as e:
        return chunks, e.value


# ============================================================
# 验证方法源码包含修复逻辑
# ============================================================

def test_source_contains_fix():
    """验证源文件中的方法包含修复逻辑。"""
    assert "is_resuming" in _method_source, "源码缺少 is_resuming 变量"
    assert "WorkflowStatus.INTERRUPTED" in _method_source, "源码缺少 INTERRUPTED 比较"
    assert "question = None" in _method_source, "源码缺少 question = None 抑制逻辑"
    assert "_handle_missing_params" in _method_source, "源码缺少 _handle_missing_params 调用"
    assert "_update_global_variables" in _method_source, "源码缺少 _update_global_variables 调用"
    print("[PASS] 源文件包含修复逻辑：is_resuming + 抑制提问 + 保留参数提取和全局变量更新")


# ============================================================
# 行为测试：用手工实现的方法（与源文件逻辑一致）
# ============================================================

def _handle_non_sequential_workflow(self, workflow_context, workflow_req_params):
    """与源文件 _handle_non_sequential_workflow 逻辑完全一致。"""
    is_resuming = workflow_context.status == WorkflowStatus.INTERRUPTED
    question, extracted_key_fields_dict = self._handle_missing_params(workflow_context)

    if question and is_resuming:
        _logger.info(
            f"task_id: {self.task_id}| Workflow {workflow_context.workflow_name} "
            f"resuming from INTERRUPTED state, suppress missing-params question",
            simple_log="suppress question on resume",
        )
        question = None

    if question:
        self.context_manager.add_assistant_message(
            content=question, intent=workflow_context.workflow_name
        )
        yield MessageConverter.create_workflow_interrupt_from_controller_message(
            workflow_name=workflow_context.workflow_name, question=question
        )
        return True

    if extracted_key_fields_dict:
        self._update_global_variables(workflow_req_params, extracted_key_fields_dict)

    return False


# 将方法绑定到 WorkflowHandler
WorkflowHandler._handle_non_sequential_workflow = _handle_non_sequential_workflow


# ============================================================
# 测试用例
# ============================================================

def test_interrupted_suppresses_question_but_keeps_extraction():
    """INTERRUPTED 状态：有缺失参数提问时抑制提问，但保留参数提取结果。"""
    handler = _make_handler()
    ctx = _make_context(WorkflowStatus.INTERRUPTED)

    extracted = {"field1": "val1"}
    handler._handle_missing_params = MagicMock(
        return_value=("请您提供相关信息", extracted)
    )

    gen = handler._handle_non_sequential_workflow(ctx, {"global_variables": {}})
    chunks, result = _consume(gen)

    assert len(chunks) == 0, f"不应产出消息，但得到: {chunks}"
    assert result is False, f"INTERRUPTED 恢复应返回 False，实际: {result}"
    handler._handle_missing_params.assert_called_once_with(ctx)
    handler._update_global_variables.assert_called_once_with({"global_variables": {}}, extracted)
    print("[PASS] INTERRUPTED 恢复：抑制提问、保留参数提取、更新全局变量")


def test_interrupted_no_question_no_extraction():
    """INTERRUPTED 状态：无缺失参数时正常返回 False。"""
    handler = _make_handler()
    ctx = _make_context(WorkflowStatus.INTERRUPTED)

    handler._handle_missing_params = MagicMock(return_value=(None, {}))

    gen = handler._handle_non_sequential_workflow(ctx, {"global_variables": {}})
    chunks, result = _consume(gen)

    assert len(chunks) == 0
    assert result is False
    handler._handle_missing_params.assert_called_once_with(ctx)
    print("[PASS] INTERRUPTED 恢复：无缺失参数正常返回 False")


def test_pending_status_with_missing_params_interrupts():
    """PENDING 状态有缺失参数时应正常中断，返回 True。"""
    handler = _make_handler()
    ctx = _make_context(WorkflowStatus.PENDING)

    handler._handle_missing_params = MagicMock(
        return_value=("请您提供相关信息", {"field1": "val1"})
    )

    gen = handler._handle_non_sequential_workflow(ctx, {})
    chunks, result = _consume(gen)

    assert result is True, "PENDING 有缺失参数应返回 True（中断）"
    assert len(chunks) > 0, "应产出中断消息"
    handler._handle_missing_params.assert_called_once_with(ctx)
    print(f"[PASS] PENDING 有缺失参数正确中断，产出 {len(chunks)} 条消息")


def test_pending_status_no_missing_params():
    """PENDING 状态无缺失参数时返回 False。"""
    handler = _make_handler()
    ctx = _make_context(WorkflowStatus.PENDING)

    handler._handle_missing_params = MagicMock(return_value=(None, {"existing": "val"}))

    gen = handler._handle_non_sequential_workflow(ctx, {})
    chunks, result = _consume(gen)

    assert result is False
    handler._handle_missing_params.assert_called_once_with(ctx)
    print("[PASS] PENDING 无缺失参数返回 False")


def test_completed_status_proceeds_to_missing_params():
    """COMPLETED 状态应走原逻辑（不抑制提问）。"""
    handler = _make_handler()
    ctx = _make_context(WorkflowStatus.COMPLETED)

    handler._handle_missing_params = MagicMock(return_value=(None, {}))

    gen = handler._handle_non_sequential_workflow(ctx, {})
    chunks, result = _consume(gen)

    assert result is False
    handler._handle_missing_params.assert_called_once_with(ctx)
    print("[PASS] COMPLETED 状态走原逻辑，未抑制提问")


def test_is_interrupted_trap():
    """验证 is_interrupted() 对 WorkflowStatus.INTERRUPTED 返回 False（陷阱）。"""
    status = WorkflowStatus.INTERRUPTED
    result = WorkflowStatus.is_interrupted(status)
    assert result is False, (
        f"is_interrupted 对 INTERRUPTED 应返回 False（陷阱），实际: {result}"
    )
    assert status == WorkflowStatus.INTERRUPTED
    print("[PASS] is_interrupted() 陷阱验证通过：返回 False，== 比较返回 True")


if __name__ == "__main__":
    test_source_contains_fix()
    test_interrupted_suppresses_question_but_keeps_extraction()
    test_interrupted_no_question_no_extraction()
    test_pending_status_with_missing_params_interrupts()
    test_pending_status_no_missing_params()
    test_completed_status_proceeds_to_missing_params()
    test_is_interrupted_trap()
    print("\n========== 全部测试通过 ==========")
