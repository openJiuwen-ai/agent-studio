# -*- coding: UTF-8 -*-
"""workflow LLM 节点遥测接线契约（issue #1583 第 7 节）。

链路：任务创建点把 trace_handlers 放进 input_data.runtime_data →
workflow_handler 在两处工作流 astream 消费点经 workflow_trace_scope 绑定
ContextVar 作用域 → llm_chain 取用并派生 manager 发射 on_llm_start/end/
error。controllers / task_planner / handler 的 import 链穿透
psycopg2 / SpiffWorkflow 等单测环境缺失依赖，行为面已由
test_llm_chain_telemetry.py 覆盖，这里以 AST 契约锁定接线不静默丢失。
"""

import ast
import os

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


def _load_tree(rel_path):
    with open(os.path.join(_REPO_ROOT, rel_path), encoding="utf-8") as f:
        return ast.parse(f.read())


def _method_of(tree, class_name, method_name):
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if item.name == method_name:
                        return item
    return None


def _func_of(tree, func_name):
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == func_name:
                return node
    return None


def _dict_key(node, key):
    """dict 字面量里取指定键的值节点；非 dict / 无键返回 None。"""
    if not isinstance(node, ast.Dict):
        return None
    for k, v in zip(node.keys, node.values):
        if isinstance(k, ast.Constant) and k.value == key:
            return v
    return None


def _calls_with_attr(node, attr):
    return [
        call
        for call in ast.walk(node)
        if isinstance(call, ast.Call) and getattr(call.func, "attr", None) == attr
    ]


def _has_runtime_data_trace_handlers(method):
    """input_data 字面量含 runtime_data → {trace_handlers: ...} 结构。"""
    for node in ast.walk(method):
        if not isinstance(node, ast.Assign):
            continue
        inner = _dict_key(node.value, "runtime_data")
        if inner is not None and _dict_key(inner, "trace_handlers") is not None:
            return True
    return False


class TestTaskCreationSites:
    """三处 WORKFLOW_START 任务创建点随 input_data 下发 trace_handlers。"""

    @staticmethod
    def test_rule_module_start_task_carries_trace_handlers():
        method = _method_of(
            _load_tree("jiuwen/controller/task_planner/rule_modules/rule_module.py"),
            "RuleModule",
            "create_workflow_start_task",
        )
        assert method is not None
        assert _has_runtime_data_trace_handlers(method)

    @staticmethod
    def test_global_intent_task_signature_and_payload():
        tree = _load_tree("jiuwen/controller/task_planner/rule_modules/rule_module.py")
        method = _method_of(tree, "RuleModule", "create_global_intent_task")
        assert method is not None
        arg_names = [a.arg for a in method.args.args]
        assert "trace_handlers" in arg_names
        assert _has_runtime_data_trace_handlers(method)
        # 中断消息变体：把 msg.runtime_data 的 trace_handlers 透传为第三参
        caller = _method_of(
            tree, "RuleModule", "create_global_intent_task_by_interrupt_message"
        )
        calls = _calls_with_attr(caller, "create_global_intent_task")
        assert calls and len(calls[0].args) == 3

    @staticmethod
    def test_controller_planner_intent_task_passes_message_handlers():
        tree = _load_tree(
            "jiuwen/controller/task_planner/planners/controller_planner.py"
        )
        found = False
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and getattr(node.func, "attr", None) == "create_global_intent_task"
                and len(node.args) == 3
            ):
                found = True
        assert found, "controller_planner 须透传 message 的 trace_handlers"

    @staticmethod
    def test_plan_execute_mode_stash_and_task_payload():
        tree = _load_tree(
            "jiuwen/controller/agent/control_mode/plan_execute_mode.py"
        )
        stream = next(
            n
            for n in ast.walk(tree)
            if isinstance(n, ast.AsyncFunctionDef) and n.name == "stream"
        )
        stashed = any(
            isinstance(node, ast.Assign)
            and isinstance(node.targets[0], ast.Attribute)
            and node.targets[0].attr == "_trace_handlers"
            and isinstance(node.value, ast.Attribute)
            and node.value.attr == "trace_handlers"
            for node in ast.walk(stream)
        )
        assert stashed, "stream 须暂存 request.trace_handlers"

        method = _method_of(tree, "PlanExecuteMode", "_create_workflow_task")
        assert method is not None
        assert _has_runtime_data_trace_handlers(method)


class TestWorkflowHandlerScopeBinding:
    """workflow_handler 两处工作流 astream 消费点绑定遥测作用域。"""

    @staticmethod
    def test_imports_scope_helper():
        tree = _load_tree(
            "jiuwen/controller/task_executor/handler/workflow_handler.py"
        )
        imported = any(
            isinstance(node, ast.ImportFrom)
            and node.module == "jiuwen.insight.workflow_trace_scope"
            and any(a.name == "workflow_trace_scope" for a in node.names)
            for node in ast.walk(tree)
        )
        assert imported

    @staticmethod
    def test_stream_execute_workflow_wraps_consumption_in_scope():
        tree = _load_tree(
            "jiuwen/controller/task_executor/handler/workflow_handler.py"
        )
        method = _method_of(
            tree, "WorkflowHandler", "_stream_execute_workflow"
        )
        assert method is not None
        scopes = [
            node
            for node in ast.walk(method)
            if isinstance(node, ast.With)
            and any(
                isinstance(item.context_expr, ast.Call)
                and getattr(item.context_expr.func, "id", None)
                == "workflow_trace_scope"
                for item in node.items
            )
        ]
        assert scopes, "astream 消费须在 workflow_trace_scope 内"
        # 消费调用（_stream_handle_workflow_execute）确实在作用域块里
        assert any(_calls_with_attr(scope, "_stream_handle_workflow_execute") for scope in scopes)

    @staticmethod
    def test_exec_workflow_wraps_function_call_path_in_scope():
        tree = _load_tree(
            "jiuwen/controller/task_executor/handler/workflow_handler.py"
        )
        method = _method_of(tree, "WorkflowHandler", "_exec_workflow")
        assert method is not None
        scopes = [
            node
            for node in ast.walk(method)
            if isinstance(node, ast.With)
            and any(
                isinstance(item.context_expr, ast.Call)
                and getattr(item.context_expr.func, "id", None)
                == "workflow_trace_scope"
                for item in node.items
            )
        ]
        assert scopes, "react 函数调用路径的 astream 消费须在作用域内"
        assert any(_calls_with_attr(scope, "astream") for scope in scopes)


class TestLLMChainInstrumentation:
    """llm_chain 的作用域取用与三条路径的发射接线。"""

    @staticmethod
    def test_imports_scope_reader():
        tree = _load_tree("jiuwen/extension/workflow_node/llm_chain.py")
        imported = any(
            isinstance(node, ast.ImportFrom)
            and node.module == "jiuwen.insight.workflow_trace_scope"
            and any(a.name == "current_workflow_trace_manager" for a in node.names)
            for node in ast.walk(tree)
        )
        assert imported

    @staticmethod
    def test_stream_dispatch_passes_telemetry_to_both_paths():
        tree = _load_tree("jiuwen/extension/workflow_node/llm_chain.py")
        method = _method_of(tree, "LLMChain", "stream")
        assert method is not None
        for helper in ("_stream_thinking_enabled", "_stream_real_time"):
            calls = _calls_with_attr(method, helper)
            assert calls, f"stream 须调用 {helper}"
            assert any(
                any(kw.arg == "oj_telemetry" for kw in call.keywords)
                for call in calls
            ), f"调用 {helper} 须传 oj_telemetry"

    @staticmethod
    def test_stream_helpers_accept_telemetry_and_emit_end():
        tree = _load_tree("jiuwen/extension/workflow_node/llm_chain.py")
        for helper in ("_stream_thinking_enabled", "_stream_real_time"):
            method = _method_of(tree, "LLMChain", helper)
            assert method is not None
            assert "oj_telemetry" in [a.arg for a in method.args.args]
            assert _calls_with_attr(method, "on_llm_end"), f"{helper} 须发射 on_llm_end"

    @staticmethod
    def test_invoke_emits_lifecycle_events():
        tree = _load_tree("jiuwen/extension/workflow_node/llm_chain.py")
        method = _method_of(tree, "LLMChain", "invoke")
        assert method is not None
        for event in ("on_llm_start", "on_llm_end", "on_llm_error"):
            assert _calls_with_attr(method, event), f"invoke 须发射 {event}"
