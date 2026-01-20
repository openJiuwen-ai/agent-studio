#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

"""
Agent - Agent实例管理器

本模块负责Agent实例的创建、配置和编译，是Agent执行系统的核心组件。

主要功能：
1. Agent配置的加载和管理
2. Workflow组件的获取和编译
3. Plugin工具的获取和编译
4. Agent实例的创建和组件绑定
5. 支持ReAct和Workflow两种Agent类型

核心职责：
- 根据配置创建对应的Agent类型（ReActAgent或WorkflowAgent）
- 获取Agent所需的所有Workflow组件
- 获取Agent所需的所有Plugin工具
- 编译并绑定所有组件到Agent实例
"""

from typing import List, Dict, Any, Union

from openjiuwen.agent.config.react_config import ReActAgentConfig
from openjiuwen.agent.config.workflow_config import WorkflowAgentConfig
from openjiuwen.agent.llm_agent.llm_agent import LLMAgent
from openjiuwen.agent.workflow_agent.workflow_agent import WorkflowAgent
from openjiuwen.core.agent.agent import Agent as InvokableAgent
from openjiuwen.core.utils.tool.base import Tool
from openjiuwen.core.common.logging import logger

from openjiuwen_studio.core.executor.plugin.plugin_mgr import PluginManager
from openjiuwen_studio.core.executor.workflow.context import Context
from openjiuwen_studio.core.executor.workflow.workflow import Workflow
from openjiuwen_studio.core.executor.workflow.workflow_runner import WorkflowRunner
from openjiuwen_studio.core.common.dsl import EndConfig, ComponentType
from openjiuwen_studio.core.common.exceptions import JiuWenExecuteException
from openjiuwen_studio.core.common.status_code import StatusCode


class Agent:
    """
    Agent实例管理器

    负责管理Agent的完整生命周期，从配置加载到组件编译绑定。
    支持ReAct和Workflow两种Agent类型的创建和管理。

    Attributes:
        agent_config: Agent配置对象，包含类型、模型、插件等信息
        workflow_mgr: Workflow管理器，负责获取和编译Workflow组件
        plugin_mgr: 插件管理器，负责获取和编译Plugin工具
        plugins: Agent所需的插件工具列表
        workflows: Agent所需的工作流组件列表

    Example:
        # 创建Agent实例并编译
        agent = Agent(workflow_mgr, agent_config, plugin_mgr)
        invokable_agent = await agent.compile(space_id, current_user)
    """

    def __init__(
            self,
            workflow_mgr: WorkflowRunner,
            agent_config: Union[ReActAgentConfig, WorkflowAgentConfig],
            plugin_mgr: PluginManager
    ) -> None:
        """
        初始化Agent实例

        Args:
            workflow_mgr: Workflow运行管理器，负责处理Workflow组件的获取和编译
            agent_config: Agent配置对象 (ReActAgentConfig 或 WorkflowAgentConfig)，包含Agent的所有配置信息
            plugin_mgr: 插件管理器，负责处理Plugin工具的获取和编译
        """
        self.agent_config = agent_config
        self.workflow_mgr = workflow_mgr
        self.plugin_mgr = plugin_mgr
        # Agent所需的插件工具列表，在_fetch_from_mgr中填充
        self.plugins = []
        # Agent所需的工作流组件列表，在_fetch_from_mgr中填充
        self.workflows: [Workflow] = []

    async def _fetch_from_mgr(
            self,
            space_id: str,
            current_user: Dict[str, Any]
    ) -> None:
        """
        从管理服务获取Agent所需的组件（内部方法）

        根据Agent配置中的Workflow和Plugin定义，分别从相应的管理服务
        获取具体的组件实例。这是Agent编译前的必要步骤。

        Args:
            space_id: 工作空间ID，用于多租户隔离和权限控制
            current_user: 当前用户信息，包含身份验证和上下文信息

        Process:
            1. 遍历Agent配置中的所有Workflow Schema
            2. 通过WorkflowRunner获取对应的Workflow实例
            3. 遍历Agent配置中的所有Plugin Schema
            4. 通过PluginManager获取对应的Plugin实例
            5. 将获取的组件存储在实例变量中供编译使用

        Note:
            此方法是异步的，因为需要通过网络请求获取组件配置
        """
        logger.warning(f"Agent _fetch_from_mgr self.agent_config: {self.agent_config}")

        # 1. 获取所有Workflow组件
        for workflow_schema in self.agent_config.workflows:
            # 通过Workflow管理器获取具体的Workflow实例
            workflow_instance = await self.workflow_mgr.get_flow(
                workflow_schema.id,
                workflow_schema.version,
                space_id,
                current_user
            )

            self.workflows.append(workflow_instance)

        # 2. 获取所有Plugin工具 (仅ReActAgent需要)
        if isinstance(self.agent_config, ReActAgentConfig):
            for plugin_schema in self.agent_config.plugins:
                logger.warning(f"Agent _fetch_from_mgr plugin_schema: {plugin_schema}")
                # 通过Plugin管理器获取具体的Plugin工具实例
                plugin_tool = await self.plugin_mgr.get_tool(
                    plugin_schema.id,
                    space_id,
                    plugin_schema.plugin_id,
                    plugin_schema.version,
                    current_user
                )
                self.plugins.append(plugin_tool)

    async def compile(
            self,
            space_id: str,
            current_user: Dict[str, Any]
    ) -> InvokableAgent:
        """
        编译Agent实例，创建可执行的Agent对象

        首先从管理服务获取所需的Workflow和Plugin组件，然后根据Agent配置的类型
        创建对应的Agent实例，并将所有组件编译并绑定到Agent上。

        Args:
            space_id: 工作空间ID，用于多租户隔离和权限控制
            current_user: 当前用户信息，包含身份验证和上下文信息

        Returns:
            InvokableAgent: 编译完成的可执行Agent实例，可以直接进行推理执行

        Process:
            1. 从管理服务获取所有必需的组件（内部调用_fetch_from_mgr）
            2. 根据controller_type创建对应的基础Agent实例
               - ReActController: 创建ReActAgent
               - 其他: 创建WorkflowAgent
            3. 编译所有Workflow组件并绑定到Agent
            4. 编译所有Plugin工具并绑定到Agent
            5. 返回完整的可执行Agent实例

        Raises:
            Exception: 当组件编译失败时抛出异常
        """
        # 1. 从管理服务获取Agent所需的组件
        await self._fetch_from_mgr(space_id, current_user)

        # 2. 根据配置类型创建对应的Agent实例
        invokable_agent: InvokableAgent
        if isinstance(self.agent_config, ReActAgentConfig):
            # 创建ReAct Agent - 基于思考-行动模式的智能体
            invokable_agent = LLMAgent(self.agent_config)
        else:
            # 创建Workflow Agent - 基于预定义工作流的智能体
            invokable_agent = WorkflowAgent(self.agent_config)

        # 3. 编译并绑定所有Workflow组件
        from openjiuwen.core.agent.agent import workflow_provider

        def create_provider(wf: Workflow, mgr: WorkflowRunner):
            @workflow_provider(workflow_id=wf.id, workflow_version=wf.version,
                               workflow_name=wf.name, inputs=wf.inputs)
            async def provider():
                return await wf.compile(Context(), mgr)

            return provider

        # 预检查所有 workflow 配置
        for wf in self.workflows:
            self._precheck_workflow_before_compile(wf)

        providers = [create_provider(wf, self.workflow_mgr) for wf in self.workflows]
        invokable_agent.add_workflows(providers)

        # 4. 编译并绑定所有Plugin工具
        tools: List[Tool] = []
        for tool in self.plugins:
            # 编译单个Plugin工具
            compiled_tool = tool.compile()
            tools.append(compiled_tool)

        # 将所有编译后的工具绑定到Agent
        invokable_agent.add_tools(tools)

        # 5. 返回完整的可执行Agent实例
        return invokable_agent

    def _precheck_workflow_before_compile(self, workflow: Workflow) -> None:
        """
        在编译 workflow 之前进行预检查

        Args:
            workflow: 待检查的 Workflow 实例

        Raises:
            JiuWenExecuteException: 当发现配置错误时抛出异常
        """
        # 检查 workflow 中的 end 组件配置
        for component in workflow.dl_workflow.components:
            # 检查是否是 end 组件
            if component.type == ComponentType.COMPONENT_TYPE_END or component.type == ComponentType.COMPONENT_TYPE_OUTPUT:
                # 检查组件配置
                end_config = EndConfig.model_validate(component.configs)
                # 如果开启了 stream_output 但 response_template 为空，抛出异常
                if end_config.stream_output and (
                        not end_config.response_template or not end_config.response_template.strip()
                ):
                    raise JiuWenExecuteException(
                        error_code=StatusCode.WORKFLOW_RUNNER_ERROR.code,
                        message=StatusCode.WORKFLOW_RUNNER_ERROR.errmsg.format(
                                msg=str(f"workflow '{workflow.name}' end node stream_output is enabled "
                                        f"but response_template is empty")
                            )
                    )
