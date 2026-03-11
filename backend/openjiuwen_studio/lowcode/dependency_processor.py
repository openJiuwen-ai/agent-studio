#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
依赖项处理器 - 处理工作流、插件、知识库等依赖
"""

from typing import Any, Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class Workflow:
    """工作流对象"""
    def __init__(
        self,
        workflow_id: str,
        workflow_name: str,
        description: str = "",
        schema: Optional[Dict] = None,
        input_params: Optional[List] = None,
        output_params: Optional[List] = None,
        variables: Optional[List] = None
    ):
        self.workflow_id = workflow_id
        self.workflow_name = workflow_name
        self.description = description
        self.schema = schema or {}
        self.input_params = input_params or []
        self.output_params = output_params or []
        self.variables = variables or []


class Tool:
    """工具对象"""
    def __init__(
        self,
        tool_id: str,
        tool_name: str,
        description: str = "",
        tool_type: str = "plugin",
        config: Optional[Dict] = None,
        input_schema: Optional[Dict] = None,
        output_schema: Optional[Dict] = None
    ):
        self.tool_id = tool_id
        self.tool_name = tool_name
        self.description = description
        self.tool_type = tool_type
        self.config = config or {}
        self.input_schema = input_schema or {}
        self.output_schema = output_schema or {}


class DependencyProcessor:
    """
    依赖项处理器
    
    处理工作流、插件、知识库等依赖
    """
    
    def __init__(
        self,
        workflow_runner: Optional[Any] = None,
        plugin_manager: Optional[Any] = None
    ):
        self.workflow_runner = workflow_runner
        self.plugin_manager = plugin_manager
    
    async def process(
        self,
        dependencies: Dict[str, Any],
        current_user: Optional[Dict] = None
    ) -> Tuple[List[Workflow], List[Tool], List[Any]]:
        """
        处理依赖项
        
        Args:
            dependencies: 依赖项定义
            current_user: 当前用户信息
            
        Returns:
            (workflows, plugins, knowledge_bases)
        """
        workflows = await self._process_workflows(
            dependencies.get("workflows", []),
            current_user
        )
        
        plugins = await self._process_plugins(
            dependencies.get("plugins", []),
            current_user
        )
        
        knowledge_bases = await self._process_knowledge_bases(
            dependencies.get("knowledge_bases", []),
            current_user
        )
        
        logger.info(
            f"Processed dependencies: "
            f"{len(workflows)} workflows, "
            f"{len(plugins)} plugins, "
            f"{len(knowledge_bases)} knowledge bases"
        )
        
        return workflows, plugins, knowledge_bases
    
    async def _process_workflows(
        self,
        workflows_data: List[Dict[str, Any]],
        current_user: Optional[Dict] = None
    ) -> List[Workflow]:
        """
        处理工作流
        
        Args:
            workflows_data: 工作流数据列表
            current_user: 当前用户信息
            
        Returns:
            Workflow对象列表
        """
        workflows = []
        
        for workflow_data in workflows_data:
            try:
                workflow = DependencyProcessor._create_workflow_from_data(workflow_data)
                if workflow:
                    workflows.append(workflow)
            except Exception as e:
                logger.error(f"Failed to process workflow: {e}")
                continue
        
        return workflows
    
    @staticmethod
    def _create_workflow_from_data(
        workflow_data: Dict[str, Any]
    ) -> Optional[Workflow]:
        """
        从数据创建工作流
        
        Args:
            workflow_data: 工作流数据
            
        Returns:
            Workflow 对象或 None
        """
        try:
            workflow_id = workflow_data.get("workflow_id") or workflow_data.get("id")
            workflow_name = workflow_data.get("workflow_name") or workflow_data.get("name", "Unnamed Workflow")
            
            # 创建工作流对象
            workflow = Workflow(
                workflow_id=workflow_id,
                workflow_name=workflow_name,
                description=workflow_data.get("description", ""),
                schema=workflow_data.get("schema", {}),
                input_params=workflow_data.get("input_params", []),
                output_params=workflow_data.get("output_params", []),
                variables=workflow_data.get("variables", [])
            )
            
            return workflow
        except Exception as e:
            logger.error(f"Error creating workflow: {e}")
            return None
    
    async def _process_plugins(
        self,
        plugins_data: List[Dict[str, Any]],
        current_user: Optional[Dict] = None
    ) -> List[Tool]:
        """
        处理插件
        
        Args:
            plugins_data: 插件数据列表
            current_user: 当前用户信息
            
        Returns:
            Tool对象列表
        """
        tools = []
        
        for plugin_data in plugins_data:
            try:
                tool = DependencyProcessor._create_tool_from_plugin_data(plugin_data)
                if tool:
                    tools.append(tool)
            except Exception as e:
                logger.error(f"Failed to process plugin: {e}")
                continue
        
        return tools
    
    @staticmethod
    def _create_tool_from_plugin_data(
        plugin_data: Dict[str, Any]
    ) -> Optional[Tool]:
        """
        从插件数据创建工具
        
        Args:
            plugin_data: 插件数据
            
        Returns:
            Tool 对象或 None
        """
        try:
            plugin_id = plugin_data.get("plugin_id") or plugin_data.get("id")
            plugin_name = plugin_data.get("plugin_name") or plugin_data.get("name", "Unnamed Plugin")
            
            # 创建工具对象
            tool = Tool(
                tool_id=plugin_id,
                tool_name=plugin_name,
                description=plugin_data.get("description", ""),
                tool_type="plugin",
                config=plugin_data.get("config", {}),
                input_schema=plugin_data.get("input_schema", {}),
                output_schema=plugin_data.get("output_schema", {})
            )
            
            return tool
        except Exception as e:
            logger.error(f"Error creating tool: {e}")
            return None
    
    async def _process_knowledge_bases(
        self,
        knowledge_bases_data: List[Dict[str, Any]],
        current_user: Optional[Dict] = None
    ) -> List[Any]:
        """
        处理知识库
        
        Args:
            knowledge_bases_data: 知识库数据列表
            current_user: 当前用户信息
            
        Returns:
            知识库对象列表
        """
        knowledge_bases = []
        
        for kb_data in knowledge_bases_data:
            try:
                kb = DependencyProcessor._create_knowledge_base_from_data(kb_data)
                if kb:
                    knowledge_bases.append(kb)
            except Exception as e:
                logger.error(f"Failed to process knowledge base: {e}")
                continue
        
        return knowledge_bases
    
    @staticmethod
    def _create_knowledge_base_from_data(
        kb_data: Dict[str, Any]
    ) -> Optional[Any]:
        """
        从数据创建知识库
        
        Args:
            kb_data: 知识库数据
            
        Returns:
            知识库对象或 None
        """
        try:
            kb_id = kb_data.get("knowledge_base_id") or kb_data.get("id")
            kb_name = kb_data.get("knowledge_base_name") or kb_data.get("name", "Unnamed KB")
            
            # 创建知识库对象（简化版）
            kb = {
                "knowledge_base_id": kb_id,
                "knowledge_base_name": kb_name,
                "description": kb_data.get("description", ""),
                "embedding_model": kb_data.get("embedding_model", {}),
                "retrieval_config": kb_data.get("retrieval_config", {}),
                "documents": kb_data.get("documents", [])
            }
            
            return kb
        except Exception as e:
            logger.error(f"Error creating knowledge base: {e}")
            return None
    
    @staticmethod
    def validate_dependencies(
        dependencies: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """
        验证依赖项
        
        Args:
            dependencies: 依赖项定义
            
        Returns:
            (是否有效，错误信息列表)
        """
        errors = []
        
        # 验证工作流
        workflows = dependencies.get("workflows", [])
        for i, workflow in enumerate(workflows):
            if not workflow.get("schema"):
                errors.append(f"Workflow {i} missing 'schema'")
        
        # 验证插件
        plugins = dependencies.get("plugins", [])
        for i, plugin in enumerate(plugins):
            if not plugin.get("plugin_id") and not plugin.get("id"):
                errors.append(f"Plugin {i} missing 'plugin_id' or 'id'")
        
        # 验证知识库
        knowledge_bases = dependencies.get("knowledge_bases", [])
        for i, kb in enumerate(knowledge_bases):
            if not kb.get("knowledge_base_id") and not kb.get("id"):
                errors.append(f"Knowledge base {i} missing 'knowledge_base_id' or 'id'")
        
        return len(errors) == 0, errors
