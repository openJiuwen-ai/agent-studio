#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

"""
Agent Trace Utils - Agent通用追踪工具模块

本模块提供Agent执行过程中的追踪功能，包括：
1. 追踪上下文管理
2. Chunk级别的追踪信息处理
3. 追踪数据的保存和清理
4. 追踪错误的统一处理

核心功能：
- 统一管理Agent执行的追踪信息
- 提供可复用的追踪处理函数
- 支持不同Agent类型的追踪需求
"""

from dataclasses import dataclass, field
from typing import Any, Optional, List, Dict
from datetime import datetime
import uuid

from openjiuwen.core.session.tracer.span import TraceWorkflowSpan, TraceAgentSpan
from openjiuwen.core.session.stream.base import TraceSchema, OutputSchema
from openjiuwen.core.common.logging import logger


@dataclass
class KBRetrievalSpanParams:
    """知识库检索span的参数封装"""
    trace_id: str
    query: str
    kb_results: List[str]
    start_time: datetime
    end_time: datetime
    parent_invoke_id: Optional[str] = None

from openjiuwen_studio.core.executor.util.utils import (
    result_convert,
    handle_stream_error,
    save_trace_details,
)
from openjiuwen_studio.core.manager.repositories.trace_summary_repository import (
    trace_summary_repository,
)
from openjiuwen_studio.schemas.agent import AgentId
from openjiuwen_studio.schemas.trace_detail import TraceDetail


@dataclass
class TraceContext:
    """
    追踪上下文，用于管理Agent执行过程中的追踪信息

    Attributes:
        agent_id: Agent标识符
        last_chunk: 最后一个chunk，用于错误处理
        trace_id: 追踪ID，用于创建执行摘要
        mapping: 映射表，用于存储invoke_type到invoke_name的映射
        trace_details: 批量收集的trace_detail，用于性能优化
        trace_logs: 批量收集的TraceAgentSpan，用于构建执行日志
        kb_retrieval_spans: 知识库检索的span列表，用于在agent执行前记录KB调用
        mode: 执行模式，0-调试运行，1-发布运行，2-节点调试
    """
    agent_id: AgentId
    last_chunk: Any = None
    trace_id: Optional[str] = None
    mapping: Dict[str, str] = field(default_factory=dict)
    trace_details: List[TraceDetail] = field(default_factory=list)
    trace_logs: List[TraceAgentSpan] = field(default_factory=list)
    agent_ouput: Optional[dict] = None
    agent_input: Optional[dict] = None
    kb_retrieval_spans: List[TraceAgentSpan] = field(default_factory=list)
    mode: int = 1  # Default to published run mode


def initialize_trace_context(
    space_id: str, agent_id: str, agent_version: str, mapping: Optional[Dict[str, str]] = None, mode: int = 1
) -> TraceContext:
    """
    初始化追踪上下文

    Args:
        space_id: 工作空间ID
        agent_id: Agent ID
        agent_version: Agent版本号
        mapping: 映射表，用于存储invoke_type到invoke_name的映射
        mode: 执行模式，0-调试运行，1-发布运行，2-节点调试

    Returns:
        TraceContext: 初始化的追踪上下文
    """
    return TraceContext(
        trace_details=[],
        trace_logs=[],
        agent_id=AgentId(
            space_id=space_id,
            agent_id=agent_id,
            agent_version=agent_version
        ),
        mapping=mapping or {},
        agent_ouput={},
        agent_input={},
        kb_retrieval_spans=[],
        mode=mode,
    )


async def process_chunk_trace(
    chunk: Any, trace_context: TraceContext, business_type: str = "AGENT"
) -> Any:
    """
    处理单个chunk的追踪信息

    Args:
        chunk: Agent执行返回的chunk
        trace_context: 追踪上下文
        business_type: 业务类型，默认为"AGENT"

    Returns:
        Tuple[Optional[Any], bool]: (响应数据, 是否有响应)
    """

    # 检查是否为需要过滤的workflow trace chunk
    if isinstance(chunk, TraceSchema) and chunk.type == "tracer_workflow":
        wf = TraceWorkflowSpan.model_validate(chunk.payload)
        # 检查条件：有workflowId字段且invokeId == workflowId
        if hasattr(wf, 'workflow_id') and wf.invoke_id == wf.workflow_id:
            return None

    if isinstance(chunk, OutputSchema) and chunk.type == "answer":
        payload = chunk.payload
        if 'output' in payload:
            trace_context.agent_ouput = {'outputs': payload.get('output')}
        return None

    # 转换chunk为响应格式和追踪信息
    rsp, trace_data, trace_detail = result_convert(chunk, business_type=business_type, mapping=trace_context.mapping)

    # 保存详细的追踪信息
    if trace_detail:
        # 保存最后一个trace chunk，用于错误处理
        trace_context.last_chunk = chunk
        trace_context.trace_details.append(trace_detail)
        if trace_context.trace_id is None:
            trace_context.trace_id = trace_detail.trace_id
            logger.debug(f"Set trace_id: {trace_context.trace_id}")

    # 收集追踪日志（TraceAgentSpan），用于构建执行日志
    if trace_data and isinstance(trace_data, TraceAgentSpan):
        trace_context.trace_logs.append(trace_data)
        logger.debug(f"Added trace log, total count: {len(trace_context.trace_logs)}")

    return rsp


async def create_kb_retrieval_span(params: KBRetrievalSpanParams) -> TraceAgentSpan:
    """
    创建知识库检索的 TraceAgentSpan
    
    Args:
        params: 知识库检索span的参数封装
        
    Returns:
        TraceAgentSpan: 知识库检索的span
    """
    invoke_id = str(uuid.uuid4())
    duration_ms = int((params.end_time - params.start_time).total_seconds() * 1000)
    
    span = TraceAgentSpan(
        trace_id=params.trace_id,
        invoke_id=invoke_id,
        parent_invoke_id=params.parent_invoke_id,
        invoke_type="retriever",
        name="knowledge_base_retrieval",
        start_time=params.start_time,
        end_time=params.end_time,
        inputs={"query": params.query},
        outputs={"kb_results": params.kb_results} if params.kb_results else None,
        elapsed_time=f"{duration_ms}ms",
    )
    return span


async def process_kb_retrieval_spans(trace_context: TraceContext, agent_invoke_id: Optional[str] = None) -> None:
    """
    处理知识库检索的spans，将它们添加到trace_logs中并保存trace_details
    
    Args:
        trace_context: 追踪上下文
        agent_invoke_id: Agent的invoke_id，用于设置知识库检索span的parent_invoke_id
    """
    from openjiuwen_studio.core.executor.util.utils import _agentspan_2_tracedetail
    
    for kb_span in trace_context.kb_retrieval_spans:
        # 如果提供了agent_invoke_id，更新parent_invoke_id
        if agent_invoke_id:
            kb_span.parent_invoke_id = agent_invoke_id
            logger.debug(f"[KB_RETRIEVAL] Set KB span parent_invoke_id to: {agent_invoke_id}")
        
        # 直接添加到trace_logs中，用于构建执行日志
        trace_context.trace_logs.append(kb_span)
        logger.debug(
            f"[KB_RETRIEVAL] Added KB span to trace_logs: "
            f"invoke_id={kb_span.invoke_id}, parent_invoke_id={kb_span.parent_invoke_id}"
        )
        
        # 创建trace_detail并添加到trace_details中
        trace_detail = _agentspan_2_tracedetail("AGENT", kb_span, trace_context.mapping)
        if trace_detail:
            trace_context.trace_details.append(trace_detail)
            logger.debug(f"[KB_RETRIEVAL] Added KB span trace_detail to trace_details")


async def finalize_trace(trace_context: TraceContext) -> None:
    """
    完成追踪，保存最终的追踪信息

    Args:
        trace_context: 追踪上下文
    """
    from openjiuwen_studio.core.executor.util.utils import save_execution_traces
    
    logger.info(f"Finalizing trace for agent: {trace_context.agent_id.agent_id}, "
               f"details size: {len(trace_context.trace_details)}, logs size: {len(trace_context.trace_logs)}")

    # 批量保存所有收集的trace details
    if trace_context.trace_details:
        try:
            await save_trace_details(trace_context.agent_id, trace_context.trace_details)
            logger.debug(f"Successfully saved {len(trace_context.trace_details)} trace details")
        except Exception as e:
            logger.error(f"Failed to save trace details: {e}")

    # 保存执行日志（TraceAgentSpan列表），用于构建执行日志树
    if trace_context.trace_logs:
        try:
            await save_execution_traces(trace_context.agent_id, trace_context.trace_logs)
            logger.debug(f"Successfully saved {len(trace_context.trace_logs)} trace logs")
        except Exception as e:
            logger.error(f"Failed to save execution traces: {e}")

    # 创建执行摘要
    if trace_context.trace_id is not None:
        try:
            trace_summary_repository.create_trace_summary_by_trace_id(
                trace_context.trace_id,
                trace_context.agent_input,
                trace_context.agent_ouput,
                mode=trace_context.mode
            )
            logger.debug(f"Created trace summary for trace_id: {trace_context.trace_id}")
        except Exception as e:
            logger.error(f"Failed to create trace summary: {e}")


async def handle_trace_error(
    trace_context: TraceContext, error_code: int, error_message: str
) -> None:
    """
    处理追踪相关的错误

    Args:
        trace_context: 追踪上下文
        error_code: 错误码
        error_message: 错误消息
    """
    logger.warning(f"Handling trace error for agent: {trace_context.agent_id.agent_id}, "
                   f"error_code: {error_code}, error_message: {error_message}")

    # 处理流式错误
    try:
        trace_id = await handle_stream_error(
            [],
            trace_context.trace_details,
            trace_context.last_chunk,
            error_code,
            error_message,
            trace_context.agent_id,
        )
        if trace_id and trace_context.trace_id is None:
            trace_context.trace_id = trace_id
    except Exception as e:
        logger.error(f"Failed to handle stream error: {e}")

    # 确保错误情况下也能保存追踪摘要
    if trace_context.trace_id is not None:
        try:
            trace_summary_repository.create_trace_summary_by_trace_id(
                trace_context.trace_id,
                trace_context.agent_input,
                trace_context.agent_ouput,
                mode=trace_context.mode
            )
            logger.debug(f"Created trace summary after error for trace_id: {trace_context.trace_id}")
        except Exception as e:
            logger.error(f"Failed to create trace summary after error: {e}")
