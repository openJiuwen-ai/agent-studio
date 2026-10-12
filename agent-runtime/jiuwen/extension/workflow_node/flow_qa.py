# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2026. All rights reserved.

"""
FlowQA - 问答节点组件
"""

from __future__ import annotations

import random
import re
from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from openjiuwen.core.common.constants.constant import USER_FIELDS, INTERACTIVE_INPUT
from openjiuwen.core.common.exception.codes import StatusCode
from openjiuwen.core.common.exception.errors import build_error
from openjiuwen.core.common.logging import LogEventType, workflow_logger
from openjiuwen.core.context_engine import ModelContext
from openjiuwen.core.graph.executable import Input, Output
from openjiuwen.core.graph.pregel import GraphInterrupt
from openjiuwen.core.session.node import Session
from openjiuwen.core.session.stream import CustomSchema
from openjiuwen.core.workflow.components.component import WorkflowComponent
from openjiuwen.core.workflow.components.flow.end_comp import TemplateUtils
from pydantic import BaseModel, ConfigDict, Field

from jiuwen.extension.workflow.execution_session_ctx import get_stream_final_output

PARTIAL_CONTENT = "partial_content"
MESSAGE_NODE_END = "message_end"
WORKFLOW_CHAT_HISTORY = "workflow_chat_history"
JIUWEN_QA_TYPE = "EI.qa"


class QAStrategy(Enum):
    random = "random"
    index = "index"


class ExecutionStatus(Enum):
    START = "start"
    USER_INTERACT = "user_interact"
    END = "end"


@dataclass
class QAState:
    status: ExecutionStatus = ExecutionStatus.START
    inputs: dict = field(default_factory=dict)
    question: str = ""


class QAConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    name: Optional[str] = Field(default=None, description="Node name.")
    needReply: bool = Field(default=False, description="Whether need user reply.")
    qaStrategy: str = Field(
        default="random", description="QA strategy: random or index."
    )
    options: List[str] = Field(default_factory=list, description="QA options.")
    struct_output_template: str = Field(
        default="", description="Structured output template."
    )
    isStructMessage: bool = Field(
        default=False, description="Enable structured message."
    )
    enable_history: bool = Field(default=True, description="Enable history write.")
    index_key: str = Field(default="index", description="Key for index strategy.")
    struct_input_schemas: Dict[str, dict] = Field(
        default_factory=dict,
        description=(
            "结构化输出模板中 dict/list 型变量的归一化 schema。"
            "渲染前按 schema 补齐缺失字段（默认 \"\"）、按 schema 顺序输出，"
            "用于和历史系统（如 Versatile Lite）的输出对齐。"
            "形如 {\"confirmData\": {\"type\": \"object\", \"properties\": {\"amount\": {\"default\": \"\"}, ...}}}"
        ),
    )


@dataclass
class FlowQAConfig:
    name: Optional[str] = None
    need_reply: bool = False
    qa_strategy: str = "random"
    options: List[str] = field(default_factory=list)
    struct_output_template: str = ""
    enable_struct_message: bool = False
    enable_history: bool = True
    index_key: str = "index"
    # 结构化输出时，对 dict/list 型输入按 schema 归一化：
    # 补齐缺失字段（默认 ""）、按 schema 顺序输出，并保留 schema 之外的字段。
    struct_input_schemas: Dict[str, dict] = field(default_factory=dict)


def _schema_field_name(schema: dict) -> Optional[str]:
    return schema.get("name") or schema.get("id") or schema.get("fieldName")


def _schema_type(schema: dict) -> str:
    return str(schema.get("type") or "").lower()


def _object_schema_fields(schema: dict) -> List[tuple[str, dict]]:
    props = schema.get("properties")
    if isinstance(props, dict):
        return [
            (str(name), prop_schema if isinstance(prop_schema, dict) else {})
            for name, prop_schema in props.items()
        ]

    children = schema.get("schema")
    if not isinstance(children, list):
        return []

    fields: List[tuple[str, dict]] = []
    for child in children:
        if not isinstance(child, dict):
            continue
        name = _schema_field_name(child)
        if name:
            fields.append((str(name), child))
    return fields


def _is_object_schema(schema: dict) -> bool:
    return (
        _schema_type(schema) == "object"
        or isinstance(schema.get("properties"), dict)
        or isinstance(schema.get("schema"), list)
    )


def _array_item_schema(schema: dict) -> Optional[dict]:
    items = schema.get("items")
    if isinstance(items, dict):
        return items

    dsl_schema = schema.get("schema")
    if isinstance(dsl_schema, dict):
        return dsl_schema
    if isinstance(dsl_schema, list):
        return {"type": "object", "schema": dsl_schema}
    return None


def _is_array_schema(schema: dict) -> bool:
    return _schema_type(schema) == "array"


def _schema_default(schema: dict) -> Any:
    value = schema.get("value")
    if isinstance(value, dict) and "default" in value:
        return value["default"]
    if "default" in schema:
        return schema["default"]
    if _is_array_schema(schema):
        return []
    if _is_object_schema(schema):
        return {}
    return ""


def _has_struct_schema(schema: dict) -> bool:
    if not isinstance(schema, dict):
        return False
    if _is_object_schema(schema):
        return bool(_object_schema_fields(schema))
    if _is_array_schema(schema):
        return _array_item_schema(schema) is not None
    return False


def _iter_input_field_defs(fields: Any):
    if isinstance(fields, list):
        for field in fields:
            if isinstance(field, dict):
                yield field
        return
    if isinstance(fields, dict) and _schema_field_name(fields):
        yield fields


def build_struct_input_schemas(
    node_inputs: Any = None,
    config_inputs: Any = None,
    explicit_schemas: Optional[Dict[str, dict]] = None,
) -> Dict[str, dict]:
    """Collect dict/list input schemas used to render QA templates.

    QA configs do not always repeat all node inputs in ``userFields.inputs``.
    For example, ``{{confirmData}}`` can appear only in the node-level inputs,
    so the converter injects those schemas into FlowQA before runtime.
    """
    schemas: Dict[str, dict] = {}
    for source in (config_inputs, node_inputs):
        for field in _iter_input_field_defs(source):
            name = _schema_field_name(field)
            if name and _has_struct_schema(field):
                schemas[str(name)] = field

    if isinstance(explicit_schemas, dict):
        schemas.update(explicit_schemas)
    return schemas


class FlowQA(WorkflowComponent):
    """工作流问答节点

    功能:
    1. 根据配置的话术选项向用户展示问题
    2. 支持随机或索引两种问答策略
    3. 支持中断等待用户回复
    4. 支持会话历史管理
    5. 支持结构化信息输出
    """

    def __init__(self, conf: Union[FlowQAConfig, dict, None] = None):
        super().__init__()
        if not conf:
            raise build_error(
                StatusCode.WORKFLOW_COMPONENT_SCHEMA_INVALID,
                comp_id="flow_qa",
                reason="conf is required",
                workflow="n/a",
            )
        try:
            if isinstance(conf, dict):
                self._conf = FlowQAConfig(
                    name=conf.get("name"),
                    need_reply=conf.get("needReply", False),
                    qa_strategy=conf.get("qaStrategy", "random"),
                    options=conf.get("options", []),
                    struct_output_template=conf.get("struct_output_template", ""),
                    enable_struct_message=conf.get("isStructMessage", False),
                    enable_history=conf.get("enable_history", True),
                    index_key=conf.get("index_key", "index"),
                    struct_input_schemas=conf.get("struct_input_schemas", {}),
                )
            else:
                self._conf = conf
        except Exception as e:
            raise build_error(
                StatusCode.WORKFLOW_COMPONENT_SCHEMA_INVALID,
                comp_id="flow_qa",
                reason=str(e),
                workflow="n/a",
                cause=e,
            )

        self._node_state = QAState()
        self._node_name: Optional[str] = self._conf.name

        self._qa_state_key = "flow_qa_state"

    def component_type(self) -> str:
        return JIUWEN_QA_TYPE

    @staticmethod
    def get_latest_k_rounds_chat(chat_history: list, k: int) -> list:
        if k is None:
            return chat_history
        return chat_history[-k * 2 - 1 :]

    def get_latest_chat_history(self, session: Session, k: int = None) -> List[Dict]:
        chat_history = None
        if hasattr(session, "get_global_state"):
            chat_history = session.get_global_state(WORKFLOW_CHAT_HISTORY)

        # 先使用工作流历史
        # if chat_history:
        #     if hasattr(chat_history, "get_conversation_history"):
        #         chat_history = chat_history.get_conversation_history()
        #     else:
        #         chat_history = []
        # else:
        #     chat_history = []
        if not chat_history:
            chat_history = []

        chat_history = self.get_latest_k_rounds_chat(chat_history, k)
        for history in chat_history:
            history.update({"content": history.get("content")})
        return chat_history

    def get_state(self) -> QAState:
        return self._node_state

    def load_state(self, state: QAState) -> None:
        self._node_state = deepcopy(state)

    def get_node_status(self) -> ExecutionStatus:
        return self._node_state.status

    def get_stream_output(self):
        """末帧输出经 ContextVar 通道读取（实例跨执行复用，不落实例）。

        FlowQA 为 INVOKE-only 组件（无 stream/transform），引擎
        ``Vertex._post_stream`` 不触达本方法；通道读保证与其余流式组件
        同一契约，实例上不再保留引擎不可达的末帧死状态。
        """
        return get_stream_final_output()

    def error_to_output(self) -> None:
        self._node_state.status = ExecutionStatus.END

    @staticmethod
    def _load_state_from_session(session: Session) -> QAState:
        state_dict = None
        if hasattr(session, "get_state"):
            session_state = session.get_state()
            if isinstance(session_state, dict):
                state_dict = session_state.get("flow_qa_state")
        if state_dict:
            return QAState(
                status=ExecutionStatus(state_dict.get("status", "start")),
                inputs=state_dict.get("inputs", {}),
                question=state_dict.get("question", ""),
            )
        return QAState()

    @staticmethod
    def _store_state_to_session(state: QAState, session: Session):
        state_dict = {
            "status": state.status.value,
            "inputs": state.inputs,
            "question": state.question,
        }
        if hasattr(session, "update_state"):
            session.update_state({"flow_qa_state": state_dict})

    def should_interrupt(self) -> bool:
        return self._node_state.status == ExecutionStatus.USER_INTERACT

    def get_latest_user_query_intent(self, session: Session) -> Optional[str]:
        chat_history = None
        if hasattr(session, "get_global_state"):
            chat_history = session.get_global_state(WORKFLOW_CHAT_HISTORY)

        # 先使用工作流历史
        # if chat_history:
        #     if hasattr(chat_history, "get_conversation_history"):
        #         chat_history = chat_history.get_conversation_history()
        #     else:
        #         return None
        # else:
        #     return None

        for chat in reversed(chat_history):
            if chat.get("role") == "user":
                return chat.get("intent")

        return None

    def _process_values_of_dict(self, origin_template: str, inputs: dict) -> str:
        """
        处理占位符模板，进行参数替换。
        支持 {{param}} 格式的占位符。
        """
        pattern = re.compile(r"(\{\{.*?\}\})")
        response_list = pattern.split(origin_template)

        response = ""
        for res in response_list:
            if res.startswith("{{") and res.endswith("}}"):
                param_name = res[2:-2]
                if param_name not in inputs:
                    raise build_error(
                        StatusCode.WORKFLOW_COMPONENT_EXECUTION_ERROR,
                        comp="flow_qa",
                        reason=f"QA parameter key not found: {param_name}",
                        workflow="n/a",
                    )
                param_value = inputs.get(param_name)
                response += "" if param_value is None else str(param_value)
            else:
                response += res
        return response

    def _validate_options(self, options: List[str], inputs: dict) -> List[str]:
        """
        检查options中是否有占位符，同时进行替换。
        """
        return [self._process_values_of_dict(option, inputs) for option in options]

    def _get_qa_by_strategy(self, inputs: dict) -> str:
        strategy = self._conf.qa_strategy
        options = self._conf.options

        options = self._validate_options(options, inputs)

        if not options:
            raise build_error(
                StatusCode.WORKFLOW_COMPONENT_EXECUTION_ERROR,
                comp="flow_qa",
                reason="QA options is empty",
                workflow="n/a",
            )

        if strategy not in [QAStrategy.random.value, QAStrategy.index.value]:
            raise build_error(
                StatusCode.WORKFLOW_COMPONENT_EXECUTION_ERROR,
                comp="flow_qa",
                reason=f"Unsupported QA strategy: {strategy}",
                workflow="n/a",
            )

        if strategy == QAStrategy.random.value:
            return random.choice(options)
        else:
            index = int(inputs.get(self._conf.index_key, 0))
            if index >= len(options):
                raise build_error(
                    StatusCode.WORKFLOW_COMPONENT_EXECUTION_ERROR,
                    comp="flow_qa",
                    reason=f"QA index {index} out of range",
                    workflow="n/a",
                )
            return options[index]

    @staticmethod
    def _normalize_with_schema(value: Any, schema: Optional[dict]) -> Any:
        """按 schema 对结构化数据归一化：补齐缺失字段为默认值、按 schema 顺序输出。

        用于消除与历史系统（如 Versatile Lite）在「空字段是否输出」上的差异——
        历史系统会按完整字段模板补齐空串字段，而本系统此前直接透传生成端字典，
        导致 ``{{confirmData}}`` 这类占位符渲染出的字典缺少空值字段。

        支持 JSON Schema 风格 ``properties/items``，也支持当前 DSL 中的
        ``schema`` + ``name/id`` + ``value.default`` 风格。
        """
        if not isinstance(schema, dict):
            return value

        if value is None:
            if _is_object_schema(schema) or _is_array_schema(schema):
                return value
            return _schema_default(schema)

        if _is_object_schema(schema):
            if not isinstance(value, dict):
                return value
            src = value
            fields = _object_schema_fields(schema)
            if not fields:
                return value
            normalized: Dict[str, Any] = {}
            schema_field_names = set()
            for name, prop_schema in fields:
                schema_field_names.add(name)
                if name in src:
                    normalized[name] = FlowQA._normalize_with_schema(
                        src[name], prop_schema
                    )
                else:
                    normalized[name] = _schema_default(prop_schema)

            for name, item in value.items():
                if name not in schema_field_names:
                    normalized[name] = item
            return normalized

        if _is_array_schema(schema) and isinstance(value, list):
            item_schema = _array_item_schema(schema)
            if item_schema is None:
                return value
            return [
                FlowQA._normalize_with_schema(item, item_schema) for item in value
            ]

        return value

    def _normalize_struct_inputs(self, user_fields: dict) -> dict:
        if not isinstance(user_fields, dict):
            return user_fields
        schemas = self._conf.struct_input_schemas or {}
        if not schemas:
            return user_fields

        normalized = dict(user_fields)
        for key, schema in schemas.items():
            if key in normalized:
                normalized[key] = self._normalize_with_schema(
                    normalized[key], schema
                )
        return normalized

    async def _write_interaction_stream(
        self,
        session: Session,
        answer: str,
        node_id: str,
        need_reply: bool = True,
    ) -> None:
        stream_related_info = {
            "answer": answer,
            "result": answer,
            "node_id": node_id,
            "node_name": self._node_name or node_id,
            "node_type": JIUWEN_QA_TYPE,
            "should_interrupt": True,
            "enable_history": self._conf.enable_history,
            "need_reply": need_reply,
        }

        # message_end 事件的数据，默认与 message 事件相同
        end_stream_info = stream_related_info

        if self._conf.enable_struct_message and self._conf.struct_output_template:
            # 对声明了 schema 的 dict/list 型输入做归一化（补空值字段、规范顺序），
            # 再渲染，使结构化输出与历史系统字段集合一致。
            render_inputs: Dict[str, Any] = {
                "_NODE_OUTPUT": answer,
                **self._normalize_struct_inputs(self._node_state.inputs),
            }
            struct_answer = TemplateUtils.render_template(
                self._conf.struct_output_template,
                render_inputs,
            )
            # message 事件保持原始输出；message_end 事件用结构化输出作为 answer
            end_stream_info = dict(stream_related_info)
            end_stream_info["answer"] = struct_answer
            end_stream_info["origin_answer"] = answer
            end_stream_info["is_struct_message"] = True

        await session.write_custom_stream(
            CustomSchema(
                type=PARTIAL_CONTENT,
                index=0,
                data=stream_related_info,
            ).model_dump(by_alias=True, exclude_none=False, exclude_unset=False)
        )
        await session.write_custom_stream(
            CustomSchema(
                type=MESSAGE_NODE_END,
                index=1,
                data=end_stream_info,
            ).model_dump(by_alias=True, exclude_none=False, exclude_unset=False)
        )

    async def invoke(
        self, inputs: Input, session: Session, context: ModelContext
    ) -> Output:
        try:
            workflow_logger.debug(
                "FlowQA component invoke started",
                event_type=LogEventType.WORKFLOW_COMPONENT_START,
                component_id=session.get_component_id(),
                component_type_str=JIUWEN_QA_TYPE,
                session_id=session.get_session_id(),
            )

            state_from_session = self._load_state_from_session(session)
            has_saved_state = state_from_session.status != ExecutionStatus.START
            if has_saved_state:
                self._node_state = state_from_session
            else:
                self._node_state = QAState()

            node_id = session.get_component_id()
            user_fields = inputs.get(USER_FIELDS, inputs) if inputs else {}
            render_fields = self._normalize_struct_inputs(user_fields)

            if self._conf.need_reply:
                # 中断结束重新开始
                if self._node_state.status == ExecutionStatus.END:
                    self._node_state = QAState()

                if self._node_state.status == ExecutionStatus.START:
                    query = self._get_qa_by_strategy(render_fields)
                    # 先设置 inputs，再调用 _write_interaction_stream（因为模板渲染依赖 inputs）
                    self._node_state.inputs = render_fields
                    await self._write_interaction_stream(session, query, node_id, True)

                    self._node_state.question = query
                    self._node_state.status = ExecutionStatus.USER_INTERACT
                    self._store_state_to_session(self._node_state, session)

                    session._interaction = None
                    session.update_state({INTERACTIVE_INPUT: None})
                    # 清除 workflow_state 中残留的 INTERACTIVE_INPUT，防止父工作流的
                    # raw_inputs 泄漏导致 WorkflowInteraction 误读而跳过中断
                    session._inner.state().update_and_commit_workflow_state(
                        {INTERACTIVE_INPUT: None}
                    )
                    session._inner.state().commit()

                    await session.interact(query)

                elif self._node_state.status == ExecutionStatus.USER_INTERACT:
                    # 恢复执行：通过 interact() 获取用户输入
                    user_response = await session.interact(
                        self._node_state.question or ""
                    )

                    self._node_state.status = ExecutionStatus.END
                    self._store_state_to_session(self._node_state, session)

                    return {USER_FIELDS: {"response": user_response}}
            else:
                self._node_state.status = ExecutionStatus.END
                query = self._get_qa_by_strategy(render_fields)
                # 先设置 inputs，再调用 _write_interaction_stream（因为模板渲染依赖 inputs）
                self._node_state.inputs = render_fields
                await self._write_interaction_stream(session, query, node_id, False)

                self._store_state_to_session(self._node_state, session)

                return {USER_FIELDS: {"response": query}}

            workflow_logger.debug(
                "FlowQA component invoke succeeded",
                event_type=LogEventType.WORKFLOW_COMPONENT_END,
                component_id=session.get_component_id(),
                component_type_str=JIUWEN_QA_TYPE,
                session_id=session.get_session_id(),
            )

        except GraphInterrupt:
            raise
        except Exception as e:
            workflow_logger.error(
                "FlowQA invoke failed",
                event_type=LogEventType.WORKFLOW_COMPONENT_ERROR,
                component_id=session.get_component_id(),
                component_type_str=JIUWEN_QA_TYPE,
                session_id=session.get_session_id(),
                exception=e,
            )
            self.error_to_output()
            raise build_error(
                StatusCode.WORKFLOW_COMPONENT_EXECUTION_ERROR,
                comp=session.get_component_id(),
                ability="invoke",
                reason=str(e),
                workflow=session.get_workflow_id(),
                cause=e,
            )

    @property
    def node_type(self) -> str:
        return JIUWEN_QA_TYPE

    @property
    def config(self) -> FlowQAConfig:
        return self._conf


__all__ = [
    "FlowQA",
    "FlowQAConfig",
    "QAState",
    "ExecutionStatus",
    "QAStrategy",
    "build_struct_input_schemas",
]
