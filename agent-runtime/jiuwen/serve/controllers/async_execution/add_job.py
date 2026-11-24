#  Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.

"""
Async workflow execution for apscheduler
"""

import asyncio
import os

from jiuwen.common.configs.env_constants import ASYNC_WORKER_ID_KEY
from jiuwen.common.exception.base import JiuWenBaseException
from jiuwen.common.exception.status_code import StatusCode
from jiuwen.common.log.base import logger
from jiuwen.common.utils.utils import safe_json_loads
from jiuwen.orchestration.flow.workflow import sync_build_workflow
from jiuwen.serve.common.exception.exception_handler import hide_security
from jiuwen.serve.controllers.async_execution.aps_server.constants import JobStatus
from jiuwen.serve.controllers.async_execution.utils import (
    handle_init_exceptions,
    get_conversation_history,
    post_process_workflow_streaming_output_async,
)
from jiuwen.serve.controllers.execution.enum import AsyncExecutionStatus
from jiuwen.serve.controllers.execution.ir_converter import IRConverter
from jiuwen.serve.controllers.execution.manager import StateManager, ApsRedisManager
from jiuwen.serve.controllers.execution.open_utils import deserialize_object
from jiuwen.serve.schemas.orchestration_mgr import ExecutionRequest
from starlette.datastructures import Headers


def async_execute_workflow_apscheduler(task):
    """
    Async execute workflow for apscheduler
    """
    # 如果当前是异步工作流的执行，则运行在线程池的线程中，需要创建事件循环
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    ir_data = task.get("ir_data")
    exec_id = task.get("exec_id")
    worker_id = os.environ.get(ASYNC_WORKER_ID_KEY)
    if not worker_id:
        raise JiuWenBaseException(
            error_code=StatusCode.WORKFLOW_ASYNC_EXECUTION_WORKER_ID_ERROR.code,
            message=StatusCode.WORKFLOW_ASYNC_EXECUTION_WORKER_ID_ERROR.errmsg.format(
                reason="worker_id not found"
            ),
        )

    req = ExecutionRequest.model_validate(safe_json_loads(task.get("req_str")))
    req.headers = Headers(req.headers)

    # 异步执行时对话历史按需调用接口获取
    req.params.conversation_history = get_conversation_history(
        req.params.conversation_key
    )

    logger.info(f"Processing job {exec_id} on {worker_id}...")

    try:
        if ir_data:
            # 走workflow初始化
            logger.info("11111")
            wf = IRConverter.ir_to_workflow(
                ir_data,
                x_auth_token=req.headers.get("X-Auth-Token"),
                execution_id=exec_id,
            )
        else:
            logger.info("2222")
            # 走workflow恢复
            serialized_data = StateManager().get_state(req.conversation_id)
            workflow_state = deserialize_object(serialized_data=serialized_data)
            wf = sync_build_workflow(workflow_state)
    except JiuWenBaseException as e:
        logger.error(f"Job {exec_id} failed on {worker_id}!")
        # 将任务从running_jobs队列中删除
        ApsRedisManager().remove_job_from_running_jobs(worker_id, exec_id)
        return handle_init_exceptions(e, exec_id, req.conversation_id)
    except Exception as err:
        logger.error(f"Job {exec_id} failed on {worker_id}!")
        # 将任务从running_jobs队列中删除
        ApsRedisManager().remove_job_from_running_jobs(worker_id, exec_id)

        e = JiuWenBaseException(
            error_code=StatusCode.WORKFLOW_INITIALIZATION_ERROR.code,
            message=StatusCode.WORKFLOW_INITIALIZATION_ERROR.errmsg.format(
                reason=hide_security(err)
            ),
        )
        return handle_init_exceptions(e, exec_id, req.conversation_id)

    # 更新为执行中状态
    ApsRedisManager().set_job_metadata(exec_id, job_status=JobStatus.RUNNING)
    streaming_output = wf.stream(query=req.query, params=req.params.model_dump())

    # 将迭代器中的message实时保存到redis，修改redis中的执行状态，清理资源
    async_exec_status: AsyncExecutionStatus = (
        post_process_workflow_streaming_output_async(
            conversation_id=req.conversation_id,
            origin_output=streaming_output,
            workflow_instance=wf,
        )
    )

    # 更新任务状态
    job_status = JobStatus.FINISHED
    ApsRedisManager().set_job_metadata(exec_id, job_status=job_status)

    logger.info(
        f"Job {exec_id} is finished on Worker {worker_id}! Execution is {async_exec_status.value}!"
    )

    # 将任务从running_jobs队列中删除
    ApsRedisManager().remove_job_from_running_jobs(worker_id, exec_id)

    # 任务执行结果并不太有用
    return True


def async_cancel_execution_apscheduler(task):
    """
    Async cancel workflow execution
    """
    exec_id = task.get("exec_id")
    worker_id = os.environ.get(ASYNC_WORKER_ID_KEY)
    if not worker_id:
        raise JiuWenBaseException(
            error_code=StatusCode.WORKFLOW_ASYNC_EXECUTION_WORKER_ID_ERROR.code,
            message=StatusCode.WORKFLOW_ASYNC_EXECUTION_WORKER_ID_ERROR.errmsg.format(
                reason="worker_id not found"
            ),
        )
    os.environ[f"{exec_id}_canceled"] = "true"
    logger.info(f"Successfully flagged task {exec_id} as canceled on {worker_id}!")
    return True
