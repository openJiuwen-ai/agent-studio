#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

import asyncio
import json
from typing import Any, Dict, AsyncGenerator, Optional
from builtins import id as builtinid

from fastapi import status
from openjiuwen_studio.core.common.exceptions import BaseError
from openjiuwen.core.common.logging import logger
from openjiuwen.core.workflow.workflow import Workflow as InvokableWorkflow
from openjiuwen.core.session.tracer.span import TraceWorkflowSpan
from openjiuwen.core.session.stream import TraceSchema
from openjiuwen.core.workflow import Session, create_workflow_session
from openjiuwen.core.session.internal.workflow import WorkflowSession
from openjiuwen.core.runner import Runner
from openjiuwen.core.context_engine import ModelContext, ContextEngine, ContextEngineConfig

import openjiuwen_studio.core.manager.workflow as mgr
from openjiuwen_studio.core.executor.workflow.context import Context
from openjiuwen_studio.core.common.status_code import StatusCode
from openjiuwen_studio.core.executor.workflow.pregel_graph_adapter import JiuWenGraphException
from openjiuwen_studio.core.executor.workflow.workflow import Workflow, IWorkflowLoader
from openjiuwen_studio.core.executor.util.utils import result_convert, save_execution_traces, handle_stream_error
from openjiuwen_studio.schemas import WorkflowId
from openjiuwen_studio.core.common.exceptions import JiuWenComponentException, JiuWenExecuteException
from openjiuwen_studio.core.manager.repositories.workflow_repository import workflow_repository
from openjiuwen_studio.core.executor.workflow.workflow_execution_manager import workflow_execution_manager, \
    WorkflowExecutionRegistration


def extract_component_names(schema_part, name_map, parent_path="", parent_component_ids=None):
    """递归提取所有组件名称，包括嵌套结构和层级关系"""
    if parent_component_ids is None:
        parent_component_ids = []

    if isinstance(schema_part, dict):
        # 1. 提取当前节点的组件信息（包括子工作流节点本身）
        if 'id' in schema_part and 'data' in schema_part and 'title' in schema_part['data']:
            component_id = schema_part['id']
            component_title = schema_part['data']['title']

            # 添加基础ID映射（如workflow_cLjMT -> AI天气查询）
            name_map[component_id] = component_title

            # 生成并添加完整的层级组件ID映射（如workflow_cLjMT.workflow_fV0Wb -> 子工作流标题）
            if parent_component_ids:
                full_component_id = f"{'.'.join(parent_component_ids)}.{component_id}"
                name_map[full_component_id] = component_title

        # 2. 处理完整的工作流schema（包含nodes和edges）
        if 'nodes' in schema_part and isinstance(schema_part['nodes'], list):
            # 遍历所有节点
            for node in schema_part['nodes']:
                if isinstance(node, dict) and 'id' in node:
                    if 'data' in node and 'title' in node['data']:
                        node_id = node['id']
                        node_title = node['data']['title']

                        # 添加基础ID映射（如code_MsmmT -> 代码）
                        name_map[node_id] = node_title

                        # 生成并添加完整的层级组件ID映射
                        # （如workflow_cLjMT.workflow_fV0Wb.code_MsmmT -> 代码）
                        if parent_component_ids:
                            full_node_id = f"{'.'.join(parent_component_ids)}.{node_id}"
                            name_map[full_node_id] = node_title

        # 特殊处理子工作流组件
        if (
                'type' in schema_part
                and (schema_part['type'] == '14'
                     or 'subWorkflow' in schema_part.get('data', {}).get('configs', {}))
        ):
            # 14 是ComponentType.COMPONENT_TYPE_SUB_WORKFLOW的值
            sub_wf_config = schema_part.get('data', {})

            # 获取当前子工作流节点ID
            current_component_id = schema_part.get('id', '')

            # 创建新的父组件ID列表，用于子工作流的节点
            new_parent_ids = parent_component_ids.copy()
            if current_component_id:
                new_parent_ids.append(current_component_id)

            # 方法1: 直接从workflow字段获取完整子工作流定义（已包含schema）
            sub_wf_full = sub_wf_config.get('workflow', {})
            sub_wf_schema_str = sub_wf_full.get('schema', '')

            if sub_wf_schema_str:
                # 直接使用已包含的schema，无需查询数据库
                try:
                    sub_wf_schema = json.loads(sub_wf_schema_str)
                    if sub_wf_schema:
                        # 递归提取子工作流的组件名称，传入更新后的父组件ID列表
                        extract_component_names(
                            sub_wf_schema,
                            name_map,
                            f"{parent_path}.sub_workflow.{current_component_id}",
                            new_parent_ids
                        )
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse embedded sub-workflow schema: {e}")

            # 方法2: 从configs.subWorkflow中获取子工作流信息（备用）
            sub_wf_info = sub_wf_config.get('configs', {}).get('subWorkflow', {})
            sub_wf_id = sub_wf_info.get('workflowId') or sub_wf_info.get('workflow_id') or sub_wf_info.get('id')
            sub_wf_version = sub_wf_info.get('workflowVersion') or sub_wf_info.get('version')

            if sub_wf_id and not sub_wf_schema_str:
                # 如果没有嵌入式schema，则查询数据库
                # 暂时跳过数据库查询，避免报错
                logger.error(f"Skipping database query for sub-workflow {sub_wf_id} because space_id is not available")

        # 特殊处理循环节点
        if 'type' in schema_part and schema_part['type'] == 'loop':
            # 循环节点处理
            current_component_id = schema_part.get('id', '')
            new_parent_ids = parent_component_ids.copy()
            if current_component_id:
                new_parent_ids.append(current_component_id)
        else:
            # 非循环节点，使用原有父组件ID列表
            new_parent_ids = parent_component_ids.copy()
            # 如果当前有ID且不是特殊节点类型，添加到父组件ID列表
            current_component_id = schema_part.get('id', '')
            if current_component_id and 'type' in schema_part and schema_part['type'] not in ['start', 'end']:
                new_parent_ids.append(current_component_id)

        # 特殊处理循环体、分支条件等嵌套结构
        nested_keys = ['loop_body', 'branches', 'branch_body', 'sub_workflow', 'components']
        for key, value in schema_part.items():
            new_path = f"{parent_path}.{key}" if parent_path else key
            # 递归处理所有嵌套结构，特别是已知的嵌套组件容器
            if key in nested_keys or isinstance(value, (dict, list)):
                extract_component_names(value, name_map, new_path, new_parent_ids)
    elif isinstance(schema_part, list):
        # 递归处理列表中的每个元素
        for idx, item in enumerate(schema_part):
            new_path = f"{parent_path}[{idx}]" if parent_path else f"[{idx}]"
            extract_component_names(item, name_map, new_path, parent_component_ids.copy())


async def _fetch_workflow_dl(
        workflow_id: str, version: str, space_id: str, current_user: Dict[str, Any], skip_validation: bool = False
) -> Any:
    req = {"workflow_id": workflow_id, "space_id": space_id, "version": version}
    res = mgr.workflow_convert(WorkflowId(**req), current_user, skip_validation=skip_validation)
    if res.code != status.HTTP_200_OK:
        if isinstance(res.data, dict) and "error_code" in res.data:
            if "component_id" in res.data and "component_type" in res.data:
                raise JiuWenComponentException(
                    code=res.data.get("error_code"),
                    message=str(res.message),
                    component_id=res.data.get("component_id"),
                    component_type=res.data.get("component_type"),
                    error_stage=res.data.get("error_stage") or "convert",
                )
            raise BaseError(
                code=res.data.get("error_code"),
                message=str(res.message),
            )
        raise BaseError(
            code=StatusCode.WORKFLOW_DL_FETCH_FAILED.code,
            message=StatusCode.WORKFLOW_DL_FETCH_FAILED.errmsg.format(msg=str(res.message)),
        )
    workflow_dl = res.data
    if workflow_dl is None:
        raise BaseError(
            code=StatusCode.WORKFLOW_DL_FETCH_FAILED.code,
            message=StatusCode.WORKFLOW_DL_FETCH_FAILED.errmsg.format(msg=str("fetch workflow failed"))
        )
    logger.info(f"fetch workflow dl: {workflow_dl.model_dump_json()}")
    return workflow_dl


class WorkflowRunner(IWorkflowLoader):
    def __init__(self) -> None:
        pass

    def generate_component_name_map(self, workflow_dl: Any) -> Optional[Dict[str, str]]:
        """
        从workflow的schema中提取组件id到name的映射
        """
        component_name_map = None
        try:
            # Handle both Pydantic model (with .schema attribute) and dict (with 'schema' key)
            workflow_schema_str = workflow_dl.schema if hasattr(workflow_dl, 'schema') else workflow_dl.get('schema')
            workflow_schema = json.loads(workflow_schema_str) if workflow_schema_str else {}

            if isinstance(workflow_schema, dict):
                component_name_map = {}
                extract_component_names(workflow_schema, component_name_map)
        except (json.JSONDecodeError, TypeError, KeyError, ImportError) as e:
            logger.warning(f"Failed to parse workflow schema for component names: {e}", exc_info=True)
        return component_name_map

    async def get_flow(
            self, id: str, version: str, space_id: str, current_user: Dict[str, Any]
    ) -> Workflow:
        flow = Workflow(await _fetch_workflow_dl(id, version, space_id, current_user), space_id, current_user)
        return flow

    async def get_compiled_workflow(
            self, context: Context,
            id: str, version: str, space_id: str, current_user: Dict[str, Any]
    ) -> InvokableWorkflow:
        workflow = await self.get_flow(id, version, space_id, current_user)
        compiled = await workflow.compile(context, self)
        return compiled

    async def run(
            self,
            id: str,
            version: str,
            inputs: Any,
            conversation_id: str,
            space_id: str,
            current_user: Dict[str, Any],
    ) -> AsyncGenerator[Any, None]:

        # 检查当前conversation_id是否处于执行状态
        if workflow_execution_manager.is_executing(conversation_id):
            all_execution_infos = workflow_execution_manager.list_executions()
            logger.info(f"Now existing workflow executions: {all_execution_infos}")
            logger.error(
                f"Workflow execution conflict detected: "
                f"conversation_id={conversation_id}, workflow_id={id}"
            )
            # 如果存在执行id, 可直接停止当前会话id
            cancel_success = await workflow_execution_manager.cancel_execution(conversation_id)
            if not cancel_success:
                raise JiuWenExecuteException(
                    code=StatusCode.WORKFLOW_EXECUTION_CONFLICT_ERROR.code,
                    message=StatusCode.WORKFLOW_EXECUTION_CONFLICT_ERROR.errmsg.format(msg=conversation_id),
                    workflow_id=id,
                )

        # 收集一次执行的所有 trace log
        trace_logs: list[TraceWorkflowSpan] = []
        flow_index = WorkflowId(
            space_id=space_id,
            workflow_id=id,
            workflow_version=version,
        )
        last_chunk = None  # 用于异常时回溯
        # trace_id = None  # 暂时保留 trace_id 用于 trace_summary 创建

        # 生成component_name_map
        component_name_map = None
        try:
            # 获取workflow的schema数据
            workflow_res = workflow_repository.workflow_get(flow_index)
            if workflow_res.code == 200 and workflow_res.data:
                workflow = workflow_res.data
                # 使用新的方法生成组件名称映射
                component_name_map = self.generate_component_name_map(workflow)
        except Exception as e:
            logger.error(f"Failed to generate component_name_map: {e}", exc_info=True)

        try:
            # 编译工作流
            flow = await self.get_compiled_workflow(Context(), id, version, space_id, current_user)
            # 创建 Session 用于 workflow 执行, session_id确保唯一性
            session = create_workflow_session(session_id=conversation_id)

            task = asyncio.current_task()
            logger.info(f"Workflow task_id: {builtinid(task)}")
            # 注册执行任务
            registration = WorkflowExecutionRegistration(
                conversation_id=conversation_id,
                workflow_id=id,
                workflow_version=version,
                space_id=space_id,
                session=session,
                task=task
            )
            workflow_execution_manager.register_execution(registration)
            # 使用 Runner.run_workflow_streaming() 执行工作流
            async for chunk in Runner.run_workflow_streaming(
                    workflow=flow,  # 传入已编译的 Workflow 实例
                    inputs=inputs,
                    session=session,
            ):
                # 检查任务是否被取消
                if task and task.cancelled():
                    logger.warning(f"Workflow execution has been cancelled: conversation_id={conversation_id}")
                    break
                # 检查执行管理器中的取消标志
                if workflow_execution_manager.is_cancelled(conversation_id):
                    logger.warning(
                        f"Workflow execution cancelled via execution manager: conversation_id={conversation_id}")
                    break

                # 检查是否为需要过滤的workflow trace chunk
                if isinstance(chunk, TraceSchema) and chunk.type == "tracer_workflow":
                    wf = TraceWorkflowSpan.model_validate(chunk.payload)
                    # 检查条件：有workflowId字段且invokeId == workflowId
                    if hasattr(wf, 'workflow_id') and wf.invoke_id == wf.workflow_id:
                        continue
                # logger.debug(f"get workflow stream chunk: {chunk}")
                last_chunk = chunk

                rsp, trace_log, _ = result_convert(chunk, business_type="WORKFLOW", mapping=component_name_map)
                # if trace_detail:
                #     await save_trace_detail(flow_index, trace_detail)
                #     if trace_id is None:
                #         trace_id = trace_detail.trace_id
                if trace_log:
                    trace_logs.append(trace_log)
                if rsp:
                    logger.debug(f"workflow stream return rsp: {rsp}")
                    yield rsp

            if trace_logs:
                await save_execution_traces(flow_index, trace_logs)
            # if trace_id is not None:
            #     trace_summary_repository.create_trace_summary_by_trace_id(trace_id)
        except asyncio.CancelledError:
            logger.warning(f"Workflow execution cancelled: conversation_id={conversation_id}")
            # task.cancel()
            # logger.warning(f"Workflow execution cancelled 1 : task.cancelled() {task.cancelled()} "
            #                f"taskid {builtinid(task)}")
            pass
        except JiuWenExecuteException as e:
            await handle_stream_error(trace_logs, [], last_chunk, e.code, e.message, flow_index)
            # if trace_id is not None:
            #     trace_summary_repository.create_trace_summary_by_trace_id(trace_id)
            e.set_workflow_id(id)
            raise e
        except (BaseError, JiuWenGraphException) as e:
            await handle_stream_error(trace_logs, [], last_chunk, e.code, e.message, flow_index)
            # if trace_id is not None:
            #     trace_summary_repository.create_trace_summary_by_trace_id(trace_id)
            raise JiuWenExecuteException(e.code, e.message, workflow_id=id) from e
        except Exception as e:
            await handle_stream_error(trace_logs, [], last_chunk, -1, str(e), flow_index)
            # if trace_id is not None:
            #     trace_summary_repository.create_trace_summary_by_trace_id(trace_id)
            raise JiuWenExecuteException(
                StatusCode.WORKFLOW_RUNNER_ERROR.code,
                StatusCode.WORKFLOW_RUNNER_ERROR.errmsg.format(msg=str(e)),
                workflow_id=id,
            ) from e
        finally:
            # 取消注册执行任务
            workflow_execution_manager.unregister_execution(conversation_id)

    async def validate(
            self,
            id: str,
            version: str,
            space_id: str,
            current_user: Dict[str, Any]
    ) -> bool:
        Workflow(await _fetch_workflow_dl(id, version, space_id, current_user), space_id, current_user)
        return True


flow_mgr = WorkflowRunner()
