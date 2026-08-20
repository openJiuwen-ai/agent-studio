#  Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
"""insight callback handler"""

import os
from abc import ABCMeta
from enum import Enum
from typing import Dict, List, Union, Any

from jiuwen.common.exception.base import JiuWenBaseException, InnerException
from jiuwen.common.exception.status_code import StatusCode
from jiuwen.common.log.base import logger
from jiuwen.insight.handlers.data import InvokeData4Callback
from jiuwen.insight.handlers.remote import get_client
from jiuwen.insight.utils import INSIGHT_EI_DEBUG_INFO_ENABLE
from jiuwen.orchestration.callbacks.base import BaseCallbackHandler
from jiuwen.orchestration.flow.enum import NodeType
from jiuwen.orchestration.flow.enum import StreamDataMsg
from jiuwen.orchestration.flow.runtime_context import RuntimeContext
from jiuwen.orchestration.flow.stream.base import StreamData, StreamCode
from jiuwen.orchestration.flow.stream.workflow_streaming import WorkflowStreamCallback
from jiuwen.orchestration.utils import Output, Input


class Insight4CallbackHandler(BaseCallbackHandler, metaclass=ABCMeta):
    """insight handler for callback"""

    def __init__(self):
        self.invoke_map: Dict[str, InvokeData4Callback] = {}
        self.on_invoke_map: Dict[str, List[dict]] = {}
        self.invoke_map_4_llm: Dict[str, InvokeData4Callback] = {}
        self.client = get_client()
        self.workflow_debug_info = bool(
            str(os.environ.get(INSIGHT_EI_DEBUG_INFO_ENABLE)).lower() == "true"
        )
        self.retry_invoke_data: Dict[str, InvokeData4Callback] = {}

    @staticmethod
    async def _call_send_msg(
        invoke: InvokeData4Callback, stream_callback: WorkflowStreamCallback
    ):
        """Send workflow node message; builds payload once without mutating invoke."""
        # Single serialization: build payload dict once and add status (no intermediate model).
        data = invoke.model_dump(mode="json", by_alias=True)
        # Normalize outputs only in payload dict, keep invoke unchanged.
        if data.get("outputs") == "":
            data["outputs"] = None
        data["status"] = get_component_status(invoke)
        item = StreamData(
            code=StreamCode.WORKFLOW_NODE_MESSAGE,
            data=data,
            execution_id=invoke.trace_id,
            msg=StreamDataMsg.SUCCESS.value,
        )
        await stream_callback.on_recv(item)

    async def on_pre_invoke(self, inputs: Input, *args: Any, **kwargs: Any) -> Any:
        """input pre invoke"""
        invoke_data_for_save = InvokeData4Callback()
        invoke_data = kwargs.get("component_metadata")
        span_data = kwargs.get("span_instance")
        runtime_ctx: RuntimeContext = kwargs.get("runtime_context")
        stream_callback: WorkflowStreamCallback = runtime_ctx.get("stream_callback")
        invoke_data_for_save.dict_to_attrs(invoke_data)
        invoke_data_for_save.dict_to_attrs(
            {
                "invoke_id": span_data.span_id,
                "parent_invoke_id": span_data.parent_id,
                "trace_id": span_data.trace_id,
                "inputs": inputs,
                "start_time": invoke_data["current_time"],
            }
        )
        if invoke_data.get("component_type") == NodeType.SUB_WORKFLOW.value:
            sub_workflow_id = invoke_data["component_config"]["reference"]["id"]
            mem_map = runtime_ctx.get("mem_map", {})
            memory_variables = runtime_ctx.get("memory_variables", {})

            mem_to_save = {
                mem_map[target_key].split(".")[-1]: memory_variables[
                    mem_map[target_key]
                ]
                for target_key in mem_map
                if target_key.split(".")[0] == sub_workflow_id
                and mem_map[target_key] in memory_variables
            }

            invoke_data_for_save.dict_to_attrs({"memory": mem_to_save})

        self._start_trace(invoke_data_for_save)
        await self._send_invoke_data(invoke_data_for_save, stream_callback)
        self._start_trace_4_llm(invoke_data_for_save)

    async def on_invoke(
        self, data: Union[JiuWenBaseException, dict], *args: Any, **kwargs: Any
    ) -> Any:
        """error or on invoke data"""
        invoke_data = kwargs.get("component_metadata")
        span_data = kwargs.get("span_instance")
        runtime_ctx: RuntimeContext = kwargs.get("runtime_context")
        stream_callback: WorkflowStreamCallback = runtime_ctx.get("stream_callback")
        invoke_id = span_data.span_id
        on_invoke_data = data
        _exception = kwargs.get("exception")

        if _exception:
            invoke_data_in_map = self._get_invoke_data(invoke_id)
            if not invoke_data_in_map and invoke_data.get("component_type") == "LLM":
                invoke_data_in_map = self._get_invoke_data_4_llm(
                    span_data.trace_id, invoke_id
                )
                self._end_trace_4_llm(span_data.trace_id, invoke_id)
                # 最后一次发送该llm的异常调测信息，清空该节点的重试缓存信息
                if not isinstance(_exception, InnerException):
                    self.retry_invoke_data.pop(invoke_id, None)
            if not invoke_data_in_map:
                logger.error(
                    f"save data failed, cause of the component: {invoke_data.get('component_type')}"
                    f" send on_invoke after on_post_invoke or does not send on_pre_invoke"
                )
                return
            # 重试场景下，仅在需要时保存一份“干净”快照，用于后续重新初始化调测信息
            if (
                isinstance(_exception, InnerException)
                and invoke_id not in self.retry_invoke_data
            ):
                self.retry_invoke_data[invoke_id] = _copy(invoke_data_in_map)
            if isinstance(_exception, JiuWenBaseException):
                invoke_data_in_map.error = {
                    "error_code": _exception.error_code,
                    "message": _exception.message,
                }
            elif isinstance(_exception, InnerException):
                invoke_data_in_map.inner_error = _exception.to_alias_dict()
            else:
                invoke_data_in_map.error = {
                    "error_code": StatusCode.ERROR.code,
                    "message": repr(_exception),
                }
            # update end time
            invoke_data_in_map.end_time = invoke_data["current_time"]

            invoke_data_in_map.on_invoke_data = self._get_on_invoke_data(invoke_id)
            if on_invoke_data:
                invoke_data_in_map.on_invoke_data.append(on_invoke_data)
            self._end_trace(invoke_id)
            await self._send_invoke_data(invoke_data_in_map, stream_callback)
            self._clear_llm_tmp_data_when_error(invoke_data_in_map)

            # 重试情况，需要重新初始化调测信息
            if isinstance(_exception, InnerException):
                invoke_data_for_save = _copy(self.retry_invoke_data.get(invoke_id))
                if not invoke_data_for_save:
                    return
                self._start_trace(invoke_data_for_save)
                self._start_trace_4_llm(invoke_data_for_save)

        else:
            self.on_invoke_map.setdefault(invoke_id, []).append(on_invoke_data)
            await self._process_on_invoke_message(
                invoke_id,
                invoke_data.get("current_time"),
                stream_callback,
                invoke_data.get("component_type"),
                span_data,
            )

    async def on_post_invoke(self, outputs: Output, *args: Any, **kwargs: Any) -> Any:
        """output post invoke"""
        invoke_data = kwargs.get("component_metadata")
        inputs = kwargs.get("inputs")
        span_data = kwargs.get("span_instance")
        runtime_ctx: RuntimeContext = kwargs.get("runtime_context")
        stream_callback: WorkflowStreamCallback = runtime_ctx.get("stream_callback")
        invoke_id = span_data.span_id

        invoke_data_in_map = self._get_invoke_data(invoke_id)
        if not invoke_data_in_map and invoke_data.get("component_type") == "LLM":
            invoke_data_in_map = self._get_invoke_data_4_llm(
                span_data.trace_id, invoke_id
            )
            self._end_trace_4_llm(span_data.trace_id, invoke_id)
            # 最后一次发送该llm的调测信息，清空该节点的重试缓存信息
            self.retry_invoke_data.pop(invoke_id, None)

        if not invoke_data_in_map:
            logger.error(
                f"component type: {invoke_data.get('component_type')}, get_invoke_data failed"
            )
            return

        if inputs and invoke_data.get("component_type") in ["End", "Message"]:
            # 为了处理end以及message组件引用流式输出的问题，end以及message组件在流式
            invoke_data_in_map.inputs = inputs

        invoke_data_in_map.dict_to_attrs(
            {"outputs": outputs, "end_time": invoke_data.get("current_time")}
        )

        invoke_data_in_map.on_invoke_data = self._get_on_invoke_data(invoke_id)

        if invoke_data.get("component_type") == NodeType.SUB_WORKFLOW.value:
            sub_workflow_id = invoke_data["component_config"]["reference"]["id"]
            mem_map = runtime_ctx.get("mem_map", {})
            memory_variables = runtime_ctx.get("memory_variables", {})

            mem_to_save = {
                source_key.split(".")[-1]: memory_variables[target_key]
                for target_key, source_key in mem_map.items()
                if target_key.split(".")[0] == sub_workflow_id
                and target_key in memory_variables
            }

            invoke_data_in_map.dict_to_attrs({"memory": mem_to_save})

        if invoke_data.get("component_type") != "LLM":
            self.retry_invoke_data.pop(invoke_id, None)

        if invoke_data.get("component_type") == "LLM" and outputs:
            # 最后一次发送该llm的正常调测信息，清空该节点的重试缓存信息；llm第一次发送的结束帧不用清空
            self.retry_invoke_data.pop(invoke_id, None)

        self._end_trace(invoke_id)
        await self._send_invoke_data(invoke_data_in_map, stream_callback)
        self._clear_llm_tmp_data_normal(invoke_data_in_map)

    async def _process_on_invoke_message(
        self, invoke_id, end_time, stream_callback, invoke_type, span_data
    ):
        """process on invoke data status is Running"""
        invoke_data = self._get_invoke_data(invoke_id)
        # 大模型节点会在第一次调用on_post_invoke之后，发出多次on_invoke数据，需要从invoke_map_4_llm获取数据
        if invoke_type == "LLM" and invoke_data is None:
            invoke_data_in_map = _copy(
                self._get_invoke_data_4_llm(span_data.trace_id, invoke_id)
            )
        else:
            invoke_data_in_map = _copy(invoke_data)
        invoke_data_in_map.end_time = end_time
        invoke_data_in_map.on_invoke_data = self._get_on_invoke_data(invoke_id)
        await self._send_invoke_data(invoke_data_in_map, stream_callback)

    async def _send_invoke_data(
        self, invoke: InvokeData4Callback, stream_callback: WorkflowStreamCallback
    ):
        """save invoke data"""
        if self.workflow_debug_info:
            # send message
            if stream_callback:
                await self._call_send_msg(invoke, stream_callback)
            return

    def _get_invoke_data(self, invoke_id: str) -> InvokeData4Callback:
        """get invoke data by invoke_id"""
        invoke_data = self.invoke_map.get(invoke_id)
        return invoke_data

    def _get_invoke_data_4_llm(
        self, trace_id: str, invoke_id: str
    ) -> InvokeData4Callback:
        """get invoke data by invoke_id"""
        invoke_data = self.invoke_map_4_llm.get(invoke_id + trace_id)
        return invoke_data

    def _get_on_invoke_data(self, invoke_id: str):
        """获取 invoke_id 对应的具体的 on_invoke_data 信息，即此次调用需要记录的一些中间信息，如果没有，则返回 None"""
        on_invoke_data = self.on_invoke_map.get(invoke_id, [])
        return on_invoke_data

    def _start_trace(self, invoke: InvokeData4Callback):
        """save invokable data in map"""
        self.invoke_map[str(invoke.invoke_id)] = invoke

    def _start_trace_4_llm(self, invoke: InvokeData4Callback):
        """save invokable data 4 llm"""
        # when NodeType is LLM, record the data and waiting for the stream LLM END
        if invoke.component_type == "LLM":
            self.invoke_map_4_llm[str(invoke.invoke_id + invoke.trace_id)] = invoke

    def _end_trace(self, current_invoke_id: str):
        """remove invokable data in map"""
        self.invoke_map.pop(str(current_invoke_id), None)
        self.on_invoke_map.pop(str(current_invoke_id), None)

    def _end_trace_4_llm(self, trace_id: str, current_invoke_id: str):
        """remove invokable data 4 llm"""
        key = str(current_invoke_id + trace_id)
        self.invoke_map_4_llm.pop(key, None)

    def _clear_llm_tmp_data_normal(self, invoke: InvokeData4Callback):
        """remove invokable data 4 llm end"""
        if invoke.component_type == "End" and invoke.end_time:
            self._end_trace_4_llm_normal(invoke)

    def _clear_llm_tmp_data_when_error(self, invoke: InvokeData4Callback):
        """remove invokable data 4 llm error"""
        if invoke.error:
            self._end_trace_4_llm_normal(invoke)

    def _end_trace_4_llm_normal(self, invoke: InvokeData4Callback):
        """remove invokable data 4 llm normal"""
        key_to_delete = [
            key for key in self.invoke_map_4_llm if key.startswith(invoke.invoke_id)
        ]
        for key in key_to_delete:
            self.invoke_map_4_llm.pop(str(key))


def _copy(invoke: InvokeData4Callback) -> InvokeData4Callback:
    """copy data"""
    copy_fn = getattr(invoke, "model_copy", None)
    if copy_fn is not None:
        return copy_fn(deep=True)
    try:
        return invoke.copy(deep=True)
    except TypeError:
        return invoke.copy()


class NodeStatus(Enum):
    """status for workflow node message"""

    START = "start"
    FINISH = "finish"
    RUNNING = "running"
    ERROR = "error"


def get_component_status(invoke: InvokeData4Callback) -> str:
    """status for workflow node message"""
    if invoke.error or invoke.inner_error:
        return NodeStatus.ERROR.value
    if invoke.on_invoke_data:
        return (
            NodeStatus.RUNNING.value if not invoke.outputs else NodeStatus.FINISH.value
        )
    if invoke.end_time:
        return NodeStatus.FINISH.value if invoke.outputs else NodeStatus.RUNNING.value
    return NodeStatus.START.value
