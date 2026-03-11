#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
配置适配器 - 将导出的Agent配置转换为内部DL格式
"""

from typing import Any, Dict, List, Optional, Union
import copy
import logging

logger = logging.getLogger(__name__)

try:
    from openjiuwen.core.application.llm_agent import ReActAgentConfig, ConstrainConfig
    from openjiuwen.core.single_agent.legacy import WorkflowAgentConfig, DefaultResponse, WorkflowSchema, PluginSchema
    from openjiuwen.core.foundation.llm import BaseModelInfo, ModelConfig
    from openjiuwen.core.common.constants.enums import ControllerType
    from openjiuwen.core.workflow import WorkflowCard
    HAS_CORE_CONFIG = True
except ImportError:
    ReActAgentConfig = None
    WorkflowAgentConfig = None
    ConstrainConfig = None
    DefaultResponse = None
    WorkflowSchema = None
    PluginSchema = None
    BaseModelInfo = None
    ModelConfig = None
    ControllerType = None
    WorkflowCard = None
    HAS_CORE_CONFIG = False


class AgentDLConfig:
    """Agent DL配置"""
    def __init__(
        self,
        agent_base,
        workflows: Optional[List[Any]] = None,
        plugins: Optional[List[Any]] = None,
        knowledge_bases: Optional[List[Any]] = None
    ):
        self.agent_base = agent_base
        self.workflows = workflows or []
        self.plugins = plugins or []
        self.knowledge_bases = knowledge_bases or []


class ConfigAdapter:
    """
    配置适配器
    
    将导出的Agent配置转换为内部DL格式
    """
    
    @staticmethod
    def adapt(
        agent_config: Dict[str, Any]
    ) -> Union["ReActAgentConfig", "WorkflowAgentConfig"]:
        """
        适配配置
        
        Args:
            agent_config: 导出的 agent 配置
            
        Returns:
            ReActAgentConfig 或 WorkflowAgentConfig (来自 openjiuwen.core)
        """
        if not HAS_CORE_CONFIG:
            raise ImportError(
                "Cannot import config classes from openjiuwen.core. "
                "Please ensure openjiuwen is installed correctly."
            )
        
        agent_type = agent_config.get("agent_type", "react").lower()
        
        if agent_type == "react":
            return ConfigAdapter._adapt_react_config(agent_config)
        else:
            return ConfigAdapter._adapt_workflow_config(agent_config)
    
    @staticmethod
    def _adapt_react_config(
        config: Dict[str, Any]
    ) -> "ReActAgentConfig":
        """
        适配 ReAct Agent 配置
        
        Args:
            config: 导出的 agent 配置
            
        Returns:
            ReActAgentConfig (来自 openjiuwen.core)
        """
        model_config = ConfigAdapter._create_core_model_config(config)
        
        workflow_cards = ConfigAdapter._create_workflow_cards(config.get("workflows", []))
        plugin_schemas = ConfigAdapter._create_plugin_schemas(config.get("plugins", []))
        
        prompt_template = config.get("prompt_template", [])
        if isinstance(prompt_template, str):
            prompt_template = [{"role": "system", "content": prompt_template}]
        
        constrain = ConstrainConfig(
            reserved_max_chat_rounds=config.get("constraint", {}).get("reserved_max_chat_rounds", 10),
            max_iteration=config.get("constraint", {}).get("max_iteration", 5),
        )
        
        react_config = ReActAgentConfig(
            id=config.get("agent_id", ""),
            version=config.get("agent_version", "draft"),
            description=config.get("description", ""),
            controller_type=ControllerType.ReActController,
            workflows=workflow_cards,
            model=model_config,
            tools=[],
            prompt_template_name=config.get("prompt_template_name", ""),
            prompt_template=prompt_template,
            constrain=constrain,
            plugins=plugin_schemas,
            memory_scope_id="",
        )
        
        return react_config
    
    @staticmethod
    def _adapt_workflow_config(
        config: Dict[str, Any]
    ) -> "WorkflowAgentConfig":
        """
        适配 Workflow Agent 配置
        
        Args:
            config: 导出的 agent 配置
            
        Returns:
            WorkflowAgentConfig (来自 openjiuwen.core)
        """
        model_config = ConfigAdapter._create_core_model_config(config)
        
        workflow_cards = ConfigAdapter._create_workflow_cards(config.get("workflows", []))
        
        default_response_text = config.get("default_response", "") or "抱歉，我无法理解您的问题，请换一种方式表达"
        
        workflow_config = WorkflowAgentConfig(
            id=config.get("agent_id", ""),
            version=config.get("agent_version", "draft"),
            description=config.get("description", ""),
            controller_type=ControllerType.WorkflowController,
            workflows=workflow_cards,
            model=model_config,
            tools=[],
            default_response=DefaultResponse(text=default_response_text),
        )
        
        return workflow_config
    
    @staticmethod
    def _create_core_model_config(
        config: Dict[str, Any]
    ) -> "ModelConfig":
        """
        创建 openjiuwen.core 的 ModelConfig
        
        Args:
            config: agent 配置
            
        Returns:
            ModelConfig
        """
        model_data = config.get("model", {})
        model_info_data = model_data.get("model_info", {})
        
        model_info = BaseModelInfo(
            api_key=model_info_data.get("api_key", ""),
            api_base=model_info_data.get("base_url", ""),
            model_name=model_data.get("model_name", ""),
            temperature=model_info_data.get("temperature", 0.7),
            top_p=model_info_data.get("top_p", 0.9),
            streaming=False,
            timeout=model_info_data.get("timeout", 300)
        )
        
        model_provider = model_data.get("model_provider", "OpenAI")
        if model_provider.lower() == 'openai':
            model_provider = 'OpenAI'
        elif model_provider.lower() == 'siliconflow':
            model_provider = 'SiliconFlow'
        
        return ModelConfig(
            model_provider=model_provider,
            model_info=model_info
        )
    
    @staticmethod
    def _create_workflow_cards(
        workflows: List[Dict[str, Any]]
    ) -> List["WorkflowCard"]:
        """
        创建 WorkflowCard 列表
        
        Args:
            workflows: 工作流配置列表
            
        Returns:
            WorkflowCard 列表
        """
        workflow_cards = []
        for wf in workflows:
            if isinstance(wf, dict):
                workflow_card = WorkflowCard(
                    id=wf.get("workflow_id", wf.get("id", "")),
                    version=wf.get("workflow_version", wf.get("version", "draft")),
                    name=wf.get("workflow_name", wf.get("name", "")),
                    description=wf.get("description", ""),
                    input_params=wf.get("input_params", {}),
                )
                workflow_cards.append(workflow_card)
        return workflow_cards
    
    @staticmethod
    def _create_plugin_schemas(
        plugins: List[Dict[str, Any]]
    ) -> List["PluginSchema"]:
        """
        创建 PluginSchema 列表
        
        Args:
            plugins: 插件配置列表
            
        Returns:
            PluginSchema 列表
        """
        plugin_schemas = []
        for plugin in plugins:
            if isinstance(plugin, dict):
                plugin_schema = PluginSchema(
                    id=plugin.get("plugin_id", plugin.get("id", "")),
                    version=plugin.get("plugin_version", plugin.get("version", "draft")),
                    name=plugin.get("plugin_name", plugin.get("name", "")),
                    description=plugin.get("description", ""),
                    inputs=plugin.get("inputs", {}),
                    plugin_id=plugin.get("plugin_id", plugin.get("id", "")),
                )
                plugin_schemas.append(plugin_schema)
        return plugin_schemas
    
    @staticmethod
    def _extract_model_config(
        config: Dict[str, Any]
    ) -> ModelConfig:
        """
        提取模型配置
        
        Args:
            config: agent 配置
            
        Returns:
            ModelConfig
        """
        model_data = config.get("model", {})
        
        # 处理不同的模型配置格式
        if "model_info" in model_data:
            model_info = model_data["model_info"]
            return ModelConfig(
                model_provider=model_data.get("model_provider", "OpenAI"),
                model_name=model_info.get("model_name", "gpt-4"),
                temperature=model_info.get("temperature", 0.7),
                top_p=model_info.get("top_p", 0.9),
                max_tokens=model_info.get("max_tokens", 2000),
                timeout=model_info.get("timeout", 300),
                api_key=model_info.get("api_key"),
                base_url=model_info.get("base_url")
            )
        else:
            return ModelConfig(
                model_provider=model_data.get("model_provider", "OpenAI"),
                model_name=model_data.get("model_name", "gpt-4"),
                temperature=model_data.get("temperature", 0.7),
                top_p=model_data.get("top_p", 0.9),
                max_tokens=model_data.get("max_tokens", 2000),
                timeout=model_data.get("timeout", 300),
                api_key=model_data.get("api_key"),
                base_url=model_data.get("base_url")
            )
    
    @staticmethod
    def _extract_tools(
        config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        提取工具配置
        
        Args:
            config: agent 配置
            
        Returns:
            工具配置列表
        """
        tools = []
        
        # 从 plugins 提取工具
        plugins = config.get("plugins", [])
        for plugin in plugins:
            if isinstance(plugin, dict):
                tools.append({
                    "type": "plugin",
                    "name": plugin.get("plugin_name", ""),
                    "id": plugin.get("plugin_id", ""),
                    "config": plugin.get("config", {})
                })
        
        # 从 tools 字段提取
        if "tools" in config:
            for tool in config["tools"]:
                if isinstance(tool, dict):
                    tools.append(tool)
        
        return tools
    
    @staticmethod
    def _extract_memory_config(
        config: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        提取记忆配置
        
        Args:
            config: agent 配置
            
        Returns:
            记忆配置或 None
        """
        memory = config.get("memory")
        if not memory:
            return None
        
        if isinstance(memory, dict):
            return {
                "enabled": memory.get("enabled", True),
                "type": memory.get("type", "conversation"),
                "max_turns": memory.get("max_turns", 10),
                "storage": memory.get("storage", "local")
            }
        
        return {"enabled": True, "type": "conversation"}
    
    @staticmethod
    def convert_to_agent_dl_config(
        agent_config: Dict[str, Any],
        workflows: Optional[List[Any]] = None,
        plugins: Optional[List[Any]] = None,
        knowledge_bases: Optional[List[Any]] = None
    ) -> AgentDLConfig:
        """
        转换为 AgentDLConfig
        
        Args:
            agent_config: agent 配置
            workflows: 工作流列表
            plugins: 插件列表
            knowledge_bases: 知识库列表
            
        Returns:
            AgentDLConfig
        """
        base_config = ConfigAdapter.adapt(agent_config)
        
        dl_config = AgentDLConfig(
            agent_base=base_config,
            workflows=workflows or [],
            plugins=plugins or [],
            knowledge_bases=knowledge_bases or []
        )
        
        return dl_config
