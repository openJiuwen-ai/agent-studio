#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
import json
import uuid
from typing import Dict, Any, Callable

from fastapi import status, HTTPException
from openjiuwen.core.common.logging import logger
from pydantic import ValidationError

from openjiuwen_studio.core.manager.login_manager.space import check_user_space
from openjiuwen_studio.core.utils.exception import log_exception
from openjiuwen_studio.schemas.workflow import WorkflowId
from openjiuwen_studio.schemas.agent import AgentId
from openjiuwen_studio.schemas.common import ResponseModel
from openjiuwen_studio.core.manager.repositories.workflow_repository import workflow_repository
from openjiuwen_studio.core.common.dsl import ComponentType
from openjiuwen_studio.core.manager.workflow_tag import create_workflow_tags, get_workflow_tags, update_workflow_tags
from openjiuwen_studio.core.database import milliseconds
from openjiuwen_studio.schemas.execution_log import WfExecutionLogsFilter, WfExecutionLogIndex, \
    ExecutionTraceChunkType, ApiExecutionLogGet, ApiExecutionLogsDebugEnter, ExecutionLogsCreateList, \
    ExecutionLogDebug, AgExecutionLogsFilter, AgExecutionLogIndex
from openjiuwen_studio.core.manager.repositories.workflow_execution_repository import workflow_execution_repository
from openjiuwen_studio.core.manager.repositories.agent_execution_repository import agent_execution_repository
from openjiuwen.core.session.stream import TraceSchema
from openjiuwen_studio.core.executor.util.utils import result_convert as executor_result_convert
from openjiuwen.core.session.tracer.span import TraceWorkflowSpan, TraceAgentSpan


def with_exception_handling(func: Callable) -> Callable:
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValidationError as e:
            log_exception(e)
            return ResponseModel(
                code=status.HTTP_400_BAD_REQUEST,
                message=str(e)
            )
        except Exception as e:
            log_exception(e)
            return ResponseModel(
                code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=str(e)
            )

    return wrapper


@with_exception_handling
def get_workflow_execution_logs_create_list(
        req: WfExecutionLogsFilter,
        current_user: dict
) -> ResponseModel[ExecutionLogsCreateList]:
    """获取workflow的所有执行日志的创建信息list"""
    _ = check_user_space(req.space_id, current_user)
    db_res: ResponseModel[ExecutionLogDebug] = workflow_execution_repository.get_execution_logs_create_list(req)
    if db_res.code != status.HTTP_200_OK:
        return db_res
    db_res.data = ExecutionLogsCreateList(logs_create_list=db_res.data.logs_create_list)
    return db_res


def trans_trace_workflow_span_list_2_execute_response_list(
    log_details: list[TraceWorkflowSpan],
    trace_schema_type: str = ExecutionTraceChunkType.workflow_tracer
):
    """将[TraceWorkflowSpan]数据转换成[ExecuteResponse]数据, 回传前端用于展示 """
    execute_response_list = []
    for log_detail in log_details:
        trace_schema = TraceSchema(type=trace_schema_type,
                                   payload=log_detail)
        execute_response, _, _ = executor_result_convert(trace_schema, "")
        execute_response_list.append(execute_response)
    return execute_response_list


@with_exception_handling
def get_workflow_execution_log(
        req: WfExecutionLogIndex,
        current_user: dict
) -> ResponseModel[ApiExecutionLogGet]:
    """获取workflow的某次执行日志"""
    _ = check_user_space(req.space_id, current_user)
    # 数据库获取该次执行日志数据
    db_res: ResponseModel[ExecutionLogDebug] = workflow_execution_repository.get_execution_log(req)
    if db_res.code != status.HTTP_200_OK:
        return db_res

    # 将类型转换成前端可展示的类型
    db_res_data: ExecutionLogDebug = db_res.data

    db_res.data = ApiExecutionLogGet(logSummary=db_res_data.log_summary,
                        logDetails=trans_trace_workflow_span_list_2_execute_response_list(db_res_data.log_details))
    return db_res


@with_exception_handling
def enter_workflow_execution_logs_debug(
        req: WorkflowId,
        current_user: dict
) -> ResponseModel[ApiExecutionLogsDebugEnter]:
    """点击调试按钮，获取workflow的所有运行log的create list及最新运行日志"""
    _ = check_user_space(req.space_id, current_user)
    # 数据库获取该次执行日志数据
    db_res: ResponseModel[ExecutionLogDebug] = workflow_execution_repository.enter_execution_logs_debug(req)
    if db_res.code != status.HTTP_200_OK:
        return db_res

    # 将类型转换成前端可展示的类型
    db_res_data: ExecutionLogDebug = db_res.data
    db_res.data = ApiExecutionLogsDebugEnter(logSummary=db_res_data.log_summary,
                        logDetails=trans_trace_workflow_span_list_2_execute_response_list(db_res_data.log_details),
                        logs_create_list=db_res_data.logs_create_list)
    return db_res


@with_exception_handling
def get_agent_execution_logs_create_list(
        req: AgExecutionLogsFilter,
        current_user: dict
) -> ResponseModel[ExecutionLogsCreateList]:
    """获取agent的所有执行日志的创建信息list"""
    _ = check_user_space(req.space_id, current_user)
    db_res: ResponseModel[ExecutionLogDebug] = agent_execution_repository.get_execution_logs_create_list(req)
    if db_res.code != status.HTTP_200_OK:
        return db_res
    db_res.data = ExecutionLogsCreateList(logs_create_list=db_res.data.logs_create_list)
    return db_res


@with_exception_handling
def get_agent_execution_log(
        req: AgExecutionLogIndex,
        current_user: dict
) -> ResponseModel[ApiExecutionLogGet]:
    """获取agent的某次执行日志"""
    _ = check_user_space(req.space_id, current_user)
    # 数据库获取该次执行日志数据
    db_res: ResponseModel[ExecutionLogDebug] = agent_execution_repository.get_execution_log(req)
    if db_res.code != status.HTTP_200_OK:
        return db_res

    # 将类型转换成前端可展示的类型
    db_res.data = ApiExecutionLogGet(logSummary=db_res.data.log_summary)
    return db_res


@with_exception_handling
def enter_agent_execution_logs_debug(
        req: AgentId,
        current_user: dict
) -> ResponseModel[ApiExecutionLogsDebugEnter]:
    """点击调试按钮，获取agent的所有运行log的create list及最新运行日志"""
    _ = check_user_space(req.space_id, current_user)
    # 数据库获取该次执行日志数据
    db_res: ResponseModel[ExecutionLogDebug] = agent_execution_repository.enter_execution_logs_debug(req)
    if db_res.code != status.HTTP_200_OK:
        return db_res

    # 将类型转换成前端可展示的类型
    db_res.data = ApiExecutionLogsDebugEnter(logSummary=db_res.data.log_summary,
                        logs_create_list=db_res.data.logs_create_list)
    return db_res
