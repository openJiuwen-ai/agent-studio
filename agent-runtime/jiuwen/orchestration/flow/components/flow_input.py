#  Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
import json
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from jiuwen.common.exception.base import JiuWenBaseException
from jiuwen.common.exception.status_code import StatusCode
from jiuwen.orchestration import Invokable
from jiuwen.orchestration.callbacks.span import Span
from jiuwen.orchestration.flow.components.interactive_base import InteractiveComponent
from jiuwen.orchestration.flow.components.util import (
    process_output_of_interaction_component,
)
from jiuwen.orchestration.flow.constant import (
    USER_FIELDS,
    WORKFLOW_CHAT_MANAGER,
    TYPE_DEFAULT_VALUE_DICT,
    WORKFLOW_CHAT_HISTORY,
)
from jiuwen.orchestration.flow.enum import ExecutionStatus
from jiuwen.orchestration.flow.model.workflow_data_class import (
    WorkflowMetadata,
    WorkflowStreamingData,
)
from jiuwen.orchestration.flow.state import State
from jiuwen.orchestration.flow.stream.workflow_streaming import WorkflowStreamCallback
from jiuwen.orchestration.utils import Input


@dataclass
class InputState(State):
    status: ExecutionStatus = ExecutionStatus.START


class FlowInput(Invokable, InteractiveComponent):
    """Input node."""

    def __init__(self):
        self.conf = None
        self.runtime_context = None
        self.metadata = None
        self.chat_manager = None
        self.node_state = InputState()
        super().__init__()

    @staticmethod
    def get_latest_k_rounds_chat(chat_history: list, k: int) -> list:
        """
        get the chat history of the last k rounds.
        chat_history: [... prev_question, prev_query] + [cur_question, cur_query ...]
        """
        if k is None:
            return chat_history
        return chat_history[-k * 2 - 1 :]

    def get_latest_chat_history(self, k=None):
        """
        get the latest chat history from runtime_context
        """
        chat_history = deepcopy(self.runtime_context.get(WORKFLOW_CHAT_HISTORY, None))
        if chat_history:
            chat_history = chat_history.get_conversation_history()
        else:
            chat_history = []
        chat_history = self.get_latest_k_rounds_chat(chat_history, k)
        # get the latest k chat history
        return chat_history

    def init(self, conf: dict, **kwargs):
        if self.node_state.status == ExecutionStatus.USER_INTERACT:
            return

        runtime_context = kwargs.get("runtime_context")
        metadata = kwargs.get("metadata")
        self.conf = conf
        self.runtime_context = runtime_context
        self.metadata = metadata
        self.chat_manager = runtime_context.get(WORKFLOW_CHAT_MANAGER)
        self.node_state = InputState()
        super().__init__()

    def should_interrupt(self) -> bool:
        """
        check if should be interrupted

        Returns:
            bool: The result of the interruption.
        """
        return self.node_state.status == ExecutionStatus.USER_INTERACT

    def error_to_output(self):
        """发生异常时，走默认值或者异常分支时，状态按正常结束算"""
        self.node_state.status = ExecutionStatus.END

    def get_state(self):
        """
        get input state
        """
        return self.node_state

    def load_state(self, state: InputState):
        """
        load input state from input state
        """
        self.node_state = deepcopy(state)

    def get_node_status(self):
        """
        返回节点状态
        :return:
        """
        return self.node_state.status

    async def await_by_stream_callback(self, stream_callback, answer, span: Span):
        """适配流式以及非流式调用"""
        if not stream_callback:
            answer = {"answer": answer}
        stream_related_info = WorkflowStreamingData(
            stream_callback=stream_callback, execution_id=span.trace_id
        )
        if isinstance(self.metadata, dict):
            self.metadata["should_interrupt"] = self.should_interrupt()
        elif isinstance(self.metadata, WorkflowMetadata):
            setattr(self.metadata, "should_interrupt", self.should_interrupt())
        await process_output_of_interaction_component(
            stream_related_info=stream_related_info,
            origin_output=answer,
            chat_manager=self.chat_manager,
            metadata=self.metadata,
        )

    def invoke(self, inputs: dict[str, Any], **kwargs):
        pass

    async def ainvoke(self, inputs: Input, **kwargs):
        stream_callback: WorkflowStreamCallback = kwargs.get("stream_callback")
        debug_info = dict(
            component_metadata=kwargs.get("component_metadata", {}),
            runtime_context=kwargs.get("runtime_context", {}),
            span=kwargs.get("span"),
        )
        inputs_copy = inputs.copy()

        query = self._need_inputs_message()
        if self.node_state.status == ExecutionStatus.START:
            # 调用过程
            self.node_state.status = ExecutionStatus.USER_INTERACT
            await self.await_by_stream_callback(
                stream_callback, query, debug_info.get("span")
            )
            return {USER_FIELDS: inputs_copy}

        if self.node_state.status == ExecutionStatus.USER_INTERACT:
            conv_history = self.get_latest_chat_history()
            # content 可能缺失（None），按空串兜底，避免 None.split 崩溃
            user_response = (
                conv_history[-1].get("content") or "" if conv_history else ""
            )
            # 逐行解析 "field: value"；用户回复是自由文本，
            # 不含冒号的行（含末尾换行产生的空行）直接跳过，
            # 缺失字段由下方 field not in values 的结构化异常兜底
            values = {
                value.split(":", 1)[0]: value.split(":", 1)[1]
                for value in user_response.split("\n")
                if ":" in value
            }

            for input_config in self.conf.get(USER_FIELDS, {}).get("inputs", []):
                field = input_config["id"]
                if field not in values:
                    raise JiuWenBaseException(
                        StatusCode.WORKFLOW_INPUT_FIELD_EMPTY_ERROR.code,
                        StatusCode.WORKFLOW_INPUT_FIELD_EMPTY_ERROR.errmsg.format(
                            field=field
                        ),
                    )
                required = input_config["required"]
                flow_type = input_config["type"]
                # 如果是非必填，且输入为空
                input_value = values.get(field)
                if not required and not input_value:
                    input_value = TYPE_DEFAULT_VALUE_DICT.get(flow_type, None)
                inputs_copy[field] = input_value

            self.node_state.status = ExecutionStatus.END
            return {USER_FIELDS: inputs_copy}

    def _validate_inputs(self, inputs):
        """
        Check whether the user has passed in all global_variables defined in the config.
        """
        pass

    def _need_inputs_message(self):
        """
        输入节点给出需要提取的参数信息，供前端取用。
        """
        key_inputs = "inputs"
        inputs_need: list[dict] = self.conf.get(USER_FIELDS, {}).get(key_inputs, [])

        def convert_format(arg_conf: dict):
            keys_to_convert = {
                "id": "name",
            }
            converted = {keys_to_convert.get(k, k): v for k, v in arg_conf.items()}
            # 替换type为actualType
            values_to_convert = {
                "type": "actualType",
            }
            converted = {
                k: converted.get(values_to_convert[k], v)
                if k in values_to_convert
                else v
                for k, v in converted.items()
            }
            return converted

        inputs_info = {"inputs": [convert_format(item) for item in inputs_need]}
        return json.dumps(inputs_info, ensure_ascii=False)
