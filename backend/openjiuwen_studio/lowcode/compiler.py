#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
Agent编译器 - Runtime SDK的主要入口
"""

from typing import Any, Dict, List, Optional, Union
from pathlib import Path
import json
import logging

from openjiuwen_studio.lowcode.loader import LowCodeAgentLoader
from openjiuwen_studio.lowcode.schemas import ModelOverride
from openjiuwen_studio.lowcode.config_adapter import ConfigAdapter

logger = logging.getLogger(__name__)

try:
    from openjiuwen.core.single_agent.base import BaseAgent as InvokableAgent
    from openjiuwen.core.single_agent.agents.react_agent import ReActAgent
    from openjiuwen.core.single_agent.schema.agent_card import AgentCard
    from openjiuwen.core.workflow.workflow import Workflow as InvokableWorkflow
    from openjiuwen_studio.core.executor.workflow.workflow import Workflow, IWorkflowLoader
    from openjiuwen_studio.core.executor.workflow.context import Context
    from openjiuwen_studio.core.executor.agent.agent_runner import AgentRunner
    from openjiuwen_studio.core.executor.plugin.plugin_mgr import PluginManager
    from openjiuwen_studio.core.common.dsl import Workflow as DlWorkflow
    from openjiuwen_studio.core.common.dsl import Component, Connection, ComponentType
    HAS_INVOKABLE_AGENT = True
except ImportError:
    InvokableAgent = None
    ReActAgent = None
    AgentCard = None
    InvokableWorkflow = None
    Workflow = None
    IWorkflowLoader = None
    Context = None
    AgentRunner = None
    PluginManager = None
    DlWorkflow = None
    Component = None
    Connection = None
    ComponentType = None
    HAS_INVOKABLE_AGENT = False


class ExportConfigWorkflowLoader(IWorkflowLoader):
    """
    从导出配置加载工作流的加载器
    
    用于 lowcode 模式，支持从导出的 JSON 配置中加载工作流，
    而不需要从数据库获取。
    """
    
    def __init__(
        self,
        workflows_data: List[Dict[str, Any]],
        model_resolver: Optional[Any] = None
    ):
        """
        初始化加载器
        
        Args:
            workflows_data: 导出配置中的工作流数据列表
            model_resolver: 模型解析器，用于解析工作流中的模型配置
        """
        self._workflows: Dict[str, Dict[str, Any]] = {}
        self._model_resolver = model_resolver
        
        for wf in workflows_data:
            wf_id = wf.get("workflow_id") or wf.get("id")
            wf_version = wf.get("workflow_version") or wf.get("version", "draft")
            key = f"{wf_id}_{wf_version}"
            self._workflows[key] = wf
        
        logger.info(f"ExportConfigWorkflowLoader initialized with {len(self._workflows)} workflows")
    
    def _convert_workflow_to_dl(self, workflow_data: Dict[str, Any]) -> "DlWorkflow":
        """
        将导出配置中的工作流数据转换为 DlWorkflow 格式
        
        Args:
            workflow_data: 导出配置中的工作流数据
            
        Returns:
            DlWorkflow 对象
        """
        schema_str = workflow_data.get("schema", "{}")
        if isinstance(schema_str, str):
            schema = json.loads(schema_str)
        else:
            schema = schema_str
        
        nodes = schema.get("nodes", [])
        edges = schema.get("edges", [])
        
        components = []
        start_id = []
        end_id = []
        
        for node in nodes:
            node_type = str(node.get("type", "0"))
            node_id = node.get("id", "")
            node_data = node.get("data", {})
            
            comp_type = self._map_node_type_to_component_type(node_type)
            
            if comp_type == ComponentType.COMPONENT_TYPE_START:
                start_id.append(node_id)
            elif comp_type == ComponentType.COMPONENT_TYPE_END:
                end_id.append(node_id)
            
            inputs = self._extract_node_inputs(node)
            configs = self._extract_node_configs(node, node_data)
            
            component = Component(
                id=node_id,
                type=comp_type,
                name=node_data.get("title", ""),
                inputs=inputs,
                configs=configs,
            )
            components.append(component)
        
        connections = []
        for edge in edges:
            source = edge.get("sourceNodeID", "")
            target = edge.get("targetNodeID", "")
            if source and target:
                connections.append(Connection(source=source, target=target))
        
        input_params = workflow_data.get("input_parameters", [])
        input_properties = {}
        input_requires = []
        for param in input_params:
            param_name = param.get("name", "")
            if param_name:
                input_properties[param_name] = {
                    "type": param.get("type", "string"),
                    "description": param.get("description", ""),
                    "default": param.get("default"),
                }
                if param.get("required"):
                    input_requires.append(param_name)
        
        inputs = {
            "type": "object",
            "properties": input_properties,
            "required": input_requires,
        }
        
        output_params = workflow_data.get("output_parameters", [])
        output_properties = {}
        for param in output_params:
            param_name = param.get("name", "")
            if param_name:
                output_properties[param_name] = {
                    "type": param.get("type", "string"),
                    "description": param.get("description", ""),
                }
        
        workflow_id = workflow_data.get("workflow_id") or workflow_data.get("id", "")
        workflow_version = workflow_data.get("workflow_version") or workflow_data.get("version", "draft")
        workflow_name = workflow_data.get("workflow_name") or workflow_data.get("name", "Unnamed Workflow")
        
        dl_workflow = DlWorkflow(
            id=workflow_id,
            version=workflow_version,
            name=workflow_name,
            description=workflow_data.get("desc", "") or workflow_data.get("description", ""),
            inputs=inputs,
            outputs=output_properties,
            start_id=start_id,
            end_id=end_id,
            components=components,
            connections=connections,
        )
        
        return dl_workflow
    
    def _map_node_type_to_component_type(self, node_type: str) -> "ComponentType":
        """
        将节点类型映射为组件类型
        
        Args:
            node_type: 节点类型字符串
            
        Returns:
            ComponentType 枚举值
        """
        type_mapping = {
            "1": ComponentType.COMPONENT_TYPE_START,
            "2": ComponentType.COMPONENT_TYPE_END,
            "3": ComponentType.COMPONENT_TYPE_LLM,
            "4": ComponentType.COMPONENT_TYPE_PLUGIN,
            "5": ComponentType.COMPONENT_TYPE_IF,
            "6": ComponentType.COMPONENT_TYPE_INTENT,
            "7": ComponentType.COMPONENT_TYPE_QUESTION,
            "8": ComponentType.COMPONENT_TYPE_LOOP,
            "9": ComponentType.COMPONENT_TYPE_CODE,
            "10": ComponentType.COMPONENT_TYPE_SUB_WORKFLOW,
            "11": ComponentType.COMPONENT_TYPE_VARIABLE_MERGE,
            "12": ComponentType.COMPONENT_TYPE_TEXT_EDITOR,
            "13": ComponentType.COMPONENT_TYPE_INPUT,
            "14": ComponentType.COMPONENT_TYPE_OUTPUT,
        }
        return type_mapping.get(node_type, ComponentType.COMPONENT_TYPE_EMPTY)
    
    def _extract_node_inputs(self, node: Dict[str, Any]) -> Dict[str, Any]:
        """
        提取节点的输入配置
        
        Args:
            node: 节点数据
            
        Returns:
            输入配置字典
        """
        node_data = node.get("data", {})
        inputs = node_data.get("inputs", {})
        node_type = str(node.get("type", "0"))
        
        if node_type == "1":
            outputs = node_data.get("outputs", {})
            if outputs:
                properties = outputs.get("properties", {})
                return {"properties": properties}
        
        return inputs if isinstance(inputs, dict) else {}
    
    def _extract_node_configs(self, node: Dict[str, Any], node_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        提取节点的配置
        
        Args:
            node: 节点数据
            node_data: 节点的 data 字段
            
        Returns:
            配置字典
        """
        configs = {}
        node_type = str(node.get("type", "0"))
        
        if node_type == "3":
            inputs = node_data.get("inputs", {})
            llm_param = inputs.get("llmParam", {})
            if llm_param:
                configs["llmParam"] = llm_param
        
        return configs
    
    async def get_flow(
        self,
        workflow_id: str,
        version: str,
        space_id: str,
        current_user: Dict[str, Any]
    ) -> "Workflow":
        """
        获取工作流实例
        
        Args:
            workflow_id: 工作流 ID
            version: 工作流版本
            space_id: 工作空间 ID
            current_user: 当前用户信息
            
        Returns:
            Workflow 实例
        """
        key = f"{workflow_id}_{version}"
        workflow_data = self._workflows.get(key)
        
        if not workflow_data:
            for wf_key, wf_data in self._workflows.items():
                if wf_key.startswith(f"{id}_"):
                    workflow_data = wf_data
                    break
        
        if not workflow_data:
            raise ValueError(f"Workflow not found: id={id}, version={version}")
        
        dl_workflow = self._convert_workflow_to_dl(workflow_data)
        
        workflow = Workflow(dl_workflow, space_id, current_user)
        
        logger.info(f"Loaded workflow from export config: {id}_{version}")
        return workflow
    
    async def get_compiled_workflow(
        self,
        context: "Context",
        workflow_id: str,
        version: str,
        space_id: str,
        current_user: Dict[str, Any]
    ) -> "InvokableWorkflow":
        """
        获取已编译的工作流实例
        
        Args:
            context: 执行上下文
            workflow_id: 工作流 ID
            version: 工作流版本
            space_id: 工作空间 ID
            current_user: 当前用户信息
            
        Returns:
            已编译的 InvokableWorkflow 实例
        """
        workflow = await self.get_flow(workflow_id, version, space_id, current_user)
        compiled = await workflow.compile(context, self)
        return compiled


class AgentCompiler:
    """
    Agent编译器 - Runtime SDK的主要入口

    使用示例:
        # 方式一：直接编译为可执行的Agent实例
        from openjiuwen_studio.lowcode import AgentCompiler

        compiler = AgentCompiler()
        agent = await compiler.compile(
            config=agent_config,
            current_user={"user_id": "system"}
        )
        # agent 是可执行的 InvokableAgent 实例

        # 方式二：仅编译配置（不创建实例）
        result = await compiler.compile_config(
            config=agent_config,
            current_user={"user_id": "system"}
        )
        # result 包含 config, workflows, plugins, knowledge_bases, agent_config
    """

    def __init__(
        self,
        workflow_runner: Optional[Any] = None,
        plugin_manager: Optional[Any] = None
    ):
        """
        初始化Agent编译器

        Args:
            workflow_runner: 工作流运行器
            plugin_manager: 插件管理器
        """
        self.loader = LowCodeAgentLoader(
            workflow_runner=workflow_runner,
            plugin_manager=plugin_manager
        )
        logger.info("AgentCompiler initialized")

    async def compile(
        self,
        config: Dict[str, Any],
        current_user: Optional[Dict] = None,
        space_id: Optional[str] = None
    ) -> "InvokableAgent":
        """
        将Agent配置编译为可执行的Agent实例

        Args:
            config: Agent配置（AgentExportData格式）
            current_user: 当前用户信息
            space_id: 工作空间ID，默认为 "default"

        Returns:
            InvokableAgent: 可执行的Agent实例

        Raises:
            ValueError: 如果配置无效
            RuntimeError: 如果编译失败
            ImportError: 如果无法导入必要的Agent运行时组件
        """
        if not HAS_INVOKABLE_AGENT:
            raise ImportError(
                "Cannot import InvokableAgent from openjiuwen.core.single_agent.base. "
                "Please ensure openjiuwen is installed correctly."
            )

        try:
            logger.info("Starting agent compilation to InvokableAgent")

            compiled_result = await self.compile_config(
                config=config,
                current_user=current_user
            )

            dependencies = config.get("dependencies", {})
            workflows_data = dependencies.get("workflows", [])

            if workflows_data:
                workflow_loader = ExportConfigWorkflowLoader(workflows_data)
                
                plugin_mgr = self.loader.dep_processor.plugin_manager or PluginManager()
                
                agent_runner = AgentRunner(
                    flow_mgr=workflow_loader,
                    plugin_mgr=plugin_mgr
                )
            else:
                agent_runner = AgentRunner(
                    flow_mgr=self.loader.dep_processor.workflow_runner,
                    plugin_mgr=self.loader.dep_processor.plugin_manager
                )

            agent_config = compiled_result['agent_config']
            adapted_config = ConfigAdapter.adapt(agent_config)

            actual_space_id = space_id or (current_user.get("space_id") if current_user else "default")
            actual_user = current_user or {"user_id": "system"}

            invokable_agent = await agent_runner.create_new_agent(
                agent_config=adapted_config,
                space_id=actual_space_id,
                current_user=actual_user
            )

            logger.info("Agent compilation to InvokableAgent completed successfully")
            return invokable_agent

        except ValueError as e:
            logger.error(f"Invalid configuration: {e}")
            raise
        except Exception as e:
            logger.error(f"Compilation failed: {e}")
            raise RuntimeError(f"Failed to compile agent: {e}") from e

    async def compile_config(
        self,
        config: Dict[str, Any],
        current_user: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        将Agent配置编译为配置字典（不创建Agent实例）

        Args:
            config: Agent配置（AgentExportData格式）
            current_user: 当前用户信息

        Returns:
            包含配置的字典:
            {
                "config": AgentDLConfig,
                "workflows": List[Workflow],
                "plugins": List[Tool],
                "knowledge_bases": List[Dict],
                "agent_config": Dict
            }

        Raises:
            ValueError: 如果配置无效
            RuntimeError: 如果编译失败
        """
        try:
            logger.info("Starting agent configuration compilation")

            result = await self.loader.load_from_export_data(
                export_data=config,
                current_user=current_user
            )

            logger.info("Agent configuration compilation completed successfully")
            return result

        except ValueError as e:
            logger.error(f"Invalid configuration: {e}")
            raise
        except Exception as e:
            logger.error(f"Compilation failed: {e}")
            raise RuntimeError(f"Failed to compile agent configuration: {e}") from e

    async def compile_from_file(
        self,
        config_path: Union[str, Path],
        current_user: Optional[Dict] = None,
        space_id: Optional[str] = None
    ) -> "InvokableAgent":
        """
        从配置文件编译Agent实例

        Args:
            config_path: 配置文件路径（JSON或ZIP）
            current_user: 当前用户信息
            space_id: 工作空间ID，默认为 "default"

        Returns:
            InvokableAgent: 可执行的Agent实例

        Raises:
            FileNotFoundError: 如果文件不存在
            ValueError: 如果配置无效
            RuntimeError: 如果编译失败
        """
        if not HAS_INVOKABLE_AGENT:
            raise ImportError(
                "Cannot import InvokableAgent from openjiuwen.core.single_agent.base. "
                "Please ensure openjiuwen is installed correctly."
            )

        try:
            logger.info(f"Compiling agent from file to InvokableAgent: {config_path}")

            compiled_result = await self.compile_from_file_config(
                config_path=config_path,
                current_user=current_user
            )

            export_data = compiled_result.get('export_data', {})
            dependencies = export_data.get("dependencies", {})
            workflows_data = dependencies.get("workflows", [])

            if workflows_data:
                workflow_loader = ExportConfigWorkflowLoader(workflows_data)
                
                plugin_mgr = self.loader.dep_processor.plugin_manager or PluginManager()
                
                agent_runner = AgentRunner(
                    flow_mgr=workflow_loader,
                    plugin_mgr=plugin_mgr
                )
            else:
                agent_runner = AgentRunner(
                    flow_mgr=self.loader.dep_processor.workflow_runner,
                    plugin_mgr=self.loader.dep_processor.plugin_manager
                )

            agent_config = compiled_result['agent_config']
            adapted_config = ConfigAdapter.adapt(agent_config)

            actual_space_id = space_id or (current_user.get("space_id") if current_user else "default")
            actual_user = current_user or {"user_id": "system"}

            invokable_agent = await agent_runner.create_new_agent(
                agent_config=adapted_config,
                space_id=actual_space_id,
                current_user=actual_user
            )

            logger.info("Agent compilation from file to InvokableAgent completed successfully")
            return invokable_agent

        except FileNotFoundError:
            logger.error(f"Configuration file not found: {config_path}")
            raise
        except Exception as e:
            logger.error(f"Failed to compile from file: {e}")
            raise RuntimeError(f"Failed to compile agent from file: {e}") from e

    async def compile_from_file_config(
        self,
        config_path: Union[str, Path],
        current_user: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        从配置文件编译Agent配置（不创建实例）

        Args:
            config_path: 配置文件路径（JSON或ZIP）
            current_user: 当前用户信息

        Returns:
            包含配置的字典

        Raises:
            FileNotFoundError: 如果文件不存在
            ValueError: 如果配置无效
            RuntimeError: 如果编译失败
        """
        try:
            logger.info(f"Compiling agent configuration from file: {config_path}")

            result = await self.loader.load_from_config_file(
                config_path=config_path,
                current_user=current_user
            )

            logger.info("Agent configuration compilation from file completed successfully")
            return result

        except FileNotFoundError:
            logger.error(f"Configuration file not found: {config_path}")
            raise
        except Exception as e:
            logger.error(f"Failed to compile configuration from file: {e}")
            raise RuntimeError(f"Failed to compile agent configuration from file: {e}") from e

    async def compile_with_overrides(
        self,
        config: Dict[str, Any],
        model_overrides: Dict[str, ModelOverride],
        current_user: Optional[Dict] = None,
        space_id: Optional[str] = None
    ) -> "InvokableAgent":
        """
        使用模型覆盖配置编译Agent实例

        Args:
            config: Agent配置
            model_overrides: 模型覆盖配置（如API Key）
            current_user: 当前用户信息
            space_id: 工作空间ID，默认为 "default"

        Returns:
            InvokableAgent: 可执行的Agent实例
        """
        if not HAS_INVOKABLE_AGENT:
            raise ImportError(
                "Cannot import InvokableAgent from openjiuwen.core.single_agent.base. "
                "Please ensure openjiuwen is installed correctly."
            )

        try:
            logger.info("Starting agent compilation with model overrides to InvokableAgent")

            compiled_result = await self.compile_with_overrides_config(
                config=config,
                model_overrides=model_overrides,
                current_user=current_user
            )

            dependencies = config.get("dependencies", {})
            workflows_data = dependencies.get("workflows", [])

            if workflows_data:
                workflow_loader = ExportConfigWorkflowLoader(workflows_data)
                
                plugin_mgr = self.loader.dep_processor.plugin_manager or PluginManager()
                
                agent_runner = AgentRunner(
                    flow_mgr=workflow_loader,
                    plugin_mgr=plugin_mgr
                )
            else:
                agent_runner = AgentRunner(
                    flow_mgr=self.loader.dep_processor.workflow_runner,
                    plugin_mgr=self.loader.dep_processor.plugin_manager
                )

            agent_config = compiled_result['agent_config']
            adapted_config = ConfigAdapter.adapt(agent_config)

            actual_space_id = space_id or (current_user.get("space_id") if current_user else "default")
            actual_user = current_user or {"user_id": "system"}

            invokable_agent = await agent_runner.create_new_agent(
                agent_config=adapted_config,
                space_id=actual_space_id,
                current_user=actual_user
            )

            logger.info("Agent compilation with overrides to InvokableAgent completed successfully")
            return invokable_agent

        except Exception as e:
            logger.error(f"Compilation with overrides failed: {e}")
            raise RuntimeError(f"Failed to compile agent with overrides: {e}") from e

    async def compile_with_overrides_config(
        self,
        config: Dict[str, Any],
        model_overrides: Dict[str, ModelOverride],
        current_user: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        使用模型覆盖配置编译Agent配置（不创建实例）

        Args:
            config: Agent配置
            model_overrides: 模型覆盖配置（如API Key）
            current_user: 当前用户信息

        Returns:
            包含配置的字典
        """
        try:
            logger.info("Starting agent configuration compilation with model overrides")

            result = await self.loader.load_from_export_data(
                export_data=config,
                model_overrides=model_overrides,
                current_user=current_user
            )

            logger.info("Agent configuration compilation with overrides completed successfully")
            return result

        except Exception as e:
            logger.error(f"Configuration compilation with overrides failed: {e}")
            raise RuntimeError(f"Failed to compile agent configuration with overrides: {e}") from e

    async def validate(
        self,
        config: Dict[str, Any],
        model_overrides: Optional[Dict[str, ModelOverride]] = None
    ) -> Dict[str, Any]:
        """
        验证Agent配置

        Args:
            config: Agent配置
            model_overrides: 模型覆盖配置

        Returns:
            验证结果
        """
        try:
            logger.info("Validating agent configuration")

            result = await self.loader.validate_export_data(
                export_data=config,
                model_overrides=model_overrides
            )

            return {
                "valid": result.valid,
                "checks": result.checks,
                "errors": [
                    {
                        "field": e.field,
                        "message": e.message,
                        "severity": e.severity
                    }
                    for e in result.errors
                ]
            }

        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return {
                "valid": False,
                "checks": {},
                "errors": [
                    {
                        "field": "general",
                        "message": str(e),
                        "severity": "error"
                    }
                ]
            }

    async def compile_for_runtime(
        self,
        config: Dict[str, Any],
        model_overrides: Optional[Dict[str, ModelOverride]] = None,
        current_user: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        编译配置用于 Runtime 环境（不依赖数据库）

        此方法专为 Runtime 环境设计，返回可直接用于创建 Agent 实例的配置。
        不依赖 AgentRunner，因此不需要数据库配置。

        Args:
            config: Agent配置（AgentExportData格式）
            model_overrides: 模型覆盖配置（如API Key）
            current_user: 当前用户信息

        Returns:
            Dict 包含:
            {
                "agent_card": AgentCard,
                "runtime_config": ReActAgentConfig,
                "agent_config": Dict
            }

        使用示例:
            from openjiuwen.core.single_agent.agents.react_agent import ReActAgent
            from openjiuwen_studio.lowcode import AgentCompiler

            compiler = AgentCompiler()
            result = await compiler.compile_for_runtime(
                config=export_data,
                model_overrides={"147": ModelOverride(...)}
            )

            agent = ReActAgent(card=result["agent_card"])
            agent.configure(result["runtime_config"])
        """
        try:
            logger.info("Starting agent compilation for runtime environment")

            compiled_result = await self.compile_with_overrides_config(
                config=config,
                model_overrides=model_overrides or {},
                current_user=current_user
            )

            agent_config = compiled_result['agent_config']

            agent_card = AgentCard(
                id=agent_config.get("agent_id", ""),
                name=agent_config.get("agent_name", "Agent"),
                description=agent_config.get("description", ""),
                version=agent_config.get("agent_version", "draft"),
            )

            runtime_config = ConfigAdapter.adapt_to_runtime_config(agent_config)

            logger.info("Agent compilation for runtime completed successfully")

            return {
                "agent_card": agent_card,
                "runtime_config": runtime_config,
                "agent_config": agent_config,
            }

        except Exception as e:
            logger.error(f"Runtime compilation failed: {e}")
            raise RuntimeError(f"Failed to compile agent for runtime: {e}") from e
