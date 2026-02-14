#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
import json
import time
from typing import Any, Dict, Optional, List
from openjiuwen.core.common.logging import logger

# MySQL LONGTEXT 最大长度约为 4GB，但为了防止内存问题，设置一个合理的上限
# 这里设置为 10MB，应该足够存储大多数正常输出，同时避免数据库问题
MAX_OUTPUT_LENGTH = 10 * 1024 * 1024


def _truncate_data(data: Any, max_length: int = MAX_OUTPUT_LENGTH) -> str:
    """
    将数据转换为字符串并截断到指定长度
    
    Args:
        data: 任意数据
        max_length: 最大长度限制
        
    Returns:
        截断后的字符串
    """
    if data is None:
        return ""
    
    try:
        if isinstance(data, str):
            text = data
        else:
            text = json.dumps(data, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        text = str(data)
    
    if len(text) > max_length:
        truncation_warning = f"\n...[Content truncated: exceeded {max_length} characters]"
        text = text[:max_length - len(truncation_warning)] + truncation_warning
    
    return text
from openjiuwen.core.session.stream import TraceSchema, OutputSchema
from openjiuwen.core.session.tracer.span import TraceAgentSpan, TraceWorkflowSpan
from openjiuwen.core.session.interaction.interaction import InteractionOutput
from openjiuwen_studio.core.manager.repositories.workflow_execution_repository import workflow_execution_repository
from openjiuwen_studio.core.manager.repositories.agent_execution_repository import agent_execution_repository
from openjiuwen_studio.core.manager.repositories.trace_detail_repository import trace_detail_repository

from openjiuwen_studio.core.common.message import (
    TraceResponse, ExecuteStatus, ExecuteResponseType,
    InteractionResponse, ExecuteResponse
)
from openjiuwen_studio.schemas.agent import AgentId
from openjiuwen_studio.schemas.workflow import WorkflowId
from openjiuwen_studio.schemas.trace_detail import TraceDetail

# Define constant locally to avoid circular import
EMPTY_NODE_ID_PREFIX = 'empty_node_'


def _workflowspan_2_tracedetail(business_type: str, workflowspan: TraceWorkflowSpan, mapping: Optional[Dict[str, str]] = None) -> TraceDetail:
    # 使用mapping获取span_name，如果不存在则使用原component_name
    span_name = workflowspan.component_name
    if mapping and workflowspan.invoke_id in mapping:
        span_name = mapping[workflowspan.invoke_id]
    
    return TraceDetail(
        space_id="",
        business_id="",  # 填入agent/workflow名字
        business_type=business_type,
        trace_id=workflowspan.trace_id,
        span_id=workflowspan.invoke_id,
        span_type=workflowspan.component_type,
        span_name=span_name,
        parent_span_id=workflowspan.parent_invoke_id,
        method="",
        psm="",
        logid="",
        platform_type="studio_workflow" if business_type == "WORKFLOW" else "studio_agent_workflow",
        start_time_micros=int(time.mktime(workflowspan.start_time.timetuple()) * 1e6 +
                              workflowspan.start_time.microsecond) if workflowspan.start_time else None,
        end_time_micros=int(time.mktime(workflowspan.end_time.timetuple()) * 1e6 +
                            workflowspan.end_time.microsecond) if workflowspan.end_time else None,
        status_code=workflowspan.status,
        input=_truncate_data(workflowspan.inputs),
        output=_truncate_data(workflowspan.outputs),
        attributes=None
    )



def _agentspan_2_tracedetail(business_type: str, agentspan: TraceAgentSpan, mapping: Optional[Dict[str, str]] = None) -> TraceDetail:
    # 使用mapping获取span_name，如果不存在则使用原name
    span_name = agentspan.name
    if mapping and agentspan.invoke_type in mapping:
        span_name = mapping[agentspan.invoke_type]
    
    return TraceDetail(
        space_id="",
        business_id="",  # 填入agent/workflow名字
        business_type=business_type,
        trace_id=agentspan.trace_id,
        span_id=agentspan.invoke_id,
        span_type=agentspan.invoke_type,
        span_name=span_name,
        parent_span_id=agentspan.parent_invoke_id,
        method="",
        psm="",
        logid="",
        platform_type="studio_agent",
        start_time_micros=int(time.mktime(agentspan.start_time.timetuple()) * 1e6 +
                              agentspan.start_time.microsecond) if agentspan.start_time else None,
        end_time_micros=int(time.mktime(agentspan.end_time.timetuple()) * 1e6 +
                            agentspan.end_time.microsecond) if agentspan.end_time else None,
        status_code="error" if agentspan.error else ("finish" if agentspan.end_time else "start"),
        input=_truncate_data(agentspan.inputs),
        output=_truncate_data(agentspan.outputs),
        attributes=None
    )


def get_trace_workflow_output(data):
    """
        获取trace_workflow中streamOutputs或outputs
    """
    outputs_value = None
    if data.outputs:
        outputs_value = data.outputs
    elif data.stream_outputs:
        # 从 stream_outputs 中提取并拼接所有文本值
        text_parts = []
        output_key = "output"

        for item in data.stream_outputs:
            # 第一种格式: {'output': 'value'}
            if isinstance(item, dict) and 'output' in item:
                text_parts.append(str(item['output']))

            # 第二种格式: {'type': 'end node stream', 'index': 0, 'payload': {'response': 'value'}}
            # 第三种格式: {'type': 'output', 'index': 0, 'payload': {'output': '111', 'result_type': 'answer'}}
            elif isinstance(item, dict) and 'payload' in item:
                payload = item.get('payload', {})
                if isinstance(payload, dict):
                    # 检查 payload 中是否有 response 字段
                    if 'response' in payload:
                        text_parts.append(str(payload['response']))
                        output_key = "response"
                    if 'output' in payload:
                        text_parts.append(str(payload['output']))
                        output_key = "response"

        if text_parts:
            combined_text = ''.join(text_parts)
            outputs_value = {output_key: combined_text}

    return outputs_value


def get_trace_workflow_input(data):
    """
    获取trace_workflow中streamInputs或inputs
    """
    inputs_value = {}

    # 首先处理inputs
    if data.inputs:
        inputs_value.update(data.inputs)

    # 处理stream_inputs，按不同的输出键合并
    if hasattr(data, 'stream_inputs') and data.stream_inputs:
        # 用于存储每个output键对应的值
        stream_values = {}

        for item in data.stream_inputs:
            if isinstance(item, dict):
                # 提取键值对，item可能是 {'output2': '从前'} 或类似格式
                for key, value in item.items():
                    if key not in stream_values:
                        stream_values[key] = []
                    stream_values[key].append(str(value))

        # 将每个output键的值合并成字符串
        for key, value_list in stream_values.items():
            combined_text = ''.join(value_list)
            inputs_value[key] = combined_text

    if not inputs_value:
        inputs_value=None

    return inputs_value


def result_convert(chunk: Any, business_type: str, mapping: Optional[Dict[str, str]] = None) -> tuple[None, None] | tuple[Any, TraceWorkflowSpan, TraceDetail] | \
                                                      tuple[Any, TraceAgentSpan, TraceDetail] | tuple[Any, None, None] | \
                                                      tuple[Any, None]:
    """
    将底层执行器返回的 chunk 转换为对外 API 响应格式。
    返回 (response_dict, trace_data_or_none)
    """
    # Workflow Trace
    if isinstance(chunk, TraceSchema) and chunk.type == "tracer_workflow":
        logger.debug(f"get chunk.type == tracer_workflow, chunk: {chunk}")
        data = TraceWorkflowSpan.model_validate(chunk.payload)
        if EMPTY_NODE_ID_PREFIX in data.invoke_id:
            return None, None, None

        input_value = get_trace_workflow_input(data)
        output_value = get_trace_workflow_output(data)
        data.inputs = input_value
        data.outputs = output_value

        # 使用component_name_map映射组件名称
        component_name = data.component_name
        if mapping and data.invoke_id in mapping:
            component_name = mapping[data.invoke_id]
        
        # 将映射后的组件名称设置回data中，确保trace log使用正确的名称
        data.component_name = component_name

        return ExecuteResponse(
            type=ExecuteResponseType.Trace,
            payload=TraceResponse(
                id=data.invoke_id,
                name=component_name,
                version="",
                description="",

                status=ExecuteStatus.Start if data.status == "start" else ExecuteStatus.Finish,

                inputs=input_value,
                outputs=output_value,
                output_text="",
                error=data.error,

                start_time=data.start_time,
                end_time=data.end_time,

                parent_id=data.loop_node_id if data.loop_node_id else data.parent_invoke_id,
                loop_index=data.loop_index,
            ).model_dump()
        ).model_dump(), data, _workflowspan_2_tracedetail(business_type, data, mapping)

    # Agent Trace
    if isinstance(chunk, TraceSchema) and chunk.type == "tracer_agent":
        data = TraceAgentSpan.model_validate(chunk.payload)

        # 处理流式输出，合并outputs列表中的多个条目
        if hasattr(data, 'outputs') and data.outputs is not None:
            # 检查outputs是否为字典且包含outputs列表
            if isinstance(data.outputs, dict) and 'outputs' in data.outputs:

                outputs_list = data.outputs['outputs']
                # 如果outputs列表有多个条目，进行合并
                if outputs_list and isinstance(outputs_list, list) and len(outputs_list) > 1:
                    # 收集所有content内容
                    merged_content = ""
                    for item in outputs_list:
                        if isinstance(item, dict) and 'content' in item:
                            merged_content += str(item['content'])
                    # 创建合并后的条目，保留第一个条目的其他字段
                    if merged_content and outputs_list:
                        # 复制第一个条目并更新content
                        merged_item = outputs_list[0].copy()
                        merged_item['content'] = merged_content
                        # 替换outputs列表为仅包含合并条目的列表
                        data.outputs['outputs'] = [merged_item]

        return ExecuteResponse(
            type=ExecuteResponseType.Trace,
            payload=TraceResponse(
                id=data.invoke_id,
                name="",
                version="",
                description="",

                status=ExecuteStatus.Agent,

                inputs=data.inputs,
                outputs=data.outputs,
                output_text="",
                error=data.error,

                start_time=data.start_time,
                end_time=data.end_time,

                parent_id=data.parent_invoke_id,
                loop_index=None,
            ).model_dump()
        ).model_dump(), data, _agentspan_2_tracedetail(business_type, data, mapping)

    # Final Answer
    if isinstance(chunk, OutputSchema) and chunk.type == "answer":
        return None, None, None

    # Streaming output
    if isinstance(chunk, OutputSchema) and chunk.type == "output":
        if mapping:
            logger.debug(f"get node name and node id mapping: {mapping}")
            for nid in mapping:
                if chunk.payload.get("node_id") == nid:
                    chunk.payload["node_name"] = mapping.get(nid)
        logger.debug(f"chunk.type == output return chunk.payload: {chunk.payload}")
        return ExecuteResponse(type=ExecuteResponseType.Workflow, payload=chunk.payload).model_dump(), None, None

    # Streaming output
    if isinstance(chunk, OutputSchema) and chunk.type == "end node stream":
        # 将原有payload={"response": "你好"} 转换成 payload={"output": "你好", "result_type": "answer"}格式
        if isinstance(chunk.payload, dict) and "response" in chunk.payload:
            answer_value = chunk.payload.get("response", "")
            # 确保answer是字符串类型，如果不是则序列化为JSON字符串
            if not isinstance(answer_value, str):
                try:
                    answer_value = json.dumps(answer_value, ensure_ascii=False)
                except (TypeError, ValueError):
                    answer_value = str(answer_value)

            transformed_payload = {
                "output": answer_value,
                "result_type": "answer",
                "node_id": "end_0",
                "node_name": "结束",
                "index": chunk.index
            }
        elif isinstance(chunk.payload, dict) and "output" in chunk.payload:
            output_value = chunk.payload.get("output", {})
            if isinstance(output_value, dict):
                # 使用list()将values转换为列表，然后取第一个
                if output_value:  # 确保字典不为空
                    output_value = next(iter(output_value.values()))
                else:
                    output_value = ""
            else:
                output_value = json.dumps(output_value, ensure_ascii=False)

            transformed_payload = {
                "output": output_value,
                "result_type": "answer",
                "node_id": "end_0",
                "node_name": "结束",
                "index": chunk.index
            }
        else:
            transformed_payload = chunk.payload
            if isinstance(transformed_payload, dict):
                transformed_payload["index"] = chunk.index

        response_type = ExecuteResponseType.Workflow
        if business_type == "AGENT":
            response_type = ExecuteResponseType.Agent

        return ExecuteResponse(type=response_type, payload=transformed_payload).model_dump(), None, None

    # Agent workflow run result
    # not processing workflow_final type
    if isinstance(chunk, OutputSchema) and chunk.type == "workflow_final":
        if business_type == "AGENT":
            answer_value = None
            # 处理 output 情况
            if chunk.payload.get("output"):
                output_data = chunk.payload.get("output")
                # 如果 output 是字典，转换为 key: value 格式的字符串
                if isinstance(output_data, dict):
                    formatted_items = []
                    for key, value in output_data.items():
                        if not isinstance(value, str):
                            value = str(value)
                        formatted_items.append(f"{key}: {value}")
                    answer_value = "\n".join(formatted_items)
                else:
                    answer_value = str(output_data)
            # 处理 response 情况
            elif chunk.payload.get("response"):
                response_data = chunk.payload.get("response")
                if isinstance(response_data, dict):
                    formatted_items = []
                    for key, value in response_data.items():
                        if not isinstance(value, str):
                            value = str(value)
                        formatted_items.append(f"{key}: {value}")
                    answer_value = "\n".join(formatted_items)
                else:
                    answer_value = str(response_data)

            if answer_value:
                agent_payload = {"output": answer_value, "result_type": "answer"}
                return ExecuteResponse(type=ExecuteResponseType.Agent, payload=agent_payload).model_dump(), None, None
        return None, None, None

    # Agent Token 粒度输出处理
    if isinstance(chunk, OutputSchema) and chunk.type == "llm_output":
        return ExecuteResponse(type=ExecuteResponseType.Agent, payload=chunk.payload).model_dump(), None, None

    # Interaction
    if (
            isinstance(chunk, OutputSchema)
            and chunk.type == "__interaction__"
            and isinstance(chunk.payload, InteractionOutput)
    ):
        payload = InteractionResponse(
            interaction_node=chunk.payload.id,
            interaction_msg=chunk.payload.value,
        )
        return ExecuteResponse(type=ExecuteResponseType.Interaction,
                               payload=payload.model_dump()).model_dump(), None, None

    logger.debug(f"not convert chunk: {chunk}")
    return None, None, None


async def save_trace_details(index: WorkflowId | AgentId, tracedetails: List[TraceDetail]) -> None:
    """
    批量保存trace details，优化性能
    
    Args:
        index: WorkflowId或AgentId
        tracedetails: TraceDetail列表
    """
    if not tracedetails:
        return
    
    # 设置space_id和business_id
    for tracedetail in tracedetails:
        tracedetail.space_id = index.space_id
        if tracedetail.business_type == "WORKFLOW":
            tracedetail.business_id = index.workflow_id
        else:
            tracedetail.business_id = index.agent_id
    
    # 使用批量保存
    trace_detail_repository.create_trace_details(tracedetails)


# 保存执行日志
async def save_execution_traces(
        index: WorkflowId | AgentId,
        trace_logs: list[TraceWorkflowSpan | TraceAgentSpan],
) -> None:
    """
    统一保存一次执行的所有 trace
    """
    try:
        if isinstance(index, WorkflowId):
            # 目前workflow_execution_repository使用trace_id作为索引，后续看时候要改成conversation_id
            workflow_execution_repository.create_workflow_execution_log(index, trace_logs)
        elif isinstance(index, AgentId):
            agent_execution_repository.create_agent_execution_log(index, trace_logs)
    except Exception as e:
        logger.error(f"Failed to save execution traces for {index}: {e}", exc_info=True)


# 处理错误
async def handle_stream_error(
        trace_logs: list[TraceWorkflowSpan | TraceAgentSpan],
        trace_details: list[TraceDetail],
        last_chunk: Any,
        error_code: int,
        error_msg: str,
        index: WorkflowId | AgentId
) -> Optional[str]:
    business_type = "WORKFLOW" if isinstance(index, WorkflowId) else "AGENT"
    trace_id: Optional[str] = None
    if last_chunk is not None and hasattr(last_chunk, "payload"):
        _, trace_data, trace_detail = result_convert(last_chunk, business_type)
        if trace_details and trace_detail is not None:
            if error_code == -2:
                trace_detail.output = f"Agent execution interrupted: {error_msg}"
                trace_detail.status_code = 'interrupted'
            else:
                trace_detail.output = f"Agent execution error: {error_msg}"
                trace_detail.status_code = 'error'
            trace_details.append(trace_detail)
            trace_id = trace_detail.trace_id
        if trace_logs and trace_data is not None:
            if hasattr(trace_data, 'error') and hasattr(trace_data, 'status'):
                trace_data.status = "error"
                trace_data.error = {str(error_code): error_msg}
                trace_logs.append(trace_data)

    # 批量保存错误追踪详情
    if trace_details:
        try:
            await save_trace_details(index, trace_details)
        except Exception as e:
            logger.error(f"Failed to save trace details batch: {e}")

    if not trace_logs:
        logger.error(f"Workflow/Agent failed before any trace was emitted: {error_msg}")
    else:
        await save_execution_traces(index, trace_logs)
    return trace_id
