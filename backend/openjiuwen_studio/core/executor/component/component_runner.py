#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

from typing import Any, Dict, Optional
import asyncio
from openjiuwen_studio.core.executor.component.component_execution_manager import (
    component_execution_manager, ComponentExecutionRegistration
)
from openjiuwen_studio.core.executor.workflow.context import Context
from openjiuwen_studio.core.executor.workflow.workflow import Workflow
from openjiuwen_studio.core.executor.workflow.workflow_runner import _fetch_workflow_dl, WorkflowRunner
from openjiuwen_studio.core.common.dsl import ComponentType
from openjiuwen_studio.core.common.status_code import StatusCode
from openjiuwen_studio.core.common.dsl import LoopConfig

# 修改：从新路径导入
from openjiuwen.core.session.internal.workflow import WorkflowSession, NodeSession
from openjiuwen.core.session.stream.emitter import StreamEmitter
from openjiuwen.core.session.stream.manager import StreamWriterManager
from openjiuwen.core.workflow.components import Session
from openjiuwen.core.workflow import WorkflowCard

from openjiuwen.core.graph.base import INPUTS_KEY
from openjiuwen_studio.core.common.exceptions import BaseError
from openjiuwen.core.workflow.workflow_config import WorkflowConfig
from openjiuwen_studio.core.executor.workflow.pregel_graph_adapter import JiuWenGraphException
from openjiuwen_studio.core.executor.util.utils import result_convert, handle_stream_error
from openjiuwen.core.session.tracer.span import TraceWorkflowSpan
from openjiuwen_studio.schemas import WorkflowId
from openjiuwen.core.common.logging import logger
from openjiuwen_studio.core.common.exceptions import JiuWenComponentException
from openjiuwen_studio.core.common.message import ExecuteResponseType, ExecuteResponse

CAN_SINGLE_COMP_RUN = [ComponentType.COMPONENT_TYPE_LLM, ComponentType.COMPONENT_TYPE_LOOP,
                       ComponentType.COMPONENT_TYPE_PLUGIN, ComponentType.COMPONENT_TYPE_TEXT_EDITOR,
                       ComponentType.COMPONENT_TYPE_CODE, ComponentType.COMPONENT_TYPE_INTENT,
                       ComponentType.COMPONENT_TYPE_QUESTION, ComponentType.COMPONENT_TYPE_SUB_WORKFLOW]


class ComponentExecutor(WorkflowRunner):
    def __init__(self) -> None:
        super().__init__()
        pass

    async def run(
            self,
            workflow_id: str,
            workflow_version: str,
            inputs: Any,
            component_id: str,
            space_id: str,
            current_user: Dict[str, Any],
            loop_id: Optional[str] = None,
            conversation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        # 生成 execution_id
        execution_id = f"{workflow_id}:{component_id}:{conversation_id}"
        # 单组件调试时跳过工作流全局校验，只关注被调试组件
        workflow = Workflow(
            await _fetch_workflow_dl(workflow_id, workflow_version, space_id, current_user, skip_validation=True),
            space_id,
            current_user)
        workflow_session = WorkflowSession(workflow_id=workflow_id, session_id=execution_id)
        workflow_session.config().add_workflow_config(workflow_id, WorkflowConfig(
            card=WorkflowCard(id=workflow_id, version=workflow_version, input_params=inputs)))

        workflow_session.set_stream_writer_manager(StreamWriterManager(stream_emitter=StreamEmitter()))
        node_session = NodeSession(workflow_session, component_id)
        session = Session(node_session, stream_mode=False)
        context = None

        if loop_id:
            try:
                target_loop = next(wf_comp for wf_comp in workflow.dl_workflow.components if wf_comp.id == loop_id)
            except StopIteration as exc:
                raise ValueError(f"Loop Component with id '{loop_id}' not found in workflow {workflow_id}") from exc
            loop_config = LoopConfig.model_validate(target_loop.configs)
            component_list = loop_config.loop_body.components
        else:
            component_list = workflow.dl_workflow.components

        try:
            target_comp = next(comp for comp in component_list if comp.id == component_id)
        except StopIteration as exc:
            raise ValueError(f"Component with id '{component_id}' not found in workflow {workflow_id}") from exc

        if target_comp.type not in CAN_SINGLE_COMP_RUN:
            raise BaseError(
                code=StatusCode.COMPONENT_UNSUPPORT_RUN_ERROR.code,
                message=StatusCode.COMPONENT_UNSUPPORT_RUN_ERROR.errmsg
            )

        def _type_cn(t: int) -> str:
            m = {
                ComponentType.COMPONENT_TYPE_START: "开始",
                ComponentType.COMPONENT_TYPE_LLM: "大模型",
                ComponentType.COMPONENT_TYPE_END: "结束",
                ComponentType.COMPONENT_TYPE_IF: "选择器",
                ComponentType.COMPONENT_TYPE_LOOP: "循环",
                ComponentType.COMPONENT_TYPE_INPUT: "输入",
                ComponentType.COMPONENT_TYPE_OUTPUT: "输出",
                ComponentType.COMPONENT_TYPE_QUESTION: "提问器",
                ComponentType.COMPONENT_TYPE_CONTINUE: "继续",
                ComponentType.COMPONENT_TYPE_BREAK: "中断",
                ComponentType.COMPONENT_TYPE_TEXT_EDITOR: "文本编辑",
                ComponentType.COMPONENT_TYPE_INTENT: "意图识别",
                ComponentType.COMPONENT_TYPE_SUB_WORKFLOW: "子工作流",
                ComponentType.COMPONENT_TYPE_EMPTY_START: "空开始",
                ComponentType.COMPONENT_TYPE_EMPTY_END: "空结束",
                ComponentType.COMPONENT_TYPE_CODE: "代码",
                ComponentType.COMPONENT_TYPE_VARIABLE_MERGE: "变量聚合",
                ComponentType.COMPONENT_TYPE_SET_VARIABLE: "设置变量",
                ComponentType.COMPONENT_TYPE_PLUGIN: "插件",
            }
            return m.get(t, str(t))

        def _compile_err_code(t: int) -> int:
            return (
                StatusCode.LLM_COMPONENT_COMPILE_ERROR.code
                if t == ComponentType.COMPONENT_TYPE_LLM
                else StatusCode.COMPONENT_COMPILE_ERROR.code
            )

        def _run_err_code(t: int) -> int:
            return (
                StatusCode.LLM_COMPONENT_RUN_ERROR.code
                if t == ComponentType.COMPONENT_TYPE_LLM
                else StatusCode.COMPONENT_RUN_ERROR.code
            )

        try:
            if target_comp.type == ComponentType.COMPONENT_TYPE_SUB_WORKFLOW:
                compiled_comp = await workflow.compile_component(Context(), workflow.dl_workflow, target_comp, self)
                inputs = {INPUTS_KEY: inputs}
            elif target_comp.type == ComponentType.COMPONENT_TYPE_LOOP:
                compiled_comp = await workflow.compile_component(Context(), workflow.dl_workflow, target_comp)
                inputs = {INPUTS_KEY: inputs}
            else:
                compiled_comp = await workflow.compile_component(Context(), workflow.dl_workflow, target_comp)
        except BaseError as be:
            code = _compile_err_code(int(target_comp.type))
            msg = f"{_type_cn(int(target_comp.type))}组件[{component_id}]: {be.message}"
            raise JiuWenComponentException(
                code, msg, component_id, int(target_comp.type), error_stage="compile"
            ) from be
        except Exception as e:
            code = _compile_err_code(int(target_comp.type))
            msg = f"{_type_cn(int(target_comp.type))}组件[{component_id}]: {str(e)}"
            raise JiuWenComponentException(
                code, msg, component_id, int(target_comp.type), error_stage="compile"
            ) from e
        executor = compiled_comp.to_executable()
        trace_logs: list[TraceWorkflowSpan] = []
        data = None
        flow_index = WorkflowId(
            space_id=space_id,
            workflow_id=workflow_id,
            workflow_version="",
        )
        # 注册执行
        task = asyncio.current_task()
        registration = ComponentExecutionRegistration(
            execution_id=execution_id,
            session=session,
            task=task
        )
        component_execution_manager.register_execution(registration)

        try:
            # 执行前检查取消
            if component_execution_manager.is_cancelled(execution_id):
                raise asyncio.CancelledError()
            data = await executor.invoke(inputs, session, context)
            rsp, trace_log, trace_detail = result_convert(data, business_type="WORKFLOW")
            if trace_log:
                trace_logs.append(trace_log)
            return self.result_convert(data)
        except asyncio.CancelledError:
            logger.warning(f"component run cancelled by user: {execution_id}")
            pass
        except (BaseError, JiuWenGraphException) as e:
            logger.error(f"component run got JiuWen error: {e}")
            code = _run_err_code(int(target_comp.type))
            msg = f"{_type_cn(int(target_comp.type))}组件[{component_id}]: {getattr(e, 'message', str(e))}"
            await handle_stream_error(trace_logs, [], data, code, msg, flow_index)
            raise JiuWenComponentException(code, msg, component_id, int(target_comp.type), error_stage="execute") from e
        except Exception as e:
            logger.error(f"component run got Exception error: {e}")
            code = _run_err_code(int(target_comp.type))
            msg = f"{_type_cn(int(target_comp.type))}组件[{component_id}]: {str(e)}"
            await handle_stream_error(trace_logs, [], data, code, msg, flow_index)
            raise JiuWenComponentException(code, msg, component_id, int(target_comp.type), error_stage="execute") from e
        finally:
            component_execution_manager.unregister_execution(execution_id)

    def result_convert(self, data: Any) -> Dict[str, Any]:
        return ExecuteResponse(
            type=ExecuteResponseType.Node,
            payload={
                "output": data,
            }
        ).model_dump()


comp_executor = ComponentExecutor()
