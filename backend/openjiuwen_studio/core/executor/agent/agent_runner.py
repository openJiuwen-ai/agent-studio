#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

"""
Agent Runner - Agent执行管理器

本模块负责Agent的完整执行生命周期管理，包括：
1. Agent实例的创建、编译和缓存管理
2. Agent的流式执行和结果处理
3. 执行过程的追踪和错误处理
4. 与Workflow和Plugin系统的集成

核心功能：
- Agent配置获取和适配
- Agent实例缓存优化
- 异步流式执行
- 执行追踪和监控

- 完善的错误处理机制
"""
import asyncio
import json
from typing import Any, AsyncGenerator, Dict, List, Optional, Union
from datetime import datetime, timezone

from fastapi import status
from openjiuwen.core.single_agent.legacy.config import ReActAgentConfig, WorkflowAgentConfig
from openjiuwen.core.single_agent.base import BaseAgent as InvokableAgent
from openjiuwen_studio.core.common.exceptions import BaseError
from openjiuwen.core.common.logging import logger
from openjiuwen.core.retrieval.common.config import RetrievalConfig
from openjiuwen.core.retrieval.graph_knowledge_base import GraphKnowledgeBase
from openjiuwen.core.retrieval.simple_knowledge_base import (
    retrieve_multi_kb,
    SimpleKnowledgeBase
)
from openjiuwen.core.runner import Runner
from openjiuwen.core.session import InteractiveInput
from openjiuwen.core.foundation.llm import Model, ModelClientConfig, ModelRequestConfig

import openjiuwen_studio.core.manager.agent as mgr
from openjiuwen_studio.core.common.status_code import StatusCode
from openjiuwen_studio.core.executor.agent.agent_trace_utils import (
    finalize_trace,
    handle_trace_error,
    initialize_trace_context,
    process_chunk_trace,
    create_kb_retrieval_span,
    process_kb_retrieval_spans,
    KBRetrievalSpanParams
)
from openjiuwen_studio.core.executor.plugin.plugin_mgr import PluginManager
from openjiuwen_studio.core.executor.workflow.pregel_graph_adapter import JiuWenGraphException
from openjiuwen_studio.core.executor.workflow.workflow_runner import WorkflowRunner
from openjiuwen_studio.core.manager.knowledge_base import create_knowledge_base_for_retrieval
from openjiuwen_studio.memory_engine_start import MemoryEngineManager
from openjiuwen_studio.schemas import AgentGetVersion
from .agent import Agent
from .agent_dl_adapter import AgentDlAdapter


class _LLMInvokeModelWrapper:
    """Wraps an openjiuwen Model so invoke() always receives a model name when missing.

    AgenticRetriever calls llm.invoke(...) without model=; this wrapper injects model=model_name
    so the API request always has a valid model parameter (no core change required).
    """

    __slots__ = ("_model", "_model_name")

    def __init__(self, model: Model, model_name: str) -> None:
        self._model = model
        self._model_name = model_name or ""

    async def invoke(self, *args, **kwargs) -> Any:
        if self._model_name and kwargs.get("model") is None:
            kwargs = {**kwargs, "model": self._model_name}
        return await self._model.invoke(*args, **kwargs)


def get_memory_engine():
    return MemoryEngineManager.get_instance()


async def _process_kb_retrieval_info(
    kb_retrieval_info: Dict[str, Any],
    trace_context: Any,
    agent_invoke_id: Optional[str] = None
) -> None:
    """
    处理知识库检索信息，创建TraceAgentSpan并添加到追踪上下文
    
    Args:
        kb_retrieval_info: 知识库检索信息字典，包含query、start_time、end_time、results
        trace_context: 追踪上下文
        agent_invoke_id: Agent的invoke_id，用于设置知识库检索span的parent_invoke_id
    """
    if not kb_retrieval_info or not trace_context.trace_id:
        return
    
    start_time = kb_retrieval_info.get("start_time")
    end_time = kb_retrieval_info.get("end_time")
    query = kb_retrieval_info.get("query", "")
    results = kb_retrieval_info.get("results", [])
    
    if not start_time or not end_time:
        logger.warning("[KB_RETRIEVAL] Missing start_time or end_time for KB retrieval span")
        return
    
    try:
        # 创建知识库检索的span参数
        span_params = KBRetrievalSpanParams(
            trace_id=trace_context.trace_id,
            query=query,
            kb_results=results,
            start_time=start_time,
            end_time=end_time,
            parent_invoke_id=agent_invoke_id  # 知识库检索是agent的直接子节点
        )
        # 创建知识库检索的span
        kb_span = await create_kb_retrieval_span(span_params)
        
        # 添加到追踪上下文
        trace_context.kb_retrieval_spans.append(kb_span)
        
        # 处理知识库检索的spans
        await process_kb_retrieval_spans(trace_context, agent_invoke_id=agent_invoke_id)
        
        logger.debug(f"[KB_RETRIEVAL] Created and processed KB retrieval span: {kb_span.invoke_id}")
    except Exception as e:
        logger.error(f"[KB_RETRIEVAL] Failed to process KB retrieval span: {str(e)}", exc_info=True)


async def _fetch_agent_dl(
        id: str,
        version: str,
        space_id: str,
        current_user: Dict[str, Any]
) -> str:
    """
    从管理服务获取Agent的DL（Domain Language）配置

    Args:
        id: Agent ID
        version: Agent版本号
        space_id: 工作空间ID，用于多租户隔离
        current_user: 当前用户信息，包含权限和上下文

    Returns:
        str: Agent DL配置的JSON字符串

    Raises:
        BaseError: 当获取配置失败时抛出异常
    """
    # 构建请求参数
    req = {"agent_id": id, "space_id": space_id, "agent_version": version}

    # 调用管理服务获取Agent配置
    res = mgr.agent_convert(AgentGetVersion(**req), current_user)
    logger.warning(f"_fetch_agent_dl mgr.agent_convert res: {res}")

    # 检查响应状态
    if res.code != status.HTTP_200_OK:
        raise BaseError(
            code=StatusCode.AGENT_DL_FETCH_FAILED.code,
            message=StatusCode.AGENT_DL_FETCH_FAILED.errmsg.format(msg=str(res.message)),
        )

    agent_dl = res.data
    if agent_dl is None:
        raise BaseError(
            code=StatusCode.AGENT_DL_FETCH_FAILED.code,
            message=StatusCode.AGENT_DL_FETCH_FAILED.errmsg.format(msg=str("fetch agent failed"))
        )

    # 序列化为JSON字符串供后续使用
    agent_dl_json = json.dumps(agent_dl)
    logger.debug(f"fetch agent dl: {agent_dl_json}")
    return agent_dl_json


def generate_agent_key(agent_id: str, agent_version: str) -> str:
    """
    生成Agent实例的缓存键

    Args:
        agent_id: Agent ID
        agent_version: Agent版本号

    Returns:
        str: 格式为 "agent_id_agent_version" 的缓存键
    """
    return f"{agent_id}_{agent_version}"


class AgentRunner:
    """
    Agent执行管理器

    负责Agent的完整生命周期管理，包括创建、缓存、执行和追踪。
    采用缓存机制优化性能，避免重复编译相同配置的Agent实例。

    Attributes:
        flow_mgr: Workflow运行管理器，负责处理Agent中的Workflow组件
        plugin_mgr: 插件管理器，负责处理Agent中的Plugin组件
        _agent_instances: Agent实例缓存，按用户维度组织以提高性能
    """

    def __init__(
            self,
            flow_mgr: WorkflowRunner,
            plugin_mgr: PluginManager
    ) -> None:
        """
        初始化AgentRunner

        Args:
            flow_mgr: Workflow运行管理器实例
            plugin_mgr: 插件管理器实例
        """
        self.flow_mgr = flow_mgr
        self.plugin_mgr = plugin_mgr
        # Agent实例缓存：{user_id: {agent_key: (config, instance)}}
        self._agent_instances: Dict[str, Dict[str, Any]] = {}

    async def create_new_agent(
            self,
            agent_config: Union[ReActAgentConfig, WorkflowAgentConfig],
            space_id: str,
            current_user: Dict[str, Any]
    ) -> InvokableAgent:
        """
        创建并编译一个新的Agent实例

        Args:
            agent_config: Agent配置对象 (ReActAgentConfig 或 WorkflowAgentConfig)
            space_id: 工作空间ID，用于多租户隔离
            current_user: 当前用户信息，包含权限和上下文

        Returns:
            InvokableAgent: 可执行的Agent实例
        """
        # 创建Agent实例并编译
        agent = Agent(self.flow_mgr, agent_config, self.plugin_mgr)
        invokable_agent = await agent.compile(space_id, current_user)
        return invokable_agent

    async def get_agent_instance(
            self,
            user_id: str,
            agent_id: str,
            agent_version: str,
            agent_config: Union[ReActAgentConfig, WorkflowAgentConfig],
            space_id: str,
            current_user: Dict[str, Any]
    ) -> InvokableAgent:
        """
        获取Agent实例，支持缓存机制以提高性能

        基于用户ID、Agent ID和版本号进行缓存，如果配置未变更则直接返回缓存实例，
        否则重新创建并更新缓存。

        Args:
            user_id: 用户ID，用于缓存隔离
            agent_id: Agent ID
            agent_version: Agent版本号
            agent_config: Agent配置对象 (ReActAgentConfig 或 WorkflowAgentConfig)
            space_id: 工作空间ID
            current_user: 当前用户信息

        Returns:
            InvokableAgent: 可执行的Agent实例（可能来自缓存）
        """
        # 初始化用户的缓存空间
        if user_id not in self._agent_instances:
            self._agent_instances[user_id] = {}

        # 生成缓存键
        agent_key = generate_agent_key(agent_id, agent_version)

        # 初始化缓存条目
        if agent_key not in self._agent_instances[user_id]:
            self._agent_instances[user_id][agent_key] = ("", None)

        # 检查缓存
        (cache_config, catch_instance) = self._agent_instances[user_id][agent_key]
        if cache_config == agent_config:
            # 配置未变更，直接返回缓存实例
            return catch_instance

        # 配置已变更或首次创建，重新编译Agent
        invokable_agent = await self.create_new_agent(agent_config, space_id, current_user)
        if catch_instance:
            invokable_agent._context_engine._context_pool = catch_instance._context_engine._context_pool

        # 更新缓存
        self._agent_instances[user_id][agent_key] = (agent_config, invokable_agent)
        return invokable_agent

    async def reset_agent_instance_cache(
            self,
            conversation_id: str,
            agent_id: str,
            agent_version: str
    ) -> bool:
        """
        重置Agent实例缓存
        
        Args:
            conversation_id: 对话ID
            agent_id: Agent ID
            agent_version: Agent版本号
        
        Returns:
            bool: 是否成功清除缓存
        """
        agent_key = f"{agent_id}_{agent_version}"
        if conversation_id in self._agent_instances:
            if agent_key in self._agent_instances[conversation_id]:
                (_, catch_instance) = self._agent_instances[conversation_id][agent_key]
                await catch_instance.clear_session(conversation_id)
                del self._agent_instances[conversation_id][agent_key]
                return True
        return False
        
    async def _create_mapping_table(self, agent_config: Union[ReActAgentConfig, WorkflowAgentConfig], space_id: str) -> Dict[str, str]:

        """
        创建invoke_type到invoke_name的映射表
        
        Args:
            agent_config: Agent配置对象
            space_id: 工作空间ID
            
        Returns:
            Dict[str, str]: 映射表，key为invoke_type，value为invoke_name
        """
        mapping = {}
        
        # 1. 添加LLM映射
        if hasattr(agent_config, 'model') and hasattr(agent_config.model, 'model_info'):
            mapping["llm"] = agent_config.model.model_info.model_name
        
        # 2. 添加工作流及其组件映射
        if hasattr(agent_config, 'workflows'):
            for workflow in agent_config.workflows:
                
                # 添加工作流组件的映射
                try:
                    from openjiuwen_studio.core.manager.repositories.workflow_repository import workflow_repository
                    from openjiuwen_studio.schemas.workflow import WorkflowId
                    
                    # 从数据库获取workflow信息
                    workflow_id_obj = WorkflowId(
                        workflow_id=workflow.id,
                        space_id=space_id,
                        workflow_version=workflow.version
                    )
                    
                    workflow_res = workflow_repository.workflow_get(workflow_id_obj)
                    if workflow_res.code == 200 and workflow_res.data:
                        workflow_db = workflow_res.data
                        # 处理workflow_db可能是字典的情况
                        if isinstance(workflow_db, dict):
                            # 如果是字典，直接从字典中获取schema
                            schema_str = workflow_db.get('schema', '')
                        else:
                            # 如果是对象，从属性中获取schema
                            schema_str = workflow_db.schema if hasattr(workflow_db, 'schema') else ''
                        
                        workflow_schema = json.loads(schema_str) if schema_str else {}
                        
                        if isinstance(workflow_schema, dict):
                            def extract_component_names(schema_part, name_map, parent_path="", parent_component_ids=None):
                                """递归提取所有组件名称，包括嵌套结构和层级关系"""
                                if parent_component_ids is None:
                                    parent_component_ids = []
                                    
                                if isinstance(schema_part, dict):
                                    # 提取当前节点的组件信息（包括子工作流节点本身）
                                    if 'id' in schema_part and 'data' in schema_part and 'title' in schema_part['data']:
                                        component_id = schema_part['id']
                                        component_title = schema_part['data']['title']
                                        
                                        # 添加基础ID映射
                                        name_map[component_id] = component_title
                                        
                                        # 生成并添加完整的层级组件ID映射
                                        if parent_component_ids:
                                            full_component_id = f"{'.'.join(parent_component_ids)}.{component_id}"
                                            name_map[full_component_id] = component_title
                                    
                                    # 处理完整的工作流schema（包含nodes和edges）
                                    if 'nodes' in schema_part and isinstance(schema_part['nodes'], list):
                                        # 遍历所有节点
                                        for node in schema_part['nodes']:
                                            if isinstance(node, dict) and 'id' in node and 'data' in node and 'title' in node['data']:
                                                node_id = node['id']
                                                node_title = node['data']['title']
                                                
                                                # 添加基础ID映射
                                                name_map[node_id] = node_title
                                                
                                                # 生成并添加完整的层级组件ID映射
                                                if parent_component_ids:
                                                    full_node_id = f"{'.'.join(parent_component_ids)}.{node_id}"
                                                    name_map[full_node_id] = node_title
                                    
                                    # 特殊处理子工作流组件
                                    if 'type' in schema_part and (schema_part['type'] == '14' or 'subWorkflow' in schema_part.get('data', {}).get('configs', {})):
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
                                                    extract_component_names(sub_wf_schema, name_map, f"{parent_path}.sub_workflow.{current_component_id}", new_parent_ids)
                                            except json.JSONDecodeError as e:
                                                logger.warning(f"Failed to parse embedded sub-workflow schema: {e}")
                                        
                                        # 方法2: 从configs.subWorkflow中获取子工作流信息（备用）
                                        sub_wf_info = sub_wf_config.get('configs', {}).get('subWorkflow', {})
                                        sub_wf_id = sub_wf_info.get('workflowId') or sub_wf_info.get('workflow_id') or sub_wf_info.get('id')
                                        
                                        # 只有当有子工作流ID但没有schema时，才记录日志，不进行数据库查询
                                        if sub_wf_id and not sub_wf_schema_str:
                                            logger.debug(f"Found sub-workflow: {sub_wf_id} but no embedded schema available, skipping further processing")
                                    
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
                            
                            # 提取组件名称
                            extract_component_names(workflow_schema, mapping)
                            
                except Exception as e:
                    # 处理异常，确保即使处理单个workflow失败，也能继续处理其他workflow
                    logger.error(f"Failed to process workflow {workflow.id} for mapping table: {str(e)}", exc_info=True)
                    # 继续处理其他workflow，不中断整个映射表的创建
        return mapping

    async def run(
            self,
            id: str,
            version: str,
            inputs: Any,
            conversation_id: str,
            space_id: str,
            current_user: Dict[str, Any]
    ) -> AsyncGenerator[Any, None]:
        """
        执行Agent实例并返回流式结果

        这是Agent执行的核心方法，负责完整的执行流程：
        1. 参数验证和配置获取
        2. Agent实例创建和缓存
        3. 流式执行和结果处理
        4. 执行追踪和监控
        5. 异常处理和错误恢复

        Args:
            id: Agent ID
            version: Agent版本号
            inputs: 输入参数，必须包含conversation_id
            conversation_id: 对话ID，用于会话上下文管理
            space_id: 工作空间ID
            current_user: 当前用户信息

        Yields:
            Any: Agent执行的流式结果

        Raises:
            BaseError: 业务异常，如配置获取失败等
            JiuWenGraphException: 图执行异常
            Exception: 其他未预期的异常
        """
        # 1. 参数验证 - 确保输入包含必要的conversation_id
        if isinstance(inputs, InteractiveInput):
            inputs = {"conversation_id": conversation_id, "query": inputs}
        elif "conversation_id" not in inputs:
            raise BaseError(StatusCode.AGENT_MISSING_CONVERSATION_ID.code,
                                      StatusCode.AGENT_MISSING_CONVERSATION_ID.errmsg)

        # 2. 获取Agent配置
        agent_dl_json = await _fetch_agent_dl(id, version, space_id, current_user)
        agent_config = AgentDlAdapter.convert_to_agent_config(agent_dl_json)

        # 2.1 使用知识库检索（如果配置了知识库）
        kb_ids, retrieval_config = AgentDlAdapter.get_knowledge_config(agent_dl_json)
        kb_retrieval_info = None
        if kb_ids:
            # 初始化知识库检索信息
            kb_retrieval_info = {
                "query": inputs.get("query", ""),
                "kb_ids": kb_ids,
                "start_time": None,
                "end_time": None,
                "results": None,
            }
            logger.debug(
                f"[KB_RETRIEVAL] Start to use knowledge retrieval - KB IDs: {kb_ids}, "
                f"Retrieval config: {retrieval_config}")
            try:
                # 创建知识库实例列表
                kb_instances: List[Union[SimpleKnowledgeBase, GraphKnowledgeBase]] = []

                # 检查是否需要 LLM 客户端（如果使用图检索或 Agentic 检索）
                llm_client = None
                model_name = None
                if retrieval_config.use_graph:
                    # 从 agent_config 中获取 LLM 配置（使用 ModelClientConfig + ModelRequestConfig，保证基础/Agentic 模式均可用）
                    if hasattr(agent_config, 'model') and hasattr(agent_config.model, 'model_info'):
                        model_info = agent_config.model.model_info
                        model_name = (
                            getattr(model_info, "model_type", None)
                            or getattr(model_info, "model_name", None)
                            or getattr(model_info, "model", None)
                            or ""
                        )
                        client_config = ModelClientConfig(
                            client_provider=agent_config.model.model_provider,
                            api_key=getattr(model_info, "api_key", "") or "",
                            api_base=getattr(model_info, "api_base", "") or "",
                            timeout=getattr(model_info, "timeout", 60.0) or 60.0,
                            verify_ssl=False,
                            ssl_cert=None,
                        )
                        request_config = ModelRequestConfig(
                            model_name=model_name,
                            temperature=getattr(model_info, "temperature", 0.7),
                            top_p=getattr(model_info, "top_p", 0.9),
                        )
                        raw_llm = Model(client_config, request_config)
                        llm_client = _LLMInvokeModelWrapper(raw_llm, model_name) if model_name else raw_llm
                        logger.debug(f"[KB_RETRIEVAL] Created LLM client for graph/agentic retrieval")

                # 为每个知识库创建实例
                for kb_id in kb_ids:
                    try:
                        kb_instance = await create_knowledge_base_for_retrieval(
                            kb_id=kb_id,
                            space_id=space_id,
                            use_graph=retrieval_config.use_graph,
                            llm_client=llm_client,
                            model_name=model_name,
                        )
                        kb_instances.append(kb_instance)
                        logger.debug(f"[KB_RETRIEVAL] Created knowledge base instance - KB ID: {kb_id}")
                    except Exception as e:
                        logger.error(f"[KB_RETRIEVAL] Failed to create knowledge base instance for {kb_id}: {str(e)}",
                                     exc_info=True)
                        # 继续处理其他知识库，不中断整个流程
                        continue

                if kb_instances:
                    # 创建 RetrievalConfig
                    score_threshold = retrieval_config.score_threshold
                    openjiuwen_retrieval_config = RetrievalConfig(
                        top_k=retrieval_config.topk or 5,
                        use_graph=retrieval_config.use_sync or retrieval_config.use_agent,
                        graph_expansion=retrieval_config.use_sync,
                        agentic=retrieval_config.use_agent,
                        score_threshold=score_threshold,
                    )

                    # 执行多知识库检索
                    query = inputs.get("query", "")
                    if query:
                        logger.debug(
                            f"[KB_RETRIEVAL] Executing multi-KB retrieval - Query: {query}, "
                            f"KB count: {len(kb_instances)}")
                        
                        # 记录开始时间
                        kb_start_time = datetime.now(tz=timezone.utc)
                        if kb_retrieval_info:
                            kb_retrieval_info["start_time"] = kb_start_time
                        
                        kb_results = await retrieve_multi_kb(
                            kbs=kb_instances,
                            query=query,
                            config=openjiuwen_retrieval_config,
                            top_k=retrieval_config.topk or 5
                        )
                        
                        # 记录结束时间和结果
                        kb_end_time = datetime.now(tz=timezone.utc)
                        if kb_retrieval_info:
                            kb_retrieval_info["end_time"] = kb_end_time
                            kb_retrieval_info["results"] = kb_results

                        # 将检索结果添加到 agent_config 的 prompt_template
                        if kb_results:
                            logger.debug(f"[KB_RETRIEVAL] Retrieved {kb_results} results from knowledge bases")
                            for result_text in kb_results:
                                if result_text:
                                    agent_config.prompt_template.append({
                                        "role": "system",
                                        "content": result_text,
                                    })
                        else:
                            logger.debug(f"[KB_RETRIEVAL] No results retrieved from knowledge bases")
                    else:
                        logger.warning(f"[KB_RETRIEVAL] Query is empty, skipping knowledge base retrieval")

                # 清理知识库实例
                for kb_instance in kb_instances:
                    try:
                        await kb_instance.close()
                    except Exception as e:
                        logger.warning(f"[KB_RETRIEVAL] Failed to close knowledge base instance: {str(e)}")

            except Exception as e:
                # 知识库检索失败不应该中断整个 Agent 执行流程
                logger.error(f"[KB_RETRIEVAL] Knowledge base retrieval failed: {str(e)}", exc_info=True)

        # 3. 获取Agent实例（带缓存机制）
        invokable_agent: InvokableAgent = await self.get_agent_instance(
            conversation_id, id, version, agent_config, space_id, current_user
        )

        # 4. 创建组件id-name映射表
        mapping = await self._create_mapping_table(agent_config, space_id)
        
        # 5. 初始化追踪上下文
        trace_context = initialize_trace_context(space_id, id, version, mapping)

        try:
            # 6. 执行Agent流式推理
            inputs["user_id"] = space_id
            inputs["group_id"] = agent_config.id
            trace_context.agent_input = {'inputs': inputs.get('query')}
            
            # 6.1 处理知识库检索的spans（在获取trace_id后）
            # 注意：agent的顶层invoke_id就是agent_id（即id参数），不需要从trace中获取
            kb_spans_processed = False
            agent_invoke_id = id  # agent的顶层invoke_id就是agent_id
            
            async for chunk in Runner.run_agent_streaming(
                agent=invokable_agent,
                inputs=inputs,
                session=conversation_id
            ):
                # 处理单个chunk的追踪信息
                rsp = await process_chunk_trace(chunk, trace_context)
                
                # 在获取到trace_id后，处理知识库检索的spans
                if not kb_spans_processed and trace_context.trace_id and kb_retrieval_info:
                    logger.debug(
                        f"[KB_RETRIEVAL] Processing KB retrieval spans - "
                        f"trace_id: {trace_context.trace_id}, agent_invoke_id: {agent_invoke_id}"
                    )
                    await _process_kb_retrieval_info(kb_retrieval_info, trace_context, agent_invoke_id)
                    kb_spans_processed = True
                    logger.debug(f"[KB_RETRIEVAL] KB retrieval spans processed successfully")

                # 返回响应结果
                if rsp:
                    yield rsp

            # 7. 执行完成后的清理和保存
            await finalize_trace(trace_context)

        except (BaseError, JiuWenGraphException) as e:
            # 7a. 处理已知的业务异常和图执行异常
            await handle_trace_error(trace_context, e.code, e.message)
            raise

        except Exception as e:
            # 7c. 处理未预期的异常
            await handle_trace_error(trace_context, -1, str(e))
            raise

        except BaseException as e:
            if isinstance(e, asyncio.exceptions.CancelledError):
                # 7d. 处理运行取消/中断
                logger.warning(f"Agent execution interrupted: {type(e)}: {str(e)}")
                await handle_trace_error(trace_context, -2, f"Agent Execution interrupted: {type(e)}")
            raise


# 全局Agent管理器实例
# 作为单例使用，负责整个系统的Agent执行管理
agent_mgr = AgentRunner(WorkflowRunner(), PluginManager())
