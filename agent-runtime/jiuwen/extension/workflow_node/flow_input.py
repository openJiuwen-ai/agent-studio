# Copyright (c) Huawei Technologies Co., Ltd. 2025-2026. All rights reserved.

"""
FlowInput - 输入节点组件

迁移自商用版本 FlowInput，适配开源版本 openjiuwen Studio 框架。

功能特性:
- 收集用户输入参数
- 支持工作流中断等待用户输入
- 管理节点执行状态（START、USER_INTERACT、END）
- 验证输入字段的完整性
- 支持流式/非流式输出
- 适配子工作流中的中断处理

设计说明:
- 直接继承 WorkflowComponent（单一继承）
- 通过 Session 管理状态
- 使用 CustomSchema 支持子工作流通信
- 状态使用 Pydantic BaseModel 序列化/反序列化
"""

from __future__ import annotations

import ast
import json
from copy import deepcopy
from enum import Enum
from typing import AsyncGenerator, Optional

from openjiuwen.core.common.exception.codes import StatusCode
from openjiuwen.core.common.exception.errors import build_error
from openjiuwen.core.common.logging import LogEventType, workflow_logger
from openjiuwen.core.context_engine import ModelContext
from openjiuwen.core.graph.executable import Input, Output
from openjiuwen.core.graph.pregel import GraphInterrupt
from openjiuwen.core.session.stream import OutputSchema
from openjiuwen.core.session.stream.base import CustomSchema
from openjiuwen.core.workflow import WorkflowComponent
from openjiuwen.core.workflow.components import Session
from pydantic import BaseModel, Field

# =============================================================================
# 常量定义
# =============================================================================

START_STR = "start"
END_STR = "end"
USER_INTERACT_STR = "user_interact"
PARTIAL_CONTENT = "partial_content"
MESSAGE_NODE_END = "message_end"
JIUWEN_FLOW_INPUT_TYPE = "jiuwen.input"
SUB_WORKFLOW_TYPE = "jiuwen.workflowComposite"
USER_FIELDS = "userFields"
FLOW_INPUT_STATE_KEY = "flow_input_state"

TYPE_DEFAULT_VALUE_DICT = {
    "string": "",
    "number": 0,
    "boolean": False,
    "array": [],
    "object": {},
}


# =============================================================================
# 枚举定义
# =============================================================================


class ExecutionStatus(Enum):
    START = START_STR
    USER_INTERACT = USER_INTERACT_STR
    END = END_STR


class FlowInputEvent(Enum):
    START_EVENT = START_STR
    USER_INTERACT_EVENT = USER_INTERACT_STR
    END_EVENT = END_STR


# =============================================================================
# 状态类定义
# =============================================================================


class FlowInputState(BaseModel):
    status: ExecutionStatus = Field(default=ExecutionStatus.START)
    question: str = Field(default="")

    @classmethod
    def deserialize(cls, raw_state: dict):
        state = cls.model_validate(raw_state)
        return state.handle_event(FlowInputEvent(state.status.value))

    def serialize(self) -> dict:
        return self.model_dump()

    def handle_event(self, event: FlowInputEvent):
        if event == FlowInputEvent.START_EVENT:
            return FlowInputStartState.from_state(self)
        if event == FlowInputEvent.USER_INTERACT_EVENT:
            return FlowInputInteractState.from_state(self)
        if event == FlowInputEvent.END_EVENT:
            return FlowInputEndState.from_state(self)
        return self

    def is_undergoing_interaction(self):
        return self.status == ExecutionStatus.USER_INTERACT

    def is_fresh_state(self):
        return self.status == ExecutionStatus.START and not self.question


class FlowInputStartState(FlowInputState):
    @classmethod
    def from_state(cls, flow_input_state: FlowInputState):
        return cls(
            status=ExecutionStatus.START,
            question=flow_input_state.question,
        )

    def handle_event(self, event: FlowInputEvent):
        if event == FlowInputEvent.USER_INTERACT_EVENT:
            return FlowInputInteractState.from_state(self)
        if event == FlowInputEvent.END_EVENT:
            return FlowInputEndState.from_state(self)
        return self


class FlowInputInteractState(FlowInputState):
    status: ExecutionStatus = Field(default=ExecutionStatus.USER_INTERACT)

    @classmethod
    def from_state(cls, flow_input_state: FlowInputState):
        return cls(
            status=ExecutionStatus.USER_INTERACT,
            question=flow_input_state.question,
        )

    def handle_event(self, event: FlowInputEvent):
        if event == FlowInputEvent.END_EVENT:
            return FlowInputEndState.from_state(self)
        return self


class FlowInputEndState(FlowInputState):
    status: ExecutionStatus = Field(default=ExecutionStatus.END)

    @classmethod
    def from_state(cls, flow_input_state: FlowInputState):
        return cls(
            status=ExecutionStatus.END,
            question=flow_input_state.question,
        )

    def handle_event(self, event: FlowInputEvent):
        if event == FlowInputEvent.START_EVENT:
            return FlowInputState().handle_event(event)
        return self


# =============================================================================
# 工具类
# =============================================================================


class FlowInputUtils:
    @staticmethod
    def parse_user_response(user_response) -> dict:
        """解析用户响应为字段值字典

        支持以下格式：
        - dict: 直接使用
        - JSON 字符串: 解析为 dict
        - field:value 格式: 逐行解析
        """
        values = {}
        if not user_response:
            return values
        if isinstance(user_response, dict):
            return user_response

        response_str = str(user_response).strip()
        if not response_str:
            return values

        try:
            parsed = json.loads(response_str)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        for line in response_str.split("\n"):
            if ":" in line:
                field, value = line.split(":", 1)
                values[field.strip()] = value.strip()

        return values

    @staticmethod
    def build_inputs_message(config: dict) -> str:
        """生成前端所需的输入配置信息"""
        inputs_need: list[dict] = config.get(USER_FIELDS, {}).get("inputs", [])

        def convert_format(arg_conf: dict) -> dict:
            keys_to_convert = {"id": "name"}
            converted = {keys_to_convert.get(k, k): v for k, v in arg_conf.items()}
            return converted

        inputs_info = {"inputs": [convert_format(item) for item in inputs_need]}
        return json.dumps(inputs_info, ensure_ascii=False)

    @staticmethod
    def validate_inputs(inputs: dict, config: dict) -> None:
        """验证输入参数的完整性和类型"""
        inputs_config = config.get(USER_FIELDS, {}).get("inputs", [])
        for input_config in inputs_config:
            input_field = input_config["id"]
            required = input_config["required"]
            flow_type = input_config["type"]

            if required and input_field not in inputs:
                raise build_error(
                    StatusCode.COMPONENT_QUESTIONER_INPUT_PARAM_ERROR,
                    error_msg=f"Required field '{input_field}' is missing",
                )

            if input_field not in inputs:
                continue

            value = inputs[input_field]

            if value is None or value == "":
                if required:
                    raise build_error(
                        StatusCode.COMPONENT_QUESTIONER_INPUT_PARAM_ERROR,
                        error_msg=f"Required field '{input_field}' cannot be empty",
                    )
                continue

            try:
                if flow_type == "string" and not isinstance(value, str):
                    inputs[input_field] = str(value)
                elif flow_type == "number":
                    if not isinstance(value, (int, float)):
                        inputs[input_field] = float(value)
                elif flow_type == "boolean":
                    if isinstance(value, str):
                        inputs[input_field] = value.lower() in ["true", "1", "yes"]
                    elif not isinstance(value, bool):
                        inputs[input_field] = bool(value)
                elif flow_type == "array":
                    if not isinstance(value, list):
                        if isinstance(value, str):
                            inputs[input_field] = json.loads(value)
                        else:
                            raise TypeError(
                                f"Expected list for field '{input_field}', "
                                f"got {type(value).__name__}"
                            )
                elif flow_type == "object":
                    if not isinstance(value, dict) and isinstance(value, str):
                        inputs[input_field] = json.loads(value)
                    elif not isinstance(value, dict):
                        raise TypeError(
                            f"Expected dict for field '{input_field}', "
                            f"got {type(value).__name__}"
                        )
            except (ValueError, TypeError) as e:
                raise build_error(
                    StatusCode.COMPONENT_QUESTIONER_INPUT_PARAM_ERROR,
                    error_msg=f"Field '{input_field}' has invalid type: {str(e)}",
                ) from e

    @staticmethod
    def fill_inputs(inputs: dict, values: dict, config: dict) -> dict:
        """根据用户响应填充输入值，对非必填空值使用类型默认值"""
        inputs_config = config.get(USER_FIELDS, {}).get("inputs", [])
        for input_config in inputs_config:
            input_field = input_config["id"]
            required = input_config["required"]
            flow_type = input_config["type"]

            input_value = values.get(input_field)
            if not required and not input_value:
                input_value = TYPE_DEFAULT_VALUE_DICT.get(flow_type, None)
            inputs[input_field] = input_value
        return inputs


# =============================================================================
# 主组件类
# =============================================================================


class FlowInput(WorkflowComponent):
    """输入节点组件

    迁移自商用版本 FlowInput，适配开源版本框架。

    职责:
    1. 收集用户输入参数
    2. 支持工作流中断等待用户输入
    3. 管理节点执行状态（START、USER_INTERACT、END）
    4. 验证输入字段的完整性
    5. 适配子工作流中的中断处理
    """

    def __init__(self, conf: dict = None):
        super().__init__()
        self._config = conf or {}
        self._node_state = FlowInputState()
        self._stream_output: Optional[dict] = None
        self._node_name: Optional[str] = self._config.get("name") or None

    # -------------------------------------------------------------------------
    # 状态管理
    # -------------------------------------------------------------------------

    @staticmethod
    def _load_state_from_session(session: Session) -> FlowInputState:
        state = session.get_state()
        state_dict = (
            state.get(FLOW_INPUT_STATE_KEY) if isinstance(state, dict) else None
        )
        if state_dict:
            return FlowInputState.deserialize(state_dict)
        return FlowInputState()

    @staticmethod
    def _store_state_to_session(state: FlowInputState, session: Session):
        state_dict = state.serialize()
        session.update_state({FLOW_INPUT_STATE_KEY: state_dict})

    def _build_custom_data(self, session: Session, message: str) -> dict:
        """构建子工作流通信所需的 CustomSchema 数据"""
        node_id = session.get_component_id()
        parent_id = None
        if getattr(getattr(session, "_inner", None), "_parent_id", None):
            parent_id = getattr(getattr(session, "_inner", None), "_parent_id")

        custom_data = {
            "answer": message,
            "result": message,
            "node_id": node_id,
            "node_name": self._node_name or node_id,
            "node_type": JIUWEN_FLOW_INPUT_TYPE,
            "should_interrupt": True,
        }
        if parent_id:
            custom_data["parentNodeId"] = parent_id
        return custom_data

    # -------------------------------------------------------------------------
    # 公共接口
    # -------------------------------------------------------------------------

    def should_interrupt(self) -> bool:
        return self._node_state.status == ExecutionStatus.USER_INTERACT

    def get_state(self) -> FlowInputState:
        return self._node_state

    def get_stream_output(self) -> Optional[dict]:
        return self._stream_output

    def load_state(self, state: FlowInputState) -> None:
        self._node_state = deepcopy(state)

    def get_node_status(self) -> ExecutionStatus:
        return self._node_state.status

    def error_to_output(self) -> None:
        self._node_state.status = ExecutionStatus.END

    # -------------------------------------------------------------------------
    # 执行入口
    # -------------------------------------------------------------------------

    async def invoke(
        self,
        inputs: Input,
        session: Session,
        context: ModelContext,
    ) -> Output:
        try:
            inputs = ast.literal_eval(inputs) if isinstance(inputs, str) else inputs
            state_from_session = self._load_state_from_session(session)
            has_saved_state = state_from_session.is_undergoing_interaction()
            if has_saved_state:
                current_state = state_from_session
            else:
                current_state = FlowInputState()

            self._node_state = current_state

            if current_state.status == ExecutionStatus.START:
                return await self._handle_start_state(
                    inputs, session, context, current_state
                )

            if current_state.status == ExecutionStatus.USER_INTERACT:
                return await self._handle_interact_state(
                    inputs, session, context, current_state
                )

            return {USER_FIELDS: deepcopy(inputs) if isinstance(inputs, dict) else {}}

        except GraphInterrupt:
            raise
        except Exception as e:
            workflow_logger.error(
                "FlowInput invoke failed",
                event_type=LogEventType.WORKFLOW_COMPONENT_ERROR,
                exception=e,
            )
            self.error_to_output()
            raise build_error(
                StatusCode.COMPONENT_QUESTIONER_INVOKE_CALL_FAILED,
                error_msg="flow_input invoke failed",
                cause=e,
            ) from e

    async def stream(
        self,
        inputs: Input,
        session: Session,
        context: ModelContext,
    ) -> AsyncGenerator[Output, None]:
        """流式执行入口

        适配子工作流中断处理模式，与 invoke 逻辑一致但使用 yield 输出。
        """
        try:
            inputs = ast.literal_eval(inputs) if isinstance(inputs, str) else inputs
            state_from_session = self._load_state_from_session(session)
            has_saved_state = state_from_session.is_undergoing_interaction()
            if has_saved_state:
                current_state = state_from_session
            else:
                current_state = FlowInputState()

            self._node_state = current_state

            if current_state.status == ExecutionStatus.START:
                query = FlowInputUtils.build_inputs_message(self._config)
                current_state.status = ExecutionStatus.USER_INTERACT
                current_state.question = query
                self._node_state = current_state

                self._store_state_to_session(current_state, session)

                custom_data = self._build_custom_data(session, query)
                await session.write_custom_stream(
                    CustomSchema(type=PARTIAL_CONTENT, index=0, data=custom_data)
                )
                await session.write_custom_stream(
                    CustomSchema(type=MESSAGE_NODE_END, index=1, data=custom_data)
                )
                self._stream_output = custom_data
                self._node_state.status = ExecutionStatus.END

                await session.interact(query)
                return

            if current_state.status == ExecutionStatus.USER_INTERACT:
                user_response = await session.interact(current_state.question)
                inputs_copy = deepcopy(inputs) if isinstance(inputs, dict) else {}
                values = FlowInputUtils.parse_user_response(user_response)
                FlowInputUtils.fill_inputs(inputs_copy, values, self._config)
                FlowInputUtils.validate_inputs(inputs_copy, self._config)

                new_state = FlowInputState()
                self._node_state = new_state
                self._store_state_to_session(new_state, session)

                yield OutputSchema(
                    type="complete",
                    index=0,
                    payload={USER_FIELDS: inputs_copy},
                )
                return

            yield OutputSchema(
                type="complete",
                index=0,
                payload={
                    USER_FIELDS: deepcopy(inputs) if isinstance(inputs, dict) else {}
                },
            )

        except GraphInterrupt:
            raise
        except Exception as e:
            workflow_logger.error(
                "FlowInput stream failed",
                event_type=LogEventType.WORKFLOW_COMPONENT_ERROR,
                exception=e,
            )
            self.error_to_output()
            raise build_error(
                StatusCode.COMPONENT_QUESTIONER_INVOKE_CALL_FAILED,
                error_msg="flow_input stream failed",
                cause=e,
            ) from e

    # -------------------------------------------------------------------------
    # 内部方法
    # -------------------------------------------------------------------------

    async def _handle_start_state(self, inputs, session, context, current_state):
        """处理 START 状态：写入 CustomSchema，session.interact() 中断"""
        query = FlowInputUtils.build_inputs_message(self._config)
        current_state.status = ExecutionStatus.USER_INTERACT
        current_state.question = query
        self._node_state = current_state

        self._store_state_to_session(current_state, session)

        custom_data = self._build_custom_data(session, query)
        await session.write_custom_stream(
            CustomSchema(type=PARTIAL_CONTENT, index=0, data=custom_data)
        )
        await session.write_custom_stream(
            CustomSchema(type=MESSAGE_NODE_END, index=1, data=custom_data)
        )
        self._stream_output = custom_data
        self._node_state.status = ExecutionStatus.END

        await session.interact(query)
        return {}

    async def _handle_interact_state(self, inputs, session, context, current_state):
        """处理 USER_INTERACT 状态：获取用户反馈，验证并返回"""
        user_response = await session.interact(current_state.question)
        inputs_copy = deepcopy(inputs) if isinstance(inputs, dict) else {}
        values = FlowInputUtils.parse_user_response(user_response)
        FlowInputUtils.fill_inputs(inputs_copy, values, self._config)
        FlowInputUtils.validate_inputs(inputs_copy, self._config)

        new_state = FlowInputState()
        self._node_state = new_state
        self._store_state_to_session(new_state, session)

        return {USER_FIELDS: inputs_copy}

    @property
    def node_type(self) -> str:
        return JIUWEN_FLOW_INPUT_TYPE

    @property
    def config(self) -> dict:
        return self._config


# =============================================================================
# 导出
# =============================================================================

__all__ = [
    "FlowInput",
    "FlowInputState",
    "FlowInputStartState",
    "FlowInputInteractState",
    "FlowInputEndState",
    "ExecutionStatus",
    "FlowInputEvent",
    "FlowInputUtils",
]
