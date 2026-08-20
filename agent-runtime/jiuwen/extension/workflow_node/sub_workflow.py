# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.

"""
SubWorkflow - 子工作流组件

迁移自商用版本 jiuwen/orchestration/flow/components/sub_workflow.py，
适配开源版本 openjiuwen 框架。

功能特性:
- 在父工作流中嵌套执行子工作流
- 支持流式和非流式两种执行方式
- 支持交互中断/恢复
- 支持 REQUEST 变量同步
- 支持状态管理（reset/load_state/get_state）

设计说明:
- 继承 WorkflowComponent（openjiuwen 标准组件基类）
- 使用 Session 进行状态管理和交互中断
- 使用 context.get_messages() 获取对话历史
- 使用 session.get_global_state("workflow_instance_dict") 获取子工作流实例
- 使用 session.write_stream() 输出流式数据
"""

import asyncio
import os
import re
from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
from typing import Any, AsyncIterator, Optional

from agent_runtime.common.session_state_access import (
    dump_state_info,
    get_state_info,
)
from jiuwen.extension.patches.workflow_sub_stream_patch import _interrupt_output_schema
from jiuwen.extension.workflow_node.utils import (
    JiuWenBaseException,
    WorkflowAbortException,
    get_workflow_param,
)
from openjiuwen.core.common.constants.constant import INTERACTIVE_INPUT, INTERACTION
from openjiuwen.core.common.logging import workflow_logger, LogEventType
from openjiuwen.core.context_engine import ModelContext
from openjiuwen.core.foundation.llm import UserMessage
from openjiuwen.core.graph.executable import Input, Output
from openjiuwen.core.graph.pregel import GraphInterrupt
from openjiuwen.core.session import (
    WORKFLOW_EXECUTE_TIMEOUT,
    WORKFLOW_STREAM_FRAME_TIMEOUT,
)
from openjiuwen.core.session.interaction.interactive_input import InteractiveInput
from openjiuwen.core.session.node import Session
from openjiuwen.core.session.stream.base import CustomSchema
from openjiuwen.core.session.stream.base import OutputSchema
from openjiuwen.core.workflow.components.component import WorkflowComponent
from openjiuwen.core.workflow.workflow import Workflow
from pydantic import BaseModel, Field, ValidationError

LOG_VERBOSE_MODE = os.getenv("LOG_VERBOSE", "false").lower() == "true"

USER_FIELDS = "userFields"
SYSTEM_FIELDS = "systemFields"
PRE_DEFINE_FIELDS = "preDefineFields"
WORKFLOW_INSTANCE_DICT = "workflow_instance_dict"
GLOBAL_VARIABLES = "global_variables"
REQUEST_VARIABLES = "_request"
MESSAGE_NODE_END = "message_end"

DEFAULT_SUB_WORKFLOW_TIMEOUT = 300
DEFAULT_STREAM_FRAME_TIMEOUT = 120
DEFAULT_FIRST_FRAME_TIMEOUT = 10

# 与各交互组件 session.update_state 持久化 key 保持一致（见 ir_converter 支持的组件）
QUESTIONER_STATE_KEY = "questioner_state"
FLOW_QA_STATE_KEY = "flow_qa_state"
FLOW_INPUT_STATE_KEY = "flow_input_state"

# 子工作流 stream 结束时 comp_state 兜底扫描：需 session.update_state 写入
# {key: {status, question, ...}} 且 status=user_interact 的组件 state key。
# 新增同类中断组件时，在此 tuple 追加一项即可。
CHILD_INTERRUPT_STATE_KEYS: tuple[str, ...] = (
    QUESTIONER_STATE_KEY,
    FLOW_QA_STATE_KEY,
    FLOW_INPUT_STATE_KEY,
)

# 子工作流 stream 结束时 comp_state 兜底扫描：需 session.update_state 写入
# {key: {status, question, ...}} 且 status=user_interact 的组件 state key。
# 新增同类中断组件时，在此 tuple 追加一项即可。
CHILD_INTERRUPT_STATE_KEYS: tuple[str, ...] = (
    QUESTIONER_STATE_KEY,
    FLOW_QA_STATE_KEY,
    FLOW_INPUT_STATE_KEY,
)
from openjiuwen.core.session.utils import is_ref_path, extract_origin_key
GLOBAL_REF_PREFIX = "MEMORY_VARIABLE."

class ExecutionStatus(str, Enum):
    """执行状态枚举"""

    START = "start"
    END = "end"
    USER_INTERACT = "user_interact"


class SubWorkflowStatusCode(Enum):
    """SubWorkflow 组件专用错误码"""

    CONFIG_VALIDATION_ERROR = (
        101160,
        "sub_workflow config validation error, reason: {error_msg}",
    )
    WORKFLOW_INSTANCE_NOT_FOUND = (
        101161,
        "sub_workflow instance not found, workflow_id: {workflow_id}",
    )
    EXECUTION_ERROR = (
        101162,
        "sub_workflow execution error, reason: {error_msg}",
    )
    STREAM_ERROR = (
        101163,
        "sub_workflow stream error, reason: {error_msg}",
    )
    EXECUTION_TIMEOUT = (
        101164,
        "sub_workflow execution timed out after {timeout}s",
    )


def build_sub_workflow_error(
    status: SubWorkflowStatusCode,
    error_msg: str = "",
    cause: Optional[Exception] = None,
    **kwargs,
) -> JiuWenBaseException:
    """构建 SubWorkflow 组件异常

    Args:
        status: 错误状态码枚举
        error_msg: 错误信息
        cause: 原始异常
        **kwargs: 额外的消息格式化参数

    Returns:
        JiuWenBaseException 实例
    """
    format_kwargs = {"error_msg": error_msg, **kwargs}
    return JiuWenBaseException(
        error_code=status.value[0],
        message=status.value[1].format(**format_kwargs),
    )


def format_pydantic_validation_error_message(error: ValidationError) -> str:
    """格式化 Pydantic 校验错误信息

    Args:
        error: Pydantic 校验错误

    Returns:
        格式化后的错误信息字符串
    """
    errors = error.errors()
    error_messages = []
    for err in errors:
        loc = ".".join(str(x) for x in err.get("loc", []))
        msg = err.get("msg", "")
        error_messages.append(f"{loc}: {msg}")
    return "; ".join(error_messages)


def sanitize_message(message: str) -> str:
    """屏蔽常见敏感字段，不区分大小写

    Args:
        message: 原始消息

    Returns:
        处理后的消息
    """
    patterns = [
        r"(secret key:\s*)(\S+)",
        r"(password:\s*)(\S+)",
        r"(access token:\s*)(\S+)",
        r"(api key:\s*)(\S+)",
    ]
    for pattern in patterns:
        message = re.sub(pattern, r"\1***", message, flags=re.IGNORECASE)
    return message


class Reference(BaseModel):
    """子工作流引用配置"""

    id: str = Field(title="子workflow对应的workflow id")
    path: str = Field(title="子workflow对应的obs中的存储路径")


class SubWorkflowConfig(BaseModel):
    """子工作流组件配置校验"""

    user_fields: dict = Field(alias="userFields", default={})
    system_fields: dict = Field(alias="systemFields")
    pre_define_fields: dict = Field(alias="preDefineFields")
    reference: Reference


@dataclass
class SubWorkflowState:
    """子工作流组件状态"""

    status: ExecutionStatus = ExecutionStatus.START


class SubWorkflow(WorkflowComponent):
    """子工作流组件

    在父工作流中嵌套执行子工作流，支持流式和非流式两种执行方式。

    Args:
        conf: 组件配置字典
    """

    def __init__(self, conf: dict, sub_workflow: Optional[Workflow] = None) -> None:
        super().__init__()
        self._conf = conf
        self._validate_config()
        self.node_state = SubWorkflowState()
        self._workflow_instance = sub_workflow
        self._node_id = conf.get("node_id", "")
        self._stream_state = None
        self._interrupt_child_node_id: Optional[str] = None
        self._pending_interact_prompt: str = ""
        self._global_var_names = None
        self._last_child_completed = False

    @staticmethod
    def _collect_global_refs_from_schema(schema, inputs, result, global_var_names):
        """Recursively collect ${global.xxx} references from nested input_schema."""
        if not isinstance(schema, dict) or not isinstance(inputs, dict):
            return
        for key, schema_value in schema.items():
            if isinstance(schema_value, str) and is_ref_path(schema_value):
                origin_key = extract_origin_key(schema_value)
                if origin_key.startswith(GLOBAL_REF_PREFIX):
                    var_name = origin_key[len(GLOBAL_REF_PREFIX):]
                    result[var_name] = inputs.get(key)
                    global_var_names.append(var_name)
            elif isinstance(schema_value, dict):
                nested_inputs = inputs.get(key, {})
                if not isinstance(nested_inputs, dict):
                    nested_inputs = {}
                SubWorkflow._collect_global_refs_from_schema(
                    schema_value, nested_inputs, result, global_var_names,
                )

    def _collect_global_vars(self, inputs: Input, session: Session) -> dict | None:
        """从 inputs 中提取全局变量值，用于调试信息记录。支持嵌套 input_schema。"""
        if not isinstance(session, Session):
            return None
        node_config = session.get_node_config()
        if not node_config or not node_config.io_configs:
            return None
        input_schema = node_config.io_configs.inputs_schema
        if not isinstance(input_schema, dict):
            return None
        if not isinstance(inputs, dict):
            return None

        result = {}
        global_var_names = []
        self._collect_global_refs_from_schema(input_schema, inputs, result, global_var_names)

        self._global_var_names = global_var_names if global_var_names else None
        return result if result else None

    def _collect_updated_memory(self, session: Session) -> dict | None:
        if not self._global_var_names:
            return None

        updated_memory = {}
        for var_name in self._global_var_names:
            val = session.get_global_state(f"{GLOBAL_REF_PREFIX}{var_name}")
            if val is None:
                val = session.get_global_state(var_name)
            updated_memory[var_name] = val
        return updated_memory

    def _validate_config(self):
        """使用 Pydantic 校验配置"""
        try:
            SubWorkflowConfig.model_validate(self._conf)
        except ValidationError as e:
            raise build_sub_workflow_error(
                SubWorkflowStatusCode.CONFIG_VALIDATION_ERROR,
                error_msg=format_pydantic_validation_error_message(e)
                if LOG_VERBOSE_MODE
                else str(type(e).__name__),
            ) from e

    def _get_timeout(self, session: Session) -> int:
        """获取子工作流执行超时时间（秒）"""
        timeout = session.get_env(WORKFLOW_EXECUTE_TIMEOUT) if session else None
        if timeout and timeout > 0:
            return timeout
        return DEFAULT_FIRST_FRAME_TIMEOUT

    def _get_frame_timeout(self, session: Session) -> int:
        """获取流式帧超时时间（秒）"""
        timeout = session.get_env(WORKFLOW_STREAM_FRAME_TIMEOUT) if session else None
        return timeout if (timeout and timeout > 0) else DEFAULT_STREAM_FRAME_TIMEOUT

    def _get_first_frame_timeout(self, session: Session) -> int:
        """获取首帧超时时间（秒）。

        必须小于父工作流 _execute_with_timeout 的超时（默认 60s），
        否则父级 timeout 会先取消整个后台任务，本组件的 graceful handler 没机会运行。
        使用固定短超时：如果首帧 10s 内未到达，说明子工作流可能是交互式的。
        """
        return DEFAULT_FIRST_FRAME_TIMEOUT

    @staticmethod
    def _status_value(status: Any) -> str:
        if status is None:
            return ""
        if isinstance(status, Enum):
            return str(status.value)
        return str(status)

    def _extract_interact_prompt(self, node_state: dict) -> str:
        for key in (*CHILD_INTERRUPT_STATE_KEYS, "question"):
            q_state = node_state.get(key)
            if isinstance(q_state, dict):
                prompt = q_state.get("question") or ""
                if prompt:
                    return prompt
            elif isinstance(q_state, str) and q_state:
                return q_state
        return ""

    def _match_interrupt_in_node_state(
        self, node_id: str, node_state: dict
    ) -> Optional[tuple[str, str]]:
        user_interact = ExecutionStatus.USER_INTERACT.value
        if self._status_value(node_state.get("status")) == user_interact:
            return node_id, self._extract_interact_prompt(node_state)

        for state_key in CHILD_INTERRUPT_STATE_KEYS:
            comp_state = node_state.get(state_key)
            if (
                isinstance(comp_state, dict)
                and self._status_value(comp_state.get("status")) == user_interact
            ):
                return node_id, comp_state.get("question") or ""

        return None

    def _find_interrupt_in_state_tree(
        self, state_root: Any
    ) -> Optional[tuple[str, str]]:
        """在 comp_state 嵌套树中查找 CHILD_INTERRUPT_STATE_KEYS 对应的 USER_INTERACT 状态。"""
        if not isinstance(state_root, dict):
            return None

        for key, value in state_root.items():
            if not isinstance(value, dict):
                continue
            matched = self._match_interrupt_in_node_state(key, value)
            if matched:
                return matched
            nested = self._find_interrupt_in_state_tree(value)
            if nested:
                return nested
        return None

    def _find_interactive_input_in_state_tree(
        self, state_root: Any, target_node_id: Optional[str] = None
    ) -> Optional[tuple[str, Any]]:
        """在 comp_state 嵌套树中递归查找 __interactive_input__ 的值。

        多层嵌套子工作流中断恢复时，父级将用户回复路由给目标 node_id，
        pregel 把 InteractiveInput 写入「某层作用域 -> 目标 node_id ->
        __interactive_input__」的嵌套路径下，而非平铺在 comp_state 顶层。
        session.get_state(f"{node_id}.{INTERACTIVE_INPUT}") 只在顶层精确查找，
        无法穿透嵌套，故需递归扫描。

        当提供 target_node_id 时，仅精确匹配该节点下的 __interactive_input__，
        避免在存在多个中断点时取到非目标节点的回复；未提供时无差别扫描兜底。

        Returns:
            Optional[tuple[str, Any]]: (所在 node_id, 原始值) 或 None
        """
        if not isinstance(state_root, dict):
            return None

        target_state = state_root.get(target_node_id)
        if isinstance(target_state, dict) and INTERACTIVE_INPUT in target_state:
            return target_node_id, target_state[INTERACTIVE_INPUT]
        for value in state_root.values():
            if not isinstance(value, dict):
                continue
            nested = self._find_interactive_input_in_state_tree(
                value, target_node_id
            )
            if nested:
                return nested
        return None

    def _session_has_interactive_input(self, session: Session) -> bool:
        """父工作流以 InteractiveInput 恢复时，checkpoint 会写入 INTERACTIVE_INPUT。"""
        return self._extract_parent_resume_query(session) is not None

    @staticmethod
    def _normalize_interactive_input_value(value: Any) -> Optional[str]:
        """将 INTERACTIVE_INPUT 的存储值规范化为字符串。"""
        if value is None:
            return None
        if isinstance(value, list):
            if not value:
                return None
            last = value[-1]
            if last is None:
                return None
            content = getattr(last, "content", last)
            if isinstance(content, str):
                return content
            if content is not None and isinstance(content, (int, float, bool)):
                return str(content)
            return None
        if isinstance(value, str):
            return value
        if isinstance(value, (int, float, bool)):
            return str(value)
        return None

    def _read_workflow_interactive_input(self, session: Session) -> Optional[str]:
        """从 session 状态读取父工作流 workflow_state 中的 INTERACTIVE_INPUT。"""
        accessors = []
        inner_session = getattr(session, "_inner", None)
        if inner_session is not None and hasattr(inner_session, "state"):
            accessors.append(inner_session.state())
        try:
            workflow_state = get_state_info(session, "workflow_state")
            if isinstance(workflow_state, dict):
                # dump 兜底：部分 Session 包装层不暴露 get_workflow_state
                wf = workflow_state.get("workflow", {})
                if isinstance(wf, dict):
                    normalized = self._normalize_interactive_input_value(
                        wf.get(INTERACTIVE_INPUT)
                    )
                    if normalized is not None:
                        return normalized
        except Exception:
            workflow_logger.debug(
                "Failed to extract interactive input from session dump", exc_info=True
            )

        for state in accessors:
            try:
                getter = getattr(state, "get_workflow_state", None)
                if getter is None:
                    continue
                normalized = self._normalize_interactive_input_value(
                    getter(INTERACTIVE_INPUT)
                )
                if normalized is not None:
                    return normalized
            except Exception:
                workflow_logger.debug(
                    "Failed to get workflow_state from accessor", exc_info=True
                )
                continue
        return None

    def _extract_parent_resume_query(self, session: Session) -> Optional[str]:
        """提取父工作流恢复时本次用户输入，优先于 Start 节点 checkpoint 中的 query。"""
        workflow_query = self._read_workflow_interactive_input(session)
        if workflow_query is not None:
            return workflow_query

        if self._interrupt_child_node_id:
            messages = (
                session.get_state(
                    f"{self._interrupt_child_node_id}.{INTERACTIVE_INPUT}"
                )
                or []
            )
            child_value = self._normalize_interactive_input_value(messages)
            if child_value is not None:
                return child_value

        # 多层嵌套兜底：父级把回复路由给目标 node_id，pregel 写入
        # comp_state[顶层作用域][目标node_id][__interactive_input__] 嵌套路径，
        # 点分查找无法穿透，递归扫描 comp_state 树取值。
        _comp_state = get_state_info(session, "comp_state")
        if _comp_state and self._interrupt_child_node_id:
            found = self._find_interactive_input_in_state_tree(
                _comp_state, self._interrupt_child_node_id
            )
            if found is not None:
                found_node_id, found_raw = found
                nested_value = self._normalize_interactive_input_value(found_raw)
                if nested_value is not None:
                    return nested_value
        return None

    def _extract_from_interactive_input(self, inputs: InteractiveInput) -> Optional[str]:
        """从 InteractiveInput 中提取用户最新输入作为兜底。

        当 _extract_parent_resume_query 的三层查找全部失败时，
        尝试直接从传入的 InteractiveInput 中获取用户回复，
        避免回退到 Start 节点 checkpoint 中的陈旧 query。

        Args:
            inputs: InteractiveInput 实例

        Returns:
            Optional[str]: 提取到的用户输入，未找到则返回 None
        """
        if not isinstance(inputs, InteractiveInput):
            return None
        # 优先从 user_inputs 中取最新值
        if inputs.user_inputs:
            last_key = list(inputs.user_inputs.keys())[-1]
            val = inputs.user_inputs[last_key]
            if val:
                return str(val)
        # 其次从 raw_inputs 中取
        if inputs.raw_inputs:
            return str(inputs.raw_inputs)
        return None

    def _should_resume_child_workflow(self, session: Session) -> bool:
        """是否应向子工作流传递 InteractiveInput 以恢复 checkpoint。

        SubWorkflow 组件每次请求都会重新实例化，node_state 不会从中断自动恢复；
        需从 session / comp_state 识别子交互组件仍处于 USER_INTERACT。
        """
        if self.node_state.status == ExecutionStatus.USER_INTERACT:
            return True
        if self._detect_child_interrupt(session):
            return True
        inner_session = getattr(session, "_inner", None)
        if self._is_parent_workflow_interrupted(inner_session):
            return True
        return self._session_has_interactive_input(session)

    async def _prepare_child_inputs(
        self,
        inputs: Input,
        session: Session,
        context: ModelContext,
        *,
        for_stream: bool,
    ) -> Any:
        """构建子工作流输入：恢复场景使用 InteractiveInput，否则使用普通 dict。"""
        is_resume = self._should_resume_child_workflow(session)
        params = await self._build_invoke_params(inputs, session, context)
        if is_resume:
            self.node_state.status = ExecutionStatus.USER_INTERACT
            resume_query = self._extract_parent_resume_query(session)
            if resume_query is None:
                # 兜底：尝试从 inputs（InteractiveInput）中直接提取用户最新输入，
                # 避免回退到 Start 节点 checkpoint 中的陈旧 query。
                resume_query = self._extract_from_interactive_input(inputs)
            if resume_query is None:
                # 所有提取方式均失败，回退到 Start 节点 checkpoint 中的 query。
                # 嵌套子工作流场景下该值通常是上一轮的陈旧输入。
                workflow_logger.warning(
                    "SubWorkflow resume: failed to extract user reply for child %s, "
                    "falling back to Start-node query=%r (may be stale)",
                    self._interrupt_child_node_id,
                    params.get("query"),
                )
            query = resume_query if resume_query is not None else params["query"]
            return self._build_child_interactive_input(query)
        memory_fields = inputs.get("memory", {})
        if not isinstance(memory_fields, dict):
            memory_fields = {}
        child_inputs = {
            **memory_fields,
            **inputs.get(USER_FIELDS, {}),
            "query": params["query"],
            "global_variables": params["global_variables"],
            "conversation_history": params["conversation_history"],
            "_REQUEST": params["global_variables"],
        }
        return child_inputs

    def _detect_child_interrupt(self, session: Session) -> Optional[tuple[str, str]]:
        """从 session 状态检测子工作流内交互组件是否处于 USER_INTERACT。

        子工作流 stream(is_sub=True) 的中断信号会写入父 StreamEmitter，但不会出现在
        子 stream 迭代器中；需要通过 comp_state 中 CHILD_INTERRUPT_STATE_KEYS 兜底识别。
        """
        if self._pending_interact_prompt:
            return (
                self._interrupt_child_node_id or session.get_component_id(),
                self._pending_interact_prompt,
            )

        self._interrupt_child_node_id = None
        comp_state = get_state_info(session, "comp_state")
        if comp_state:
            found = self._find_interrupt_in_state_tree(comp_state)
            if found:
                self._interrupt_child_node_id = found[0]
                return found

        sub_session_state = session.get_state() or {}
        if isinstance(sub_session_state, dict):
            matched = self._match_interrupt_in_node_state(
                session.get_component_id(), sub_session_state
            )
            if matched:
                self._interrupt_child_node_id = matched[0]
                return matched
            for node_id, node_state in sub_session_state.items():
                if not isinstance(node_state, dict):
                    continue
                matched = self._match_interrupt_in_node_state(node_id, node_state)
                if matched:
                    self._interrupt_child_node_id = matched[0]
                    return matched

        return None

    @staticmethod
    def _is_parent_workflow_interrupted(inner_session: Any) -> bool:
        if inner_session is None:
            return False
        try:
            workflow_state = get_state_info(inner_session, "workflow_state")
            if not isinstance(workflow_state, dict):
                return False
            return workflow_state.get("workflow", {}).get("__interrupted") is True
        except Exception:
            return False

    @staticmethod
    def _payload_dict_from_chunk(chunk: OutputSchema) -> dict:
        payload = chunk.payload
        if isinstance(payload, dict):
            return payload
        if hasattr(payload, "model_dump"):
            return payload.model_dump()
        if hasattr(payload, "id") or hasattr(payload, "value"):
            return {
                "id": getattr(payload, "id", None),
                "value": getattr(payload, "value", None),
            }
        return {}

    def _find_interaction_chunk_in_child_result(
        self, result: dict
    ) -> Optional[OutputSchema]:
        chunk = _interrupt_output_schema(result)
        if chunk is not None:
            return chunk
        stream = result.get("stream")
        if isinstance(stream, list):
            for item in reversed(stream):
                if isinstance(item, OutputSchema) and item.type == INTERACTION:
                    return item
        return None

    def _parse_normal_child_invoke_result(self, result: dict) -> tuple[str, dict]:
        response_content = result.get("answer", "") or ""
        user_fields = result.get("user_fields") or {}
        stream = result.get("stream")
        if not isinstance(stream, list) or not stream:
            return response_content, user_fields

        last = stream[-1]
        if isinstance(last, OutputSchema):
            if last.type == INTERACTION:
                return response_content, user_fields
            payload = self._payload_dict_from_chunk(last)
            response_content = (
                response_content
                or payload.get("answer", "")
                or payload.get("result", "")
            )
            user_fields = (
                user_fields
                or payload.get("userFields", {})
                or payload.get("user_fields", {})
            )
        elif isinstance(last, dict):
            response_content = response_content or last.get("answer", "")
            user_fields = (
                user_fields or last.get("userFields", {}) or last.get("user_fields", {})
            )
        return response_content, user_fields

    async def _raise_user_interact_from_chunk(
        self, session: Session, chunk: OutputSchema
    ) -> None:
        self.node_state.status = ExecutionStatus.USER_INTERACT
        payload = chunk.payload
        child_node_id = None
        if hasattr(payload, "id"):
            child_node_id = payload.id
        elif isinstance(payload, dict):
            child_node_id = payload.get("id")
        if child_node_id:
            self._interrupt_child_node_id = child_node_id
        await session.interact(self._resolve_interact_value(payload))

    @staticmethod
    def _resolve_interact_value(payload: Any) -> Any:
        """从 INTERACTION payload 提取传给 session.interact 的 value。"""
        if payload is None:
            return ""
        if isinstance(payload, str):
            return payload
        if isinstance(payload, dict):
            return payload.get("value") or payload.get("prompt") or payload
        if hasattr(payload, "value") and getattr(payload, "value", None) is not None:
            return payload.value
        return payload

    def _resolve_interact_prompt(
        self, session: Session, final_res: str, inner_session: Any
    ) -> str:
        if self._pending_interact_prompt:
            return self._pending_interact_prompt
        if final_res:
            return final_res
        detected = self._detect_child_interrupt(session)
        if detected:
            return detected[1]
        if self._is_parent_workflow_interrupted(inner_session):
            return final_res
        return final_res

    async def _emit_sub_workflow_user_interact(
        self,
        session: Session,
        inner_session: Any,
        final_res: str,
        final_val: dict,
        *,
        log_reason: str,
    ) -> AsyncIterator[Output]:
        """统一处理子工作流用户交互中断：更新状态、yield 摘要并触发父级 interact。"""
        self.node_state.status = ExecutionStatus.USER_INTERACT
        workflow_logger.info(
            "SubWorkflow detected child user interact",
            event_type=LogEventType.WORKFLOW_COMPONENT_END,
            component_type_str="SubWorkflow",
            metadata={
                "node_id": self._node_id,
                "child_node_id": self._interrupt_child_node_id,
                "reason": log_reason,
            },
        )
        self._stream_state = {
            "responseContent": final_res,
            USER_FIELDS: final_val,
        }
        if inner_session:
            inner_session.state().update_and_commit_workflow_state(
                {"__interrupted": True}
            )
        interact_prompt = self._resolve_interact_prompt(
            session, final_res, inner_session
        )
        yield {
            "responseContent": final_res,
            USER_FIELDS: final_val,
        }
        await session.interact(interact_prompt or final_res)

    def reset(self) -> bool:
        """重置组件状态

        Returns:
            bool: 重置成功返回 True
        """
        self.node_state.status = ExecutionStatus.START
        return True

    def get_state(self) -> SubWorkflowState:
        """获取当前状态

        Returns:
            SubWorkflowState: 当前状态
        """
        return self.node_state

    def load_state(self, state: SubWorkflowState):
        """从外部加载状态

        Args:
            state: 要加载的状态
        """
        self.node_state = deepcopy(state)

    def should_interrupt(self) -> bool:
        """检查是否需要中断

        Returns:
            bool: 需要中断返回 True
        """
        return self.node_state.status == ExecutionStatus.USER_INTERACT

    def error_to_output(self):
        """异常时设置状态为 END"""
        self.node_state.status = ExecutionStatus.END

    async def _get_workflow_instance(self, session: Session):
        """从全局状态获取子工作流实例

        Args:
            session: 工作流会话

        Returns:
            Workflow: 子工作流实例

        Raises:
            JiuWenBaseException: 未找到子工作流实例时抛出
        """
        if self._workflow_instance:
            return self._workflow_instance

        workflow_instance_dict = session.get_global_state(WORKFLOW_INSTANCE_DICT) or {}
        workflow_id = self._conf.get("reference", {}).get("id", "")
        workflow_instance = workflow_instance_dict.get(self._node_id)

        if not workflow_instance:
            workflow_logger.error(
                "Failed to get sub workflow instance",
                event_type=LogEventType.WORKFLOW_COMPONENT_ERROR,
                component_type_str="SubWorkflow",
                metadata={"workflow_id": workflow_id, "node_id": self._node_id},
            )
            raise build_sub_workflow_error(
                SubWorkflowStatusCode.WORKFLOW_INSTANCE_NOT_FOUND,
                workflow_id=workflow_id,
            )

        return workflow_instance

    async def _build_invoke_params(
        self, inputs: dict, session: Session, context: ModelContext
    ) -> dict:
        """构建子工作流调用参数，并将 query 作为用户消息写入对话历史。

        在调用子工作流前，将当前 query 以 UserMessage 形式追加到 context 中，
        使子工作流内各组件（如 LLM）通过 context.get_messages() 即可获取完整对话历史。
        同时将对话历史序列化后放入返回的 params，便于子工作流通过 inputs 显式获取。

        Args:
            inputs: 输入数据
            session: 工作流会话
            context: 模型上下文

        Returns:
            dict: 调用参数，包含 query、global_variables、conversation_history
        """
        system_fields = inputs.get(SYSTEM_FIELDS, {})
        user_fields = inputs.get(USER_FIELDS, {})
        memory_fields = inputs.get("memory", {})
        if not isinstance(memory_fields, dict):
            memory_fields = {}

        query = system_fields.get("query", "")
        if self._interrupt_child_node_id:
            resume_query = self._extract_parent_resume_query(session)
            if resume_query is not None:
                query = resume_query

        global_variables = dict(get_workflow_param(session, GLOBAL_VARIABLES) or {})
        user_id = global_variables.get("userId", "")

        global_variables.update(memory_fields)
        global_variables.update(user_fields)
        global_variables["userId"] = user_id

        if context and query:
            user_msg = UserMessage(content=query)
            await context.add_messages(user_msg)

            all_messages = context.get_messages()
            conversation_history = [msg.model_dump() for msg in all_messages]
        else:
            conversation_history = []

        self._current_query = query

        return {
            "query": query,
            "global_variables": global_variables,
            "conversation_history": conversation_history,
        }

    def _build_child_interactive_input(self, user_response: str) -> InteractiveInput:
        """根据恢复状态构建子工作流的 InteractiveInput

        当 SubWorkflow 因子工作流中断而恢复执行时，需要将用户的响应
        包装为 InteractiveInput 传给子工作流，使其 checkpointer 能正确恢复。

        始终使用 raw_inputs 路由，原因如下：

        user_inputs 路由在 SubWorkflow 场景下不可用：
        _process_interactive_inputs 通过 NodeSession(session, node_id) 将
        user_inputs 写入 comp_state，而 NodeSession 构造时
        create_parent_id(session) 在 session 为 SubWorkflowSession 时
        返回 session.executable_id()，导致 state key 被加上 SubWorkflow
        前缀。但子工作流内部节点（如循环中的 QA）的 executable_id 不含
        该前缀，因此 comp_state 的 key 永远无法匹配，user_inputs 路由
        在 SubWorkflow 场景下本质上是不可用的。

        raw_inputs 路由的安全性：
        raw_inputs 写入 workflow_state（全局共享），QA 节点通过
        WorkflowInteraction.__init__ → get_workflow_state(INTERACTIVE_INPUT)
        读取，不依赖 executable_id 匹配。子工作流一次只有一个节点
        处于 USER_INTERACT（pregel 引擎保证），因此 raw_inputs 广播
        不会导致误投递。

        Args:
            user_response: 用户响应内容

        Returns:
            InteractiveInput: 子工作流恢复所需的交互输入
        """
        return InteractiveInput(raw_inputs=user_response)

    async def invoke(
        self, inputs: Input, session: Session, context: ModelContext
    ) -> Output:
        """非流式执行子工作流

        Args:
            inputs: 输入数据
            session: 工作流会话
            context: 模型上下文

        Returns:
            Output: 输出数据
        """
        workflow_logger.info(
            "SubWorkflow invoke started",
            event_type=LogEventType.WORKFLOW_COMPONENT_START,
            component_type_str="SubWorkflow",
            metadata={"node_id": self._node_id},
        )

        self._workflow_instance = await self._get_workflow_instance(session)

        child_inputs = await self._prepare_child_inputs(
            inputs, session, context, for_stream=False
        )
        # 记录传入的全局变量值（调试信息）
        global_vars = self._collect_global_vars(inputs, session)
        if global_vars:
            await session.trace(data={"memory": global_vars})
        # 进入子工作流前：父子 _REQUEST 隔离，避免父值覆盖子 Start 的输入
        parent_request_snapshot = self._enter_sub_request_scope(session, child_inputs)
        scope_active = True
        try:
            invoke_timeout = self._get_timeout(session)
            result = await asyncio.wait_for(
                self._workflow_instance.invoke(
                    inputs=child_inputs,
                    session=session,
                    context=context,
                    is_sub=True,
                    reset_sub_outputs=self._last_child_completed,
                ),
                timeout=invoke_timeout,
            )

            # 子工作流正常返回：还原父 _REQUEST 并选择性同步子的修改
            self._exit_sub_request_scope(session, parent_request_snapshot)
            scope_active = False
            # 获取更新后的全局变量值
            updated_memory = self._collect_updated_memory(session)

            if isinstance(result, dict):
                if "error_code" in result and "error_message" in result:
                    raise build_sub_workflow_error(
                        SubWorkflowStatusCode.EXECUTION_ERROR,
                        error_msg=result.get("error_message", "Unknown error"),
                    )
                interaction_chunk = self._find_interaction_chunk_in_child_result(result)
                if interaction_chunk is not None:
                    await self._raise_user_interact_from_chunk(
                        session, interaction_chunk
                    )
                response_content, user_fields = self._parse_normal_child_invoke_result(
                    result
                )
            else:
                response_content = str(result)
                user_fields = {}

            self.node_state.status = ExecutionStatus.END
            self._last_child_completed = True

            workflow_logger.info(
                "SubWorkflow invoke completed",
                event_type=LogEventType.WORKFLOW_COMPONENT_END,
                component_type_str="SubWorkflow",
                metadata={"node_id": self._node_id},
            )
            self._stream_state = {
                "responseContent": response_content,
                USER_FIELDS: user_fields,
            }
            return {
                "responseContent": response_content,
                USER_FIELDS: user_fields,
                "memory": updated_memory,
            }

        except asyncio.TimeoutError:
            self.node_state.status = ExecutionStatus.USER_INTERACT
            self._last_child_completed = False
            workflow_logger.info(
                "SubWorkflow stream timed out, likely interactive sub-workflow",
                event_type=LogEventType.WORKFLOW_COMPONENT_END,
                component_type_str="SubWorkflow",
                metadata={"node_id": self._node_id, "timeout": invoke_timeout},
            )
            sub_session_state = session.get_state() or {}
            for key, value in sub_session_state.items():
                for k, v in value.items():
                    status = v.get("status")
                    if status.value == ExecutionStatus.USER_INTERACT.value:
                        self._interrupt_child_node_id = key
                        break
                if self._interrupt_child_node_id:
                    break
            await session.interact(child_inputs.get("query", ""))
        except JiuWenBaseException:
            self._last_child_completed = False
            raise
        except GraphInterrupt:
            self._last_child_completed = False
            partial_state = getattr(self, '_stream_state', {}) or {}
            await self._trace_interrupt_marker(
                session,
                partial_state.get("responseContent", ""),
                partial_state.get(USER_FIELDS, {}),
            )
            raise
        except Exception as e:
            self._last_child_completed = False
            workflow_logger.error(
                "SubWorkflow invoke error",
                event_type=LogEventType.WORKFLOW_COMPONENT_ERROR,
                component_type_str="SubWorkflow",
                metadata={"node_id": self._node_id, "error": str(e)},
            )
            raise build_sub_workflow_error(
                SubWorkflowStatusCode.EXECUTION_ERROR,
                error_msg=str(e) if LOG_VERBOSE_MODE else str(type(e).__name__),
                cause=e,
            ) from e
        finally:
            # 子工作流异常 / 中断退出时也要还原父 _REQUEST，否则后续父节点读到的
            # 是子工作流的 _request，会导致变量解析错误
            if scope_active:
                self._exit_sub_request_scope(session, parent_request_snapshot)
                scope_active = False

    async def stream(
        self, inputs: Input, session: Session, context: ModelContext
    ) -> AsyncIterator[Output]:
        """流式执行子工作流

        Args:
            inputs: 输入数据
            session: 工作流会话
            context: 模型上下文

        Yields:
            Output: 流式输出数据
        """
        workflow_logger.info(
            "SubWorkflow stream started",
            event_type=LogEventType.WORKFLOW_COMPONENT_START,
            component_type_str="SubWorkflow",
            metadata={"node_id": self._node_id},
        )

        self._pending_interact_prompt = ""

        inner_session = getattr(session, "_inner", None)
        is_child_resume = self._should_resume_child_workflow(session)
        # 仅全新执行时清除中断标记；恢复场景需保留 checkpoint 关联状态
        if not is_child_resume and inner_session:
            inner_session.state().update_and_commit_workflow_state(
                {"__interrupted": False}
            )

        self._workflow_instance = await self._get_workflow_instance(session)

        child_inputs = await self._prepare_child_inputs(
            inputs, session, context, for_stream=True
        )
        # 记录传入的全局变量值（调试信息）
        global_vars = self._collect_global_vars(inputs, session)
        if global_vars:
            await session.trace(data={"memory": global_vars})
        final_res = ""
        final_val = {}
        messages = []
        first_frame_timeout = self._get_first_frame_timeout(session)
        frame_timeout = self._get_frame_timeout(session)
        current = session.get_env(WORKFLOW_STREAM_FRAME_TIMEOUT)
        if current is None or (isinstance(current, (int, float)) and current <= 0):
            if inner_session:
                inner_session.config().set_envs(
                    {WORKFLOW_STREAM_FRAME_TIMEOUT: frame_timeout}
                )

        # 进入子工作流前：父子 _REQUEST 隔离，避免父值覆盖子 Start 的输入
        parent_request_snapshot = self._enter_sub_request_scope(session, child_inputs)
        scope_active = True
        try:
            stream_iter = self._workflow_instance.stream(
                inputs=child_inputs,
                session=session,
                context=context,
                is_sub=True,
                reset_sub_outputs=self._last_child_completed,
            ).__aiter__()

            first_chunk = True
            last_processed: Optional[dict] = None
            while True:
                current_timeout = first_frame_timeout if first_chunk else frame_timeout
                try:
                    chunk = await asyncio.wait_for(
                        stream_iter.__anext__(), timeout=current_timeout
                    )
                except StopAsyncIteration:
                    break
                first_chunk = False

                processed = await self._process_stream_chunk(
                    chunk, session, context, inputs
                )

                if processed is None:
                    continue

                last_processed = processed

                if processed.get("is_final"):
                    final_val = processed.get("user_fields", {})
                    continue

                if processed.get("is_message_end"):
                    messages.append(final_res)
                    final_res = ""
                    continue

                if processed.get("is_interaction"):
                    self.node_state.status = ExecutionStatus.USER_INTERACT
                    self._last_child_completed = False
                    payload = processed.get("payload", {})
                    child_node_id = None
                    if hasattr(payload, "id"):
                        child_node_id = payload.id
                    elif isinstance(payload, dict):
                        child_node_id = payload.get("id")
                    if child_node_id:
                        self._interrupt_child_node_id = child_node_id
                    if inner_session:
                        inner_session.state().update_and_commit_workflow_state(
                            {"__interrupted": True}
                        )
                    # 中断时也写入 sub_workflow_query，避免恢复时丢失
                    interact_value = self._resolve_interact_value(payload)
                    current_query = getattr(self, '_current_query', '')
                    if current_query:
                        interact_payload = {
                            "sub_workflow_query": current_query,
                            "parentNodeId": session.get_component_id(),
                        }
                        if isinstance(interact_value, dict):
                            interact_payload.update(interact_value)
                        else:
                            interact_payload["value"] = interact_value
                        await session.write_custom_stream(
                            CustomSchema(type=MESSAGE_NODE_END, index=1, data=interact_payload)
                        )
                    await session.interact(interact_value)
                    return

                if "answer" in processed:
                    final_res = processed["answer"]

                yield processed

            # 子 stream 迭代结束：Questioner 中断时往往无 INTERACTION chunk，需读 session 兜底
            if self._detect_child_interrupt(
                session
            ) or self._is_parent_workflow_interrupted(inner_session):
                self._last_child_completed = False
                async for item in self._emit_sub_workflow_user_interact(
                    session,
                    inner_session,
                    final_res,
                    final_val,
                    log_reason="child_stream_end_with_interrupt_state",
                ):
                    yield item
                return

            # 子工作流流式正常结束：还原父 _REQUEST 并选择性同步子的修改
            self._exit_sub_request_scope(session, parent_request_snapshot)
            scope_active = False

            final_res = messages[-1] if messages else final_res
            # 获取更新后的全局变量值
            updated_memory = self._collect_updated_memory(session)
            self.node_state.status = ExecutionStatus.END
            self._last_child_completed = True

            workflow_logger.info(
                "SubWorkflow stream completed",
                event_type=LogEventType.WORKFLOW_COMPONENT_END,
                component_type_str="SubWorkflow",
                metadata={"node_id": self._node_id},
            )
            self._stream_state = {
                "responseContent": final_res,
                USER_FIELDS: final_val,
            }
            end_payload = dict(last_processed or {})
            end_payload["is_sub"] = True
            end_payload["parentNodeId"] = session.get_component_id()
            end_payload["sub_workflow_query"] = getattr(self, '_current_query', '')
            await session.write_custom_stream(
                CustomSchema(type=MESSAGE_NODE_END, index=1, data=end_payload)
            )
            result = {
                "responseContent": final_res,
                USER_FIELDS: final_val,
            }
            if updated_memory:
                result["memory"] = updated_memory
            yield result

        except asyncio.TimeoutError:
            self._last_child_completed = False
            # 首帧/帧超时：子 _sub_stream 可能阻塞在 sub_workflow_stream.receive，用 session 识别中断
            self._detect_child_interrupt(session)
            timed_out = first_frame_timeout if first_chunk else frame_timeout
            workflow_logger.info(
                "SubWorkflow stream timed out, likely interactive sub-workflow",
                event_type=LogEventType.WORKFLOW_COMPONENT_END,
                component_type_str="SubWorkflow",
                metadata={"node_id": self._node_id, "timeout": timed_out},
            )
            async for item in self._emit_sub_workflow_user_interact(
                session,
                inner_session,
                final_res,
                final_val,
                log_reason="stream_frame_timeout",
            ):
                yield item
            return
        except JiuWenBaseException:
            self._last_child_completed = False
            raise
        except GraphInterrupt:
            self._last_child_completed = False
            await self._trace_interrupt_marker(
                session, final_res, final_val
            )
            raise
        except Exception as e:
            self._last_child_completed = False
            workflow_logger.error(
                "SubWorkflow stream error",
                event_type=LogEventType.WORKFLOW_COMPONENT_ERROR,
                component_type_str="SubWorkflow",
                metadata={"node_id": self._node_id, "error": str(e)},
            )
            raise build_sub_workflow_error(
                SubWorkflowStatusCode.STREAM_ERROR,
                error_msg=str(e) if LOG_VERBOSE_MODE else str(type(e).__name__),
                cause=e,
            ) from e
        finally:
            # 流式异常 / 中断 / generator 提前 close 时也要还原父 _REQUEST，
            # 否则父工作流后续节点读到的是子工作流残留的 _request
            if scope_active:
                self._exit_sub_request_scope(session, parent_request_snapshot)
                scope_active = False

    async def _process_stream_chunk(
        self,
        chunk: Any,
        session: Session,
        context: ModelContext,
        inputs: dict,
    ) -> Optional[dict]:
        """处理流式数据块

        Args:
            chunk: 流式数据块
            session: 工作流会话
            context: 模型上下文
            inputs: 输入数据

        Returns:
            Optional[dict]: 处理后的数据，None 表示需要跳过
        """
        if isinstance(chunk, OutputSchema):
            chunk_type = chunk.type
            payload = chunk.payload if isinstance(chunk.payload, dict) else {}

            if chunk_type in ["start", "workflow_start", "workflow_end"]:
                return None

            if chunk_type == INTERACTION:
                self.node_state.status = ExecutionStatus.USER_INTERACT
                child_node_id = (
                    getattr(chunk.payload, "id", None) if chunk.payload else None
                )
                if child_node_id is None and isinstance(chunk.payload, dict):
                    child_node_id = chunk.payload.get("id")
                if child_node_id:
                    self._interrupt_child_node_id = child_node_id
                interact_value = getattr(chunk.payload, "value", None)
                if interact_value:
                    self._pending_interact_prompt = str(interact_value)
                return {"is_interaction": True, "payload": chunk.payload}

            if chunk_type == "error":
                raw_msg = payload.get("error_message") or payload.get("message", "")
                safe_msg = sanitize_message(raw_msg)
                raise build_sub_workflow_error(
                    SubWorkflowStatusCode.STREAM_ERROR,
                    error_msg=raw_msg if LOG_VERBOSE_MODE else safe_msg,
                )

            if chunk_type == "workflow_exception":
                raise WorkflowAbortException(data=payload)

            if chunk_type == "workflow_final":
                return {"is_final": True, "user_fields": payload.get("user_fields", {})}

            if chunk_type == "message_end":
                if payload.get("should_interrupt"):
                    self._pending_interact_prompt = (
                        payload.get("answer") or payload.get("result") or ""
                    )
                    # 仅在 INTERACTION chunk 未设置时更新 _interrupt_child_node_id，
                    # 避免不含 loop 前缀的 componentId 覆盖 INTERACTION 设置的
                    # 含 loop 前缀的 executableId
                    if not self._interrupt_child_node_id:
                        node_id = payload.get("node_id")
                        if node_id:
                            self._interrupt_child_node_id = node_id
                return {"is_message_end": True}

            if chunk_type in ["end node stream", "partial_content"]:
                content = payload.get("answer", "")
                if payload.get("should_interrupt"):
                    self._pending_interact_prompt = (
                        payload.get("answer") or payload.get("result") or ""
                    )
                    if not self._interrupt_child_node_id:
                        node_id = payload.get("node_id")
                        if node_id:
                            self._interrupt_child_node_id = node_id
                await session.write_stream(chunk)
                return {"content": content}

            return {"type": chunk_type, "payload": payload}

        if isinstance(chunk, dict):
            return chunk

        return None

    def _enter_sub_request_scope(
        self, session: Session, child_inputs: dict
    ) -> dict:
        """进入子工作流前隔离父子 _REQUEST 作用域。

        新框架中父子工作流共享同一份 ``global_state``，导致子工作流的 Start 节点
        ``_assemble_output`` 通过 ``get_workflow_param(session, REQUEST_VARIABLES)``
        读到的是父工作流的 ``_request``，会把 ``inputs_copy`` 中本应保留的子工作流
        输入字段错误覆盖。

        旧框架（``orchestration/flow/workflow.py``）通过每个工作流实例持有独立
        ``runtime_context`` 实现父子隔离，并在子 ``_arun`` 入口将 ``_request`` 重置
        为传入的 ``global_variables``：

            recovered = self.runtime_context.get(REQUEST_VARIABLES, {})
            request_variables = {...过滤后的 global_variables...}
            self.runtime_context.set(REQUEST_VARIABLES, {**recovered, **request_variables})

        本方法在新框架下模拟相同语义：将父 ``_request`` 快照保存并返回，再把
        ``global_state[_request]`` 替换为 ``parent_snapshot ∪ child_request``，
        让子工作流既能继承父声明的 envs，又能用自身的 globals 覆盖同名 key。

        Args:
            session: 工作流会话
            child_inputs: 即将传给子工作流的 inputs；其中 ``_REQUEST`` 键由
                ``_prepare_child_inputs`` 写入，是子工作流的 globals 视图

        Returns:
            dict: 父工作流 ``_request`` 的深拷贝快照，供 ``_exit_sub_request_scope``
                还原使用
        """
        parent_snapshot = deepcopy(
            get_workflow_param(session, REQUEST_VARIABLES) or {}
        )
        # resume 场景下 child_inputs 是 InteractiveInput 而非 dict，没有 _REQUEST
        if isinstance(child_inputs, dict):
            child_request = child_inputs.get("_REQUEST") or {}
        else:
            child_request = {}
        if not isinstance(child_request, dict):
            child_request = {}
        merged = {**parent_snapshot, **child_request}
        session.update_global_state({REQUEST_VARIABLES: merged})
        return parent_snapshot

    def _exit_sub_request_scope(
        self, session: Session, parent_snapshot: dict
    ) -> None:
        """退出子工作流时还原父 _REQUEST 并选择性同步子的修改。

        子工作流执行期间可能通过 SetVariable 等组件修改 ``global_state[_request]``，
        这些修改语义上属于子工作流的局部副本。退出时仅把 **父工作流已声明的 key**
        从子修改后的副本同步回父快照——既不会丢失子对父变量的合法更新，又能避免
        子工作流内部的临时变量污染父的 ``_request``。

        与旧框架 ``components/sub_workflow.py::_sync_sub_request_to_parent`` 的策略
        一致（``orchestration/flow/components/sub_workflow.py:357``）。

        Args:
            session: 工作流会话
            parent_snapshot: ``_enter_sub_request_scope`` 返回的父 ``_request`` 快照
        """
        try:
            sub_request_vars = get_workflow_param(session, REQUEST_VARIABLES) or {}
            updated = {
                k: sub_request_vars[k]
                for k in parent_snapshot
                if k in sub_request_vars
            }
            restored = {**parent_snapshot, **updated}
            session.update_global_state({REQUEST_VARIABLES: restored})
            if updated:
                workflow_logger.info(
                    "Sub-workflow request variables synced to parent",
                    event_type=LogEventType.WORKFLOW_COMPONENT_END,
                    component_type_str="SubWorkflow",
                    metadata={"updated_keys": list(updated.keys())},
                )
        except Exception as e:
            workflow_logger.warning(
                f"Failed to restore parent request scope after sub-workflow: {e}",
                event_type=LogEventType.WORKFLOW_COMPONENT_ERROR,
                component_type_str="SubWorkflow",
            )
            # 兜底：尽量恢复父快照，避免父 state 被子的临时变量污染
            try:
                session.update_global_state({REQUEST_VARIABLES: parent_snapshot})
            except Exception:
                workflow_logger.warning(
                    "Failed to restore parent request scope snapshot as fallback",
                    event_type=LogEventType.WORKFLOW_COMPONENT_ERROR,
                    component_type_str="SubWorkflow",
                    exc_info=True,
                )

    def _sync_sub_request_to_parent(self, session: Session):
        """将子工作流的 REQUEST 变量同步回父工作流

        只更新父已声明的 key，防止子工作流内部临时变量污染父的 _REQUEST。

        Args:
            session: 工作流会话
        """
        if not self._workflow_instance:
            return

        try:
            sub_session_state = session.get_global_state("_sub_session_state")
            if not sub_session_state:
                return

            sub_request_vars = sub_session_state.get(REQUEST_VARIABLES) or {}
            if not sub_request_vars:
                return

            parent_request_vars = get_workflow_param(session, REQUEST_VARIABLES) or {}

            updated = {
                k: sub_request_vars[k]
                for k in parent_request_vars
                if k in sub_request_vars
            }

            if updated:
                parent_request_vars.update(updated)
                session.update_global_state({REQUEST_VARIABLES: parent_request_vars})
                workflow_logger.info(
                    "Sub-workflow request variables synced to parent",
                    event_type=LogEventType.WORKFLOW_COMPONENT_END,
                    component_type_str="SubWorkflow",
                    metadata={"updated_keys": list(updated.keys())},
                )

        except Exception as e:
            workflow_logger.warning(
                f"Failed to sync sub-workflow request variables: {e}",
                event_type=LogEventType.WORKFLOW_COMPONENT_ERROR,
                component_type_str="SubWorkflow",
            )

    async def _trace_interrupt_marker(
        self,
        session: Session,
        response_content: str,
        user_fields: dict,
    ) -> None:
        """向 trace span 写入中断标记和部分输出。

        session.trace() 将数据写入 on_invoke_data，生成一条 status="running"
        的 TraceSchema。wrapper 层检测到 on_invoke_data 中的 _sub_interrupt_marker
        后会缓存此帧，等 status="interrupted" 的 TraceSchema 到达后，
        以 status="finish" 合并发送。
        """
        try:
            await session.trace(data={
                "_sub_interrupt_marker": True,
                "interrupt_outputs": {
                    "responseContent": response_content,
                    USER_FIELDS: user_fields,
                },
            })
        except Exception as e:
            workflow_logger.warning(f"_trace_interrupt_marker error: {e}")

    def get_stream_output(self) -> Output:
        """Get the cached stream output for batch retrieval."""
        if self._stream_state:
            return self._stream_state
        return None

    def component_type(self) -> str:
        return "sub_workflow"


from jiuwen.extension.patches.loop_body_session_cleanup_patch import (
    apply_loop_body_session_cleanup_patch,
    apply_loop_state_cleanup_patch,
)
from jiuwen.extension.patches.workflow_sub_stream_patch import (
    apply_workflow_sub_stream_patch,
)

apply_workflow_sub_stream_patch()
apply_loop_body_session_cleanup_patch()
apply_loop_state_cleanup_patch()