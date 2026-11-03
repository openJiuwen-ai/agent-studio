#  Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
"""Basic definition of workflow."""

import ast
import re
from datetime import datetime
from typing import Optional, Union

from jiuwen.common.exception import JiuWenBaseException
from jiuwen.common.exception.status_code import StatusCode
from jiuwen.orchestration import Invokable
from jiuwen.orchestration.flow.component_class_pool import component_class_pool
from jiuwen.orchestration.flow.components import (
    End,
    LLMChain,
    FlowApi,
    Questioner,
    FlowMessage,
    Branch,
    IntentDetection,
    Start,
    Extractor,
    ExceptionInfo,
    FlowCard,
    FlowStreamTransform,
)
from jiuwen.orchestration.flow.components.agent import Agent
from jiuwen.orchestration.flow.components.flow_agent import FlowAgent
from jiuwen.orchestration.flow.components.flow_aggregate import FlowAggregate
from jiuwen.orchestration.flow.components.flow_input import FlowInput
from jiuwen.orchestration.flow.components.flow_mcp import FlowMcp
from jiuwen.orchestration.flow.components.loop import Loop, SetVariable
from jiuwen.orchestration.flow.components.sub_workflow import SubWorkflow
from jiuwen.orchestration.flow.components.util import find_references
from jiuwen.orchestration.flow.constant import (
    EXCEPTION_TIMEOUT,
    EXCEPTION_RETRY_TIMES,
    EXCEPTION_HANDLE_TYPE,
    EXCEPTION_DEFAULT_OUTPUTS,
    EXCEPTION_HANDLE_INTERRUPT,
    EXCEPTION_HANDLE_DEFAULT_OUTPUTS,
    EXCEPTION_HANDLE_ERROR_BRANCH,
    DEFAULT_EXECUTION_NODE_TIMEOUT,
    EXCEPTION_EXCEPTION_PROCESS,
)
from jiuwen.orchestration.flow.constant import SYSTEM_FIELDS, USER_FIELDS
from jiuwen.orchestration.flow.enum import NodeType, ExecutionStatus
from jiuwen.orchestration.flow.model.workflow_data_class import WorkflowMetadata
from jiuwen.orchestration.flow.runtime_context import RuntimeContext
from jiuwen.orchestration.flow.state import State, NodeSpec
from jiuwen.orchestration.utils import Output, Input

_INPUTS = "inputs"
_RESULT = "result"
_CONFIGS = "configs"
_OUTPUTS = "outputs"
_BRANCHES = "branches"
_SOURCE_TYPE = "sourceType"
_TYPE = "type"
_ID = "id"
_BOOL_EXPRESSION = "boolExpression"
_NODE_TYPE = "Node"
_SWITCH_NODE_TYPE = "SwitchNode"


class ExceptionProcess:
    is_config: bool = False
    timeout: float
    retry_times: int
    handle_type: str
    default_outputs: dict[str, any]


class Node:
    """Definition of workflow node."""

    def __init__(
        self, node_info, runtime_context, invokable=None, from_spec: bool = False
    ):
        self.id = node_info.get("id", "")
        self.type = node_info.get("type", "")
        self.name = node_info.get("name", "")
        self.configs = node_info.get("configs", {})
        self.inputs = node_info.get("inputs", {})
        self.outputs = node_info.get("outputs", {})
        self.state = node_info.get("state", State()) if not from_spec else State()
        self.action_reusable = None
        # invokable
        if isinstance(invokable, Invokable):
            self.action = invokable
        else:
            self.action = self.get_invokable_from_configs(runtime_context)
        self.node_spec = NodeSpec(
            node_config=node_info, invokable=self.action_reusable, node_type=_NODE_TYPE
        )
        # exception config
        exception_process = self.configs.get(EXCEPTION_EXCEPTION_PROCESS, {})
        self.exception_config = ExceptionProcess()
        if exception_process:
            self.exception_config.is_config = True
        self.exception_config.timeout = exception_process.get(
            EXCEPTION_TIMEOUT, DEFAULT_EXECUTION_NODE_TIMEOUT
        )
        if (
            not isinstance(self.exception_config.timeout, (float, int))
            or self.exception_config.timeout < 0
        ):
            self.exception_config.timeout = DEFAULT_EXECUTION_NODE_TIMEOUT
        self.exception_config.retry_times = exception_process.get(
            EXCEPTION_RETRY_TIMES, 0
        )
        if (
            not isinstance(self.exception_config.retry_times, int)
            or self.exception_config.retry_times < 0
        ):
            self.exception_config.retry_times = 0
        self.exception_config.handle_type = exception_process.get(
            EXCEPTION_HANDLE_TYPE, EXCEPTION_HANDLE_INTERRUPT
        )
        if not isinstance(
            self.exception_config.handle_type, str
        ) or self.exception_config.handle_type not in [
            EXCEPTION_HANDLE_INTERRUPT,
            EXCEPTION_HANDLE_DEFAULT_OUTPUTS,
            EXCEPTION_HANDLE_ERROR_BRANCH,
        ]:
            self.exception_config.handle_type = EXCEPTION_HANDLE_INTERRUPT
        self.exception_config.default_outputs = exception_process.get(
            EXCEPTION_DEFAULT_OUTPUTS, {}
        )

    @staticmethod
    def construct_from_spec(
        node_spec: NodeSpec, runtime_context: RuntimeContext = None
    ) -> "Node":
        """
        Construct workflow node from spec
        """
        if node_spec.invokable is None:
            return Node(node_spec.node_config, runtime_context, from_spec=True)
        return Node(
            node_spec.node_config,
            runtime_context,
            invokable=node_spec.invokable,
            from_spec=True,
        )

    def get_invokable_from_configs(self, runtime_context):
        """Get invokable from configs."""
        invokable = None
        metadata = WorkflowMetadata(
            node_id=self.id,
            node_type=self.type,
            node_name=self.name,
            node_state=self.state,
        )

        # 创建节点类型与类的映射字典
        node_type_mapping = {
            NodeType.START.value: (Start, False),
            NodeType.LLM.value: (LLMChain, True),
            NodeType.API.value: (FlowApi, True),
            NodeType.END.value: (End, False),
            NodeType.QUESTIONER.value: (Questioner, True),
            NodeType.MESSAGE.value: (FlowMessage, False),
            NodeType.CARD.value: (FlowCard, False),
            NodeType.STREAM_TRANSFORM.value: (FlowStreamTransform, False),
            NodeType.BRANCH.value: (Branch, False),
            NodeType.INTENT_DETECTION.value: (IntentDetection, False),
            NodeType.SUB_WORKFLOW.value: (SubWorkflow, False),
            NodeType.AGGREGATE.value: (FlowAggregate, False),
            NodeType.INPUT.value: (FlowInput, True),
            NodeType.LOOP.value: (Loop, True),
            NodeType.SET_VARIABLE.value: (SetVariable, False),
            NodeType.AGENT.value: (Agent, True),
            NodeType.FLOW_AGENT.value: (FlowAgent, True),
            NodeType.MCP.value: (FlowMcp, True),
            NodeType.EXTRACTOR.value: (Extractor, True),
        }

        # 根据节点类型创建实例
        if self.type in node_type_mapping:
            cls, need_init = node_type_mapping[self.type]
            # 初始化 Start Aggregate
            if self.type in {NodeType.START.value, NodeType.AGGREGATE.value}:
                invokable = cls(conf=self.configs)
                self.action_reusable = invokable
            else:
                if need_init:
                    invokable = cls()
                    invokable.init(
                        conf=self.configs,
                        runtime_context=runtime_context,
                        metadata=metadata,
                    )
                else:
                    invokable = cls(
                        conf=self.configs,
                        runtime_context=runtime_context,
                        metadata=metadata,
                    )
        # 初始化 exception_info
        elif self.type == NodeType.ERROR_END.value:
            invokable = ExceptionInfo(self.id, self.name, self.type)
            invokable.init(configs={})
        # 自定义组件
        else:
            invokable = self.init_custom_component(runtime_context, metadata)
        return invokable

    def init_custom_component(self, runtime_context, metadata):
        """Init custom component"""
        comp = component_class_pool.create_component_instance(self.type)
        comp.init(conf=self.configs, runtime_context=runtime_context, metadata=metadata)
        return comp

    def error_to_output(self):
        """发生异常时，走默认值或者异常分支时，状态按正常结束算"""
        self.action.error_to_output()

    def reset(self):
        """组件状态重置"""
        if self.action:
            return self.action.reset()
        return True

    def invoke(self, inputs: Input, **kwargs) -> Output:
        """Execute node."""
        default_res = {}
        if self.action:
            return self.action.invoke(inputs, **kwargs)
        # for code check
        return default_res.get("")

    def get_node_status(self):
        """获取节点状态"""
        if self.action:
            return self.action.get_node_status()
        return ExecutionStatus.START

    async def ainvoke(self, inputs: Input, **kwargs) -> Output:
        """Async execute node."""
        default_res = None
        if self.action:
            return await self.action.ainvoke(inputs, **kwargs)
        return default_res

    def stream(self, inputs: Input, **kwargs) -> Output:
        """node streaming"""
        default_res = None
        if self.action:
            return self.action.stream(inputs, **kwargs)
        return default_res

    async def astream(self, inputs: Input, **kwargs) -> Output:
        """Async node streaming."""
        default_res = None
        if self.action:
            return await self.action.astream(inputs, **kwargs)
        return default_res

    def init(
        self, conf: dict, runtime_context: RuntimeContext, metadata: WorkflowMetadata
    ):
        """node init"""
        default_res = None
        if self.action:
            return self.action.init(
                conf=conf, runtime_context=runtime_context, metadata=metadata
            )
        return default_res

    def is_ref_input(self, input_name):
        """check whether user input sourceType is reference"""
        user_inputs_configs = self.configs.get(USER_FIELDS, {}).get(_INPUTS, [])
        for user_inputs_config in user_inputs_configs:
            if (
                user_inputs_config.get(_ID) == input_name
                and user_inputs_config.get(_SOURCE_TYPE) == "ref"
            ):
                return True
        return False


class SwitchNode(Node):
    """Branch node."""

    # 字符串字面量（单/双引号，支持转义）。安全检查前先剥离，
    # 避免把字面量的"内容"当成标识符或非法字符来判定（如 'open'、'a@b.com'）。
    _STR_LITERAL_RE = re.compile(r"'(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\"")

    def __init__(self, node_info, runtime_context, from_spec: bool = False):
        # 意图分类组件已在外部进行Node实例化，所以此处跳过
        if node_info.get(_TYPE) != NodeType.INTENT_DETECTION.value:
            if node_info.get(_TYPE) == NodeType.BRANCH.value:
                # 针对于分支组件，IR当前没有inputs与outputs，此处构造
                node_info = self._construct_inputs_and_outputs_of_branch(node_info)
            super().__init__(node_info, runtime_context, from_spec=from_spec)
        self.branches = {}
        for branch in node_info.get(_CONFIGS, {}).get(_BRANCHES, []):
            expression_str = branch.get(_BOOL_EXPRESSION, "")
            safe_expr_for_check = self._preprocess_expression(expression_str)
            if not self.safe_check(safe_expr_for_check):
                node_id = node_info.get(_ID, "")
                node_name = node_info.get("name", "")
                node_type = node_info.get(_TYPE, "")
                raise JiuWenBaseException(
                    error_code=StatusCode.WORKFLOW_BRANCH_EXPRESSION_ERROR.code,
                    message=(
                        f"{StatusCode.WORKFLOW_BRANCH_EXPRESSION_ERROR.errmsg}"
                        f", node={node_name}({node_id}), branch={branch.get(_ID, '')}"
                        f", expression={expression_str}"
                    ),
                    node_id=node_id,
                    node_name=node_name,
                    node_type=node_type,
                )
            self.branches.update({branch[_ID]: expression_str})
        self.node_spec = NodeSpec(node_config=node_info, node_type=_SWITCH_NODE_TYPE)

    @staticmethod
    def construct_from_spec(
        node_spec: NodeSpec, runtime_context: RuntimeContext = None
    ) -> "Node":
        """
        Construct workflow node from spec
        """
        return SwitchNode(node_spec.node_config, runtime_context, from_spec=True)

    @staticmethod
    def _construct_inputs_and_outputs_of_branch(node_info: dict) -> dict:
        inputs = {}
        params_set = set()
        for branch in node_info[_CONFIGS][_BRANCHES]:
            conditions: str = branch.get(_BOOL_EXPRESSION, "")
            references = find_references(conditions)
            for each in references:
                if each not in params_set:
                    inputs[each] = ""
                    params_set.add(each)
        node_info.update(dict(inputs=inputs))
        node_info.update(dict(outputs={SYSTEM_FIELDS: {_RESULT: ""}}))
        system_fields_in_configs = node_info.get(_CONFIGS, {}).get(SYSTEM_FIELDS, {})
        system_fields_in_configs.update({_OUTPUTS: {_ID: _RESULT, _TYPE: "string"}})
        return node_info

    def safe_check(self, expression_str: str) -> bool:
        """
        Perform security verification on branch expression strings to prevent code injection attacks
        """
        if not expression_str or not isinstance(expression_str, str):
            return True

        stripped = expression_str.strip()
        if not stripped:
            return True

        allowed_pattern = r'^[a-zA-Z0-9_.$\s+\-*/%()<>!=&|~^?:,\[\]{}\'"\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]+$'
        # 先剥离字符串字面量再校验字符白名单：'a@b.com'、'x#y'、'a;b' 这类
        # 合法业务取值的内容不应被判定为"非法字符"。
        if not re.match(allowed_pattern, self._STR_LITERAL_RE.sub("''", expression_str)):
            return False

        dangerous_keywords = [
            r"\bexec\b",
            r"\beval\b",
            r"\bcompile\b",
            r"\bopen\b",
            r"\b__import__\b",
            r"\bgetattr\b",
            r"\bsetattr\b",
            r"\bdelattr\b",
            r"\bhasattr\b",
            r"\bvars\b",
            r"\blocals\b",
            r"\bglobals\b",
            r"\bdir\b",
            r"\bhelp\b",
            r"\binput\b",
            r"\bos\b",
            r"\bsys\b",
            r"\bsubprocess\b",
            r"\bshutil\b",
            r"\bimportlib\b",
            r"\bpathlib\b",
            r"\bglob\b",
            r"\bsocket\b",
            r"__class__",
            r"__mro__",
            r"__subclasses__",
            r"__bases__",
            r"__dict__",
            r"__globals__",
            r"__builtins__",
            r"__code__",
            r"__func__",
            r"__self__",
            r"__closure__",
            r"__module__",
            r"__file__",
            r"__path__",
            r"__package__",
            r"__loader__",
            r"__spec__",
            r"__getattribute__",
            r"__getattr__",
            r"\.system\(",
            r"\.popen\(",
            r"\.spawn\(",
            r"\.exec\(",
            r"\.eval\(",
            r"\.compile\(",
            r"\\x[0-9a-fA-F]{2}",
            r"\\u[0-9a-fA-F]{4}",
            r"chr\(",
            r"ord\(",
            r"unichr\(",
            r"lambda\s*:",
        ]

        try:
            tree = ast.parse(stripped, mode="eval")
        except Exception:
            return False

        # 危险关键词只匹配"标识符"（Name / Attribute.attr / Call.func），
        # 字符串、数字字面量的"内容"不参与匹配 —— 否则 'open'、'os'、'sys'、'input'
        # 这类合法业务取值会被误判为注入风险。
        identifier_skeleton = " ".join(self._iter_identifiers(tree.body))
        for pattern in dangerous_keywords:
            if re.search(pattern, identifier_skeleton, re.IGNORECASE):
                return False

        return self._is_ast_safe(tree.body)

    def _iter_identifiers(self, node):
        """遍历 AST，产出标识符骨架。

        调用节点产出 ``名字(`` 形式，以保证 ``chr\\(`` / ``ord\\(`` / ``unichr\\(``
        这类带左括号的关键词模式仍可命中。
        """
        if isinstance(node, ast.Name):
            yield node.id
        elif isinstance(node, ast.Attribute):
            yield node.attr
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                yield func.id + "("
            elif isinstance(func, ast.Attribute):
                yield func.attr + "("
        elif isinstance(node, ast.Lambda):
            # 产出 "lambda:" 以保证 dangerous_keywords 中的 r"lambda\s*:" 能命中；
            # 否则骨架里只有 "lambda"（无冒号），lambda 表达式会被放行
            yield "lambda:"
        for child in ast.iter_child_nodes(node):
            yield from self._iter_identifiers(child)

    def _is_ast_safe(self, node) -> bool:
        """Recursively validate AST node safety."""
        if isinstance(node, ast.Name):
            return self._is_name_safe(node.id)

        if isinstance(node, ast.Attribute):
            return self._is_attribute_safe(node)

        if isinstance(node, ast.Call):
            return self._is_call_safe(node)

        if isinstance(node, ast.Lambda):
            return False

        return all(self._is_ast_safe(child) for child in ast.iter_child_nodes(node))

    def _is_name_safe(self, name: str) -> bool:
        """Check if a variable/function name is safe."""
        if name in ["exec", "eval", "compile", "open", "__import__"]:
            return False
        if name.startswith("__") and name.endswith("__"):
            return False
        return True

    def _is_attribute_safe(self, node: ast.Attribute) -> bool:
        """Check if an attribute access (e.g., obj.attr) is safe."""
        attr_name = node.attr
        if attr_name.startswith("__"):
            return False
        if attr_name in [
            "system",
            "popen",
            "spawn",
            "exec",
            "eval",
            "compile",
            "globals",
            "locals",
            "builtins",
            "mro",
            "subclasses",
        ]:
            return False
        return self._is_ast_safe(node.value)

    def _is_call_safe(self, node: ast.Call) -> bool:
        """Check if a function/method call is safe."""
        func = node.func

        if isinstance(func, ast.Name):
            func_name = func.id
            if func_name in [
                "exec",
                "eval",
                "compile",
                "open",
                "__import__",
                "getattr",
                "setattr",
                "delattr",
                "hasattr",
                "vars",
            ]:
                return False

        elif isinstance(func, ast.Attribute):
            method_name = func.attr
            if method_name in ["system", "popen", "spawn"]:
                return False
            # Check the object part (e.g., os in os.system)
            if not self._is_ast_safe(func.value):
                return False

        else:
            # 被调用对象既不是 Name 也不是 Attribute（如 Lambda、Subscript、
            # 嵌套 Call）时，递归校验 func 本身，避免 (lambda: 0)()、arr[0]()
            # 这类表达式绕过安全检查
            if not self._is_ast_safe(func):
                return False

        return all(self._is_ast_safe(arg) for arg in node.args) and all(
            self._is_ast_safe(kw.value) for kw in node.keywords
        )

    def _preprocess_expression(self, expr: str) -> str:
        """Convert business DSL expressions into legal Python expressions for security verification"""
        if not expr:
            return expr

        expr = expr.replace("&&", "and")
        expr = expr.replace("||", "or")
        expr = expr.replace("not_in", "not in")
        expr = expr.replace("in_", "in")

        var_counter = 0

        # Replacing the reference variable of an expression with a constant string has
        # no business significance for parsing the expression.
        def replace_placeholder(match):
            nonlocal var_counter
            var_counter += 1
            return f"var{var_counter}"

        processed = re.sub(r"\$\{[^}]+\}", replace_placeholder, expr)

        return processed


class BaseWorkflow:
    """Base class of workflow."""

    name: str
    description: str
    nodes: Union[dict, list]
    start_time: Optional[datetime] = None
    finish_time: Optional[datetime] = None
