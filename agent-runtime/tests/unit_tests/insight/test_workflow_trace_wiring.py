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
    """workflow_handler 两处工作流 astream 消费点绑定遥测作用域。

    消费经 scoped_astream 包装：作用域只在步进内层流期间绑定，跨
    yield 零残留——直接 `with workflow_trace_scope(...)` 包住含 yield
    的 async for 会让绑定滞留在消费方 Task 上下文、兄弟任务错误继承
    （检视意见），该形态不得回潮。
    """

    @staticmethod
    def _scoped_astream_calls(method):
        """method 内 scoped_astream(...) 调用列表。"""
        return [
            node
            for node in ast.walk(method)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "scoped_astream"
        ]

    @staticmethod
    def _lambda_calls_attr(call, attr):
        """scoped_astream 首参 lambda 的函数体是否调用 <attr>。"""
        if not call.args or not isinstance(call.args[0], ast.Lambda):
            return False
        return bool(_calls_with_attr(call.args[0], attr))

    @staticmethod
    def test_imports_scope_helper():
        tree = _load_tree(
            "jiuwen/controller/task_executor/handler/workflow_handler.py"
        )
        imported = any(
            isinstance(node, ast.ImportFrom)
            and node.module == "jiuwen.insight.workflow_trace_scope"
            and any(a.name == "scoped_astream" for a in node.names)
            for node in ast.walk(tree)
        )
        assert imported

    def test_stream_execute_workflow_consumes_via_scoped_astream(self):
        tree = _load_tree(
            "jiuwen/controller/task_executor/handler/workflow_handler.py"
        )
        method = _method_of(
            tree, "WorkflowHandler", "_stream_execute_workflow"
        )
        assert method is not None
        calls = self._scoped_astream_calls(method)
        assert calls, "_stream_execute_workflow 须经 scoped_astream 消费"
        assert any(
            self._lambda_calls_attr(c, "_stream_handle_workflow_execute")
            for c in calls
        ), "scoped_astream 须包住 _stream_handle_workflow_execute 内层流"

    def test_exec_workflow_consumes_via_scoped_astream(self):
        tree = _load_tree(
            "jiuwen/controller/task_executor/handler/workflow_handler.py"
        )
        method = _method_of(tree, "WorkflowHandler", "_exec_workflow")
        assert method is not None
        calls = self._scoped_astream_calls(method)
        assert calls, "react 函数调用路径的 astream 消费须经 scoped_astream"
        assert any(
            self._lambda_calls_attr(c, "astream") for c in calls
        ), "scoped_astream 须包住 workflow.astream 内层流"

    def test_no_bare_with_scope_around_yield_loops(self):
        """旧形态（with workflow_trace_scope 包住含 yield 的循环）不得回潮。"""
        tree = _load_tree(
            "jiuwen/controller/task_executor/handler/workflow_handler.py"
        )
        for node in ast.walk(tree):
            if isinstance(node, ast.With) and any(
                isinstance(item.context_expr, ast.Call)
                and getattr(item.context_expr.func, "id", None)
                == "workflow_trace_scope"
                for item in node.items
            ):
                raise AssertionError(
                    "workflow_handler 不得直接 with workflow_trace_scope——"
                    "须经 scoped_astream 收敛绑定（检视意见）"
                )


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
