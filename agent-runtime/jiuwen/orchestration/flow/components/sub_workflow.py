#  Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
import asyncio
import os
import re
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, AsyncGenerator

from jiuwen.common.exception.base import JiuWenBaseException, WorkflowAbortException
from jiuwen.common.exception.status_code import StatusCode
from jiuwen.common.log.base import logger
from jiuwen.context.history import ConversationHistory
from jiuwen.orchestration import Invokable
from jiuwen.orchestration.callbacks.span import Span
from jiuwen.orchestration.flow.chat_manager import ChatManager
from jiuwen.orchestration.flow.components.interactive_base import InteractiveComponent
from jiuwen.orchestration.flow.components.util import (
    format_pydantic_validation_error_message,
    process_output_of_interaction_component,
)
from jiuwen.orchestration.flow.constant import (
    WORKFLOW_INSTANCE_DICT,
    WORKFLOW_API_CONFIGS,
    MEM_MAP,
    WORKFLOW_CHAT_HISTORY,
    USER_FIELDS,
    WORKFLOW_CHAT_MANAGER,
    SYSTEM_FIELDS,
    ENVIRONMENT_VARIABLES,
    MEMORY_VARIABLES,
    ENABLE_MEMORY_RETRIEVE,
    USER_ID,
    APP_ID,
    REQUEST_VARIABLES,
)
from jiuwen.orchestration.flow.enum import ExecutionStatus, NodeType
from jiuwen.orchestration.flow.model.workflow_data_class import (
    WorkflowMetadata,
    WorkflowStreamingData,
)
from jiuwen.orchestration.flow.runtime_context import RuntimeContext
from jiuwen.orchestration.flow.state import State
from jiuwen.orchestration.flow.stream.base import StreamCode
from jiuwen.orchestration.utils import Input, Output
from pydantic import BaseModel, Field, ValidationError

LOG_VERBOSE_MODE = os.getenv("LOG_VERBOSE", "false").lower() == "true"


class Reference(BaseModel):
    id: str = Field(title="子workflow对应的workflow id")
    path: str = Field(title="子workflow对应的obs中的存储路径")


class SubWorkflowConfig(BaseModel):
    """
    子workflow组件 配置校验
    """

    user_fields: dict = Field(alias="userFields", default={})
    system_fields: dict = Field(alias="systemFields")
    pre_define_fields: dict = Field(alias="preDefineFields")
    reference: Reference = Field()


@dataclass
class SubWorkflowState(State):
    status: ExecutionStatus = ExecutionStatus.START


class SubWorkflow(Invokable, InteractiveComponent):
    """SubWorkflow node"""

    def __init__(
        self, conf: dict, runtime_context: RuntimeContext, metadata: WorkflowMetadata
    ):
        self._conf = conf
        self._validate_config()
        self._runtime_context = runtime_context
        self._chat_manager: ChatManager = runtime_context.get(WORKFLOW_CHAT_MANAGER)
        self._metadata = metadata
        self._workflow_instance = None  # 调用时再获取
        self.node_state = SubWorkflowState()

    @staticmethod
    async def _filter_stream_res(data_queue: asyncio.Queue):
        """
        通过队列读取子线程中子工作流流式输出内容，过滤START, WORKFLOW_START, WORKFLOW_END
        """
        while True:
            data = await data_queue.get()
            if data.code not in [
                StreamCode.START.value,
                StreamCode.WORKFLOW_START.value,
                StreamCode.WORKFLOW_END.value,
            ]:
                yield data
            if data.code == StreamCode.FINISH.value:
                break

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

    def reset(self) -> bool:
        """组件状态重置"""
        self.node_state.status = ExecutionStatus.START
        return True

    def get_state(self):
        return self.node_state

    def load_state(self, state: SubWorkflowState):
        """
        load sub_workflow state from input state
        """
        self.node_state = deepcopy(state)

    def invoke(self, inputs: Input, **kwargs) -> Output:
        pass

    async def ainvoke(self, inputs: dict[str, Any], **kwargs):
        """Invoke to assemble final answer."""
        self._workflow_instance = await self._get_workflow_instance()
        span: Span = kwargs.get("span")
        workflow_chat_history: ConversationHistory = self._runtime_context.get(
            WORKFLOW_CHAT_HISTORY
        )
        workflow_chat_history_dict = [
            message.model_dump(exclude_none=True)
            for message in workflow_chat_history.get_all_messages()
        ]

        # 当状态为START时，从inputs中取值，可能为别的组件的输出；当状态为USER_INTERACT时，需要从对话历史中获取用户的输入
        if self.node_state.status == ExecutionStatus.USER_INTERACT:
            # chat_history会拼接上最后一条用户输入，此列表一定有值
            query = workflow_chat_history_dict[-1].get("content")
        else:
            query = inputs.get(SYSTEM_FIELDS, {}).get("query")
        global_variables_dict = inputs.get(USER_FIELDS, {})
        global_variables_dict["userId"] = self._runtime_context.get(USER_ID)
        params = dict(
            conversation_history=workflow_chat_history_dict,
            plugin_configs=self._runtime_context.get(WORKFLOW_API_CONFIGS),
            global_variables=global_variables_dict,
            tool_switch_dict={},
            environment_variables=self._runtime_context.get(ENVIRONMENT_VARIABLES),
            memory_variables=self._runtime_context.get(MEMORY_VARIABLES),
            mem_map=self._runtime_context.get(MEM_MAP),
            enable_memory_retrieve=self._runtime_context.get(ENABLE_MEMORY_RETRIEVE),
            app_id=self._runtime_context.get(APP_ID),
        )

        message = query
        # workflow嵌套执行存在事件循环嵌套，所以此处直接使用线程池执行子workflow
        stream_related_info = WorkflowStreamingData(
            stream_callback=kwargs.get("stream_callback"), execution_id=span.trace_id
        )
        # 提交任务到线程池
        if stream_related_info.stream_callback:
            result, result_vals = await self.execute_stream_workflow(
                message, params, stream_related_info
            )
        else:
            result, result_vals = await self.invoke_workflow(message, params)

        # 把子工作流对 _request 变量的修改同步回父工作流的 runtime_context
        self._sync_sub_request_to_parent()

        # 更新子工作流状态
        self.node_state.status = self._workflow_instance.get_workflow_execute_status()

        if (
            self.node_state.status != ExecutionStatus.END
            and not stream_related_info.stream_callback
        ):
            # 子工作流需发送消息
            stream_related_info = WorkflowStreamingData(
                stream_callback=stream_related_info.stream_callback,
                execution_id=span.trace_id,
            )
            if isinstance(self._metadata, dict):
                self._metadata["should_interrupt"] = self.should_interrupt()
            elif isinstance(self._metadata, WorkflowMetadata):
                setattr(self._metadata, "should_interrupt", self.should_interrupt())
            await process_output_of_interaction_component(
                stream_related_info=stream_related_info,
                origin_output=dict(answer=result),
                chat_manager=self._chat_manager,
                metadata=self._metadata,
            )
        return dict(responseContent=result, userFields=result_vals or {})

    async def execute_stream_workflow(self, message, params, stream_related_info):
        """流式调用子工作流"""

        async def stream_run_sub_workflow(query_: str, params_: dict):
            """封装子工作流流式执行及 clean_up，捕获未知异常，打印到日志中"""
            try:
                self._workflow_instance.recover_chat_manager()
                await self._workflow_instance.astream(query_, params_)
            except Exception as e:
                logger.error(
                    f"Unexpected error encountered when stream running sub-workflow! Detail: {str(e)}",
                    simple_log=f"Unexpected error "
                    f"encountered when stream running sub-workflow! Detail: {type(e).__name__}",
                )
                try:
                    await self._workflow_instance.stream_out_queue.put(
                        ("ERROR", type(e).__name__)
                    )
                except Exception:
                    logger.error("Failed to enqueue ERROR event to stream_out_queue")
                raise
            finally:
                await self._workflow_instance.async_clean_up()

        self._workflow_instance = await self._get_workflow_instance()
        task = asyncio.create_task(stream_run_sub_workflow(message, params))
        # 读取流式结果，过滤 START, WORKFLOW_START, WORKFLOW_END
        stream_result = self._filter_stream_res(
            self._workflow_instance.stream_out_queue
        )
        # 流式转发
        result, result_vals = await self._process_stream_result(
            stream_result, stream_related_info
        )
        try:
            await task
        except Exception as ex:
            raise ex
        return result, result_vals

    async def invoke_workflow(self, message, params):
        """同步调用子工作流"""

        async def invoke_sub_workflow(query_: str, params_: dict):
            """封装子工作流非流式执行及 clean_up，捕获未知异常，打印到日志中"""
            try:
                self._workflow_instance = await self._get_workflow_instance()
                self._workflow_instance.recover_chat_manager()
                result_ = await self._workflow_instance.ainvoke(query_, params_)
                return result_
            except Exception as e:
                logger.error(
                    f"Unexpected error encountered when invoking sub-workflow! Detail: {str(e)}",
                    simple_log=f"Unexpected error "
                    f"encountered when invoking sub-workflow! Detail: {type(e).__name__}",
                )
                raise e
            finally:
                await self._workflow_instance.async_clean_up()

        result = await invoke_sub_workflow(message, params)
        # 结果中存在异常
        if "error_code" in result.data and "error_message" in result.data:
            raise JiuWenBaseException(
                error_code=StatusCode.SUB_WORKFLOW_EXECUTION_ERROR.code,
                message=StatusCode.SUB_WORKFLOW_EXECUTION_ERROR.errmsg,
            )
        # 获取正常执行结果
        result_vals = result.data.get("user_fields", {})
        result = result.data.get("answer")
        return result, result_vals

    async def _process_stream_result(
        self, result: AsyncGenerator, stream_related_info: WorkflowStreamingData
    ):
        """
        只发送，不接收。
        发送者：子工作流内流式返回对象，排除 end 节点。
        """

        def check_update_item_data(data):
            # 解决子工作流嵌套时，父工作流的parentNodeId覆盖子工作流的问题
            return "parentNodeId" not in data or not data.get("parentNodeId", None)

        def sanitize_message(message: str) -> str:
            # 屏蔽常见敏感字段，不区分大小写
            patterns = [
                r"(secret key:\s*)(\S+)",
                r"(password:\s*)(\S+)",
                r"(access token:\s*)(\S+)",
                r"(api key:\s*)(\S+)",
            ]
            for pattern in patterns:
                message = re.sub(pattern, r"\1***", message, flags=re.IGNORECASE)
            return message

        final_res = ""
        final_val = {}
        messages = []
        async for item in result:
            if (
                check_update_item_data(item.data)
                and StreamCode(item.code) != StreamCode.WORKFLOW_EXCEPTION
            ):
                item.data.update(dict(parentNodeId=self._metadata.node_id))
            item.execution_id = stream_related_info.execution_id
            if item.code in [
                StreamCode.WORKFLOW_NODE_MESSAGE.value
            ] and check_update_item_data(item.data):
                item.data.update(dict(traceId=stream_related_info.execution_id))
            if item.code in [StreamCode.PARTIAL_CONTENT.value, StreamCode.ERROR.value]:
                if "workflow_id" not in item.data:
                    item.data.update(
                        dict(workflow_id=self._workflow_instance.get_workflow_id())
                    )
            if item.code == StreamCode.FINISH.value:
                final_val = item.data.get("user_fields", {})
                continue
            is_end_msg_event = item.data.get(
                "node_type"
            ) == NodeType.END.value and item.code in [
                StreamCode.PARTIAL_CONTENT.value,
                StreamCode.MESSAGE_END.value,
            ]
            if not is_end_msg_event:
                await stream_related_info.stream_callback.on_recv(item)
            if item.code == StreamCode.WORKFLOW_EXCEPTION.value:
                abort_data = item.data
                e = WorkflowAbortException(data=abort_data)
                # 标记这是子工作流异常
                setattr(e, "_from_subworkflow", True)
                raise e
            if item.code in [StreamCode.ERROR.value]:
                raw_msg = (
                    item.data.get("error_message")
                    if "error_message" in item.data
                    else item.data.get("message")
                )
                safe_msg = sanitize_message(raw_msg)
                raise JiuWenBaseException(
                    error_code=StatusCode.SUB_WORKFLOW_EXECUTION_ERROR.code,
                    message=StatusCode.SUB_WORKFLOW_EXECUTION_ERROR.errmsg.format(
                        msg=raw_msg if LOG_VERBOSE_MODE else safe_msg
                    ),
                )
            if item.code == StreamCode.MESSAGE_END.value:
                messages.append(final_res)
                final_res = ""
                continue
            if item.code in [StreamCode.PARTIAL_CONTENT.value]:
                final_res = final_res + item.data.get("answer")
        final_res = messages[-1] if messages else final_res
        return final_res, final_val

    def _sync_sub_request_to_parent(self) -> None:
        """子工作流执行完毕后，将子工作流对 REQUEST 变量的修改同步回父工作流的 runtime_context。

        只更新父已声明的 key，防止子工作流内部临时变量污染父的 _session。
        """
        if not self._workflow_instance:
            return
        try:
            sub_rt = self._workflow_instance.runtime_context
            sub_request_vars = sub_rt.get(REQUEST_VARIABLES) or {}
            if not sub_request_vars:
                return
            parent_request_vars = self._runtime_context.get(REQUEST_VARIABLES) or {}
            updated = {
                k: sub_request_vars[k]
                for k in parent_request_vars
                if k in sub_request_vars
            }
            if updated:
                parent_request_vars.update(updated)
                self._runtime_context.set(REQUEST_VARIABLES, parent_request_vars)
                logger.info(
                    f"Sub-workflow request variables synced to parent runtime_context: {updated}"
                )
        except Exception as e:
            logger.warning(
                f"Failed to sync sub-workflow request variables to parent runtime_context: {e}"
            )

    async def _get_workflow_instance(self):
        if self._workflow_instance:
            self._workflow_instance.stream_out_queue = asyncio.Queue()
            return self._workflow_instance
        workflow_instance_map = self._runtime_context.get(WORKFLOW_INSTANCE_DICT) or {}
        workflow_id = self._conf.get("reference", {}).get("id", "")
        workflow_instance = workflow_instance_map.get(self._metadata.node_id)
        if not workflow_instance:
            logger.error("Failed to get sub workflow instance")
            raise JiuWenBaseException(
                error_code=StatusCode.SUB_WORKFLOW_INIT_ERROR.code,
                message=StatusCode.SUB_WORKFLOW_INIT_ERROR.errmsg.format(
                    workflow_id=workflow_id
                ),
            )
        workflow_instance = await workflow_instance.instantiate()
        return workflow_instance

    def _validate_config(self):
        try:
            SubWorkflowConfig.model_validate(self._conf)
        except ValidationError as e:
            raise JiuWenBaseException(
                error_code=StatusCode.SUB_WORKFLOW_CONFIGURATION_VALIDATION_ERROR.code,
                message=StatusCode.SUB_WORKFLOW_CONFIGURATION_VALIDATION_ERROR.errmsg.format(
                    msg=format_pydantic_validation_error_message(e)
                    if LOG_VERBOSE_MODE
                    else f"{type(e).__name__}"
                ),
            ) from e
