#  Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.

"""
Utilities for async execution
"""

from typing import Iterable

from jiuwen.common.exception.base import JiuWenBaseException
from jiuwen.common.exception.status_code import StatusCode
from jiuwen.orchestration.flow.constant import WORKFLOW_UNIFIED_ERROR_INFORMATION_UNSAFE
from jiuwen.orchestration.flow.enum import ExecutionStatus
from jiuwen.orchestration.flow.stream.base import StreamCode
from jiuwen.orchestration.flow.workflow import Workflow
from jiuwen.serve.controllers.execution.enum import (
    AsyncExecutionStatus,
    ConversationEvent,
)
from jiuwen.serve.controllers.execution.manager import (
    AsyncExecStateManager,
    ExecutionResultManager,
)
from jiuwen.serve.controllers.execution.types import (
    AsyncExecutionState,
    StreamingChatResponse,
    AsyncExecutionResponse,
)
from jiuwen.serve.controllers.execution.utils import (
    get_current_time_ms,
    item_code_to_conversation_event_type,
    update_state_of_workflow,
)


# COM-08 §4.7B 条3: 不以 item.data.get("message") / e.message 作为公开文案来源；
# 两种 LOG_VERBOSE 配置 wire 一致。SYNC-01 P5-R3 Phase 2 落地（与 execution/utils.py 对齐）。
_SAFE_PUBLIC_ERROR_MESSAGE = "系统内部错误，请参考错误码并联系系统管理员"


def get_conversation_history(conversation_key=None):
    """
    第三方需重写此接口，用于获取对话历史
    返回格式参考：
        [
            {
              "role": "",
              "content": ""
            }
        ]
    """
    return []


def handle_init_exceptions(e: JiuWenBaseException, exec_id, conv_id):
    """
    Handle the exception occurring during Workflow initialization.
    """
    # 将执行状态标记为失败
    AsyncExecStateManager().set_state_status(conv_id, AsyncExecutionStatus.FAILED)

    start_stream_data = StreamingChatResponse(
        event=ConversationEvent.START,
        index=0,
        executionId=exec_id,
        data={},
        createdTime=get_current_time_ms(),
    )

    error_stream_data = StreamingChatResponse(
        event=ConversationEvent.ERROR,
        index=0,
        executionId=exec_id,
        data={"code": e.error_code, "message": _SAFE_PUBLIC_ERROR_MESSAGE},
        createdTime=get_current_time_ms(),
    )

    done_stream_data = StreamingChatResponse(
        event=ConversationEvent.DONE,
        index=0,
        executionId=exec_id,
        data={},
        createdTime=get_current_time_ms(),
    )

    ExecutionResultManager().append_message(exec_id, start_stream_data)
    ExecutionResultManager().append_message(exec_id, error_stream_data)
    ExecutionResultManager().append_message(exec_id, done_stream_data)

    messages = ExecutionResultManager().get_messages(exec_id)
    async_execute_resp = AsyncExecutionResponse(
        status=AsyncExecutionStatus.FAILED,
        time=get_current_time_ms(),
        messages=messages,
    )
    return async_execute_resp.model_dump_json(by_alias=True, exclude_none=True)


def post_process_workflow_streaming_output_async(
    conversation_id: str, origin_output: Iterable, workflow_instance: Workflow
) -> AsyncExecutionStatus:
    """
    Processes the original workflow streaming output result in a structured manner.
    Processing may be accompanied by state update operations.
    """
    # 每次对话都需要先生成一个start标识
    start_flag = True
    execution_id = ""
    error_flag = False
    error_code = 0

    for item in origin_output:
        if not execution_id:
            execution_id = item.execution_id
        if start_flag:
            start_stream_data = StreamingChatResponse(
                event=ConversationEvent.START,
                index=0,
                executionId=item.execution_id,
                data={},
                createdTime=get_current_time_ms(),
                isStructMessage=item.is_struct_message,
            )
            start_flag = False
            ExecutionResultManager().append_message(execution_id, start_stream_data)

        if item.code == StreamCode.ERROR.value:
            code_of_data = item.data.get("code") or ""
            item.data.update(
                dict(
                    message=WORKFLOW_UNIFIED_ERROR_INFORMATION_UNSAFE.format(
                        code_of_data, _SAFE_PUBLIC_ERROR_MESSAGE
                    )
                )
            )
            error_flag = True
            error_code = code_of_data
        static_data_res = StreamingChatResponse(
            event=item_code_to_conversation_event_type.get(item.code),
            data=item.data,
            index=item.index,
            executionId=item.execution_id,
            createdTime=get_current_time_ms(),
            isStructMessage=item.is_struct_message,
        )
        ExecutionResultManager().append_message(execution_id, static_data_res)

    execution_status: ExecutionStatus = workflow_instance.get_workflow_execute_status()

    # 修改数据库中的AsyncExecutionStatus
    cur_async_exec_state: AsyncExecutionState = (
        AsyncExecStateManager().get_state_parsed(conversation_id)
    )
    async_exec_status: AsyncExecutionStatus = _get_conv_status_by_exec_status(
        cur_async_exec_state.status, execution_status, error_code
    )
    AsyncExecStateManager().set_state_status(conversation_id, async_exec_status)

    # 更新或者删除存储介质中的workflow state
    update_state_of_workflow(
        conversation_id=conversation_id,
        workflow_instance=workflow_instance,
        error_flag=error_flag,
    )
    # 流式执行结束，清理workflow对象
    workflow_instance.clean_up()
    return async_exec_status


def _get_conv_status_by_exec_status(
    current_async_exec_status: AsyncExecutionStatus,
    execution_status: ExecutionStatus,
    error_code: int,
) -> AsyncExecutionStatus:
    # canceled / timeout / failed / success 为最终状态，不能再被修改为其他状态
    if current_async_exec_status in [
        AsyncExecutionStatus.CANCELED,
        AsyncExecutionStatus.TIMEOUT,
        AsyncExecutionStatus.FAILED,
        AsyncExecutionStatus.SUCCESS,
    ]:
        return current_async_exec_status

    if error_code in [StatusCode.WORKFLOW_TERMINATION_OF_EXECUTION.code]:
        return AsyncExecutionStatus.CANCELED
    if error_code in [StatusCode.WORKFLOW_COMPONENT_EXECUTE_TIMEOUT.code]:
        return AsyncExecutionStatus.TIMEOUT
    if execution_status == ExecutionStatus.USER_INTERACT:
        return AsyncExecutionStatus.INTERACTING
    if execution_status == ExecutionStatus.END:
        return AsyncExecutionStatus.SUCCESS

    return AsyncExecutionStatus.FAILED
