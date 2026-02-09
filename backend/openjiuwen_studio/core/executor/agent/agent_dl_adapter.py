#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from typing import List, Union

from openjiuwen_studio.core.common.dsl import Agent as AgentDL, AgentType, ReactAgent as ReactAgentDL, \
    WorkflowAgent as WorkflowAgentDL, PluginSchema as PluginSchemaDL, WorkflowSchema as WorkflowSchemaDL
from openjiuwen.core.common.constants.enums import ControllerType
from openjiuwen.core.application.llm_agent import ReActAgentConfig, ConstrainConfig
from openjiuwen.core.single_agent.legacy import WorkflowAgentConfig, DefaultResponse, WorkflowSchema, PluginSchema
from openjiuwen.core.foundation.llm import BaseModelInfo, ModelConfig
from openjiuwen.core.memory.config.config import AgentMemoryConfig
from openjiuwen.core.common import Param
from openjiuwen.core.workflow import WorkflowCard


VARIABLE_PROMPT_SYS = """
以下列出的是用户历史保存的记忆变量\n{{sys_memory_variables}}
"""

LONG_TERM_PROMPT = """
以下内容源自用户与你的过往交流，可在需要时帮助提升回答的完整性与亲切感：
- 用户提供的信息：用户在对话中主动输入的内容，如与其他信息冲突，应优先采用。
- 用户画像信息：用户的个人资料及偏好,标注了记录日期和时间
注意事项：
- 不使用隐私或敏感信息，除非用户主动提及。
- 避免生硬或冗长的历史信息插入，保持简洁自然。
- 默认主语为用户\n{{sys_long_term_memory}}
"""


def _plugin_schema_adapter(plugin_dls: List[PluginSchemaDL]) -> List[PluginSchema]:
    plugin_schemas = []
    for plugin_dl in plugin_dls:
        plugin_schema = PluginSchema(
            id=plugin_dl.id,
            version=plugin_dl.version,
            name=plugin_dl.id,
            description=plugin_dl.description,
            inputs=plugin_dl.inputs,
            plugin_id=plugin_dl.plugin_id,
        )
        plugin_schemas.append(plugin_schema)
    return plugin_schemas


def _workflow_schema_adapter(workflow_dls: List[WorkflowSchemaDL]) -> List[WorkflowCard]:
    workflow_cards = []
    for workflow_dl in workflow_dls:
        workflow_card = WorkflowCard(
            id=workflow_dl.id,
            version=workflow_dl.version,
            name=workflow_dl.name,
            description=workflow_dl.description,
            input_params=workflow_dl.inputs,
        )
        workflow_cards.append(workflow_card)
    return workflow_cards


class AgentDlAdapter:
    @staticmethod
    def _parse_base_agent_config(agent_dl: AgentDL) -> Union[ReActAgentConfig, WorkflowAgentConfig]:
        """
        解析基础AgentConfig字段，根据agent_type直接返回对应类型

        Args:
            agent_dl: AgentDL对象，支持ReactAgentDL和WorkflowAgentDL

        Returns:
            Union[ReActAgentConfig, WorkflowAgentConfig]: 直接返回对应类型的配置对象
        """
        if agent_dl.agent_type == AgentType.ReAct:
            agent_config = ReActAgentConfig()
        else:
            agent_config = WorkflowAgentConfig()

        # 基础Agent字段
        agent_config.id = agent_dl.id
        agent_config.version = agent_dl.version
        agent_config.description = agent_dl.description

        # 控制器类型
        if agent_dl.agent_type == AgentType.ReAct:
            agent_config.controller_type = ControllerType.ReActController
        elif agent_dl.agent_type == AgentType.Workflow:
            agent_config.controller_type = ControllerType.WorkflowController

        # 绑定的工作流
        agent_config.workflows = _workflow_schema_adapter(agent_dl.workflows)

        # 模型配置
        if agent_dl.model and agent_dl.model.model_client_config:
            request_config = agent_dl.model.request_config
            model_info = BaseModelInfo(
                api_key=agent_dl.model.model_client_config.api_key,
                api_base=agent_dl.model.model_client_config.api_base,
                model=request_config.model_name if request_config else "",
                temperature=request_config.temperature if request_config else 0.7,
                top_p=request_config.top_p if request_config else 0.9,
                stream=request_config.stream if request_config else False,
                timeout=agent_dl.model.model_client_config.timeout
            )

            model_provider = agent_dl.model.model_client_config.client_provider
            # Normalize provider casing
            if model_provider.lower() == 'openai':
                model_provider = 'OpenAI'
            elif model_provider.lower() == 'siliconflow':
                model_provider = 'SiliconFlow'

            agent_config.model = ModelConfig(
                model_provider=model_provider,
                model_info=model_info
            )

        return agent_config

    @staticmethod
    def _parse_memory_config_to_react_agent_config(react_agent_config: ReActAgentConfig, react_agent_dl: ReactAgentDL):
        # 1.获取记忆的配置
        variable_config = react_agent_dl.configs.get("variable_config")
        if isinstance(variable_config, list):
            variable_list = variable_config
        else:
            variable_list = []
        react_agent_config.agent_memory_config = AgentMemoryConfig(
            mem_variables=[
                Param.string(var["name"], description=var["description"], required=False)
                for var in variable_list if var.get("enabled", False)
            ],
            enable_long_term_mem=react_agent_dl.configs.get("longterm_memory_config", False)
        )

        # 2.获取记忆库的id和对应的配置
        memory_base_dict = react_agent_dl.configs.get("memory_base")
        if not isinstance(memory_base_dict, dict):
            memory_base_dict = {}
        mdb_id = memory_base_dict.get("mdb_id", "")
        # 如果绑定了记忆库
        if mdb_id:
            react_agent_config.memory_scope_id = mdb_id

        # 3.拼接prompt
        if not react_agent_config.prompt_template:
            system_content = ""
            if react_agent_config.agent_memory_config.mem_variables:
                system_content += VARIABLE_PROMPT_SYS
            if react_agent_config.agent_memory_config.enable_long_term_mem:
                system_content += LONG_TERM_PROMPT
            if system_content != "":
                react_agent_config.prompt_template.append({
                    "role": "system",
                    "content": system_content
                })
        else:
            if react_agent_config.agent_memory_config.mem_variables:
                react_agent_config.prompt_template[0]["content"] += VARIABLE_PROMPT_SYS
            if react_agent_config.agent_memory_config.enable_long_term_mem:
                react_agent_config.prompt_template[0]["content"] += LONG_TERM_PROMPT

    @staticmethod
    def _parse_react_agent_config(agent_config: ReActAgentConfig, react_agent_dl: ReactAgentDL) -> ReActAgentConfig:
        """
        解析ReActAgentConfig独有的字段

        Args:
            agent_config: 已配置基础字段的ReActAgentConfig对象
            react_agent_dl: ReactAgentDL对象

        Returns:
            ReActAgentConfig: 包含完整字段的配置对象
        """
        # 直接在传入的agent_config上添加ReAct特有字段
        agent_config.prompt_template_name = react_agent_dl.prompt_template_name
        agent_config.prompt_template = react_agent_dl.prompt_template
        agent_config.prompt_template_name = react_agent_dl.prompt_template_name

        # 绑定的插件
        agent_config.plugins = _plugin_schema_adapter(react_agent_dl.plugins)

        # 约束配置
        agent_config.constrain = ConstrainConfig(
            reserved_max_chat_rounds=react_agent_dl.constrain.reserved_max_chat_rounds,
            max_iteration=react_agent_dl.constrain.max_iteration,
        )

        return agent_config

    @staticmethod
    def _dl_to_react_agent_config(agent_dl: ReactAgentDL) -> ReActAgentConfig:
        """
        将DL配置转换为ReActAgent配置

        Args:
            agent_dl: ReactAgentDL对象

        Returns:
            ReActAgentConfig: 完整的ReActAgent配置对象
        """
        # 1. 解析基础Agent配置
        agent_config = AgentDlAdapter._parse_base_agent_config(agent_dl)

        # 2. 解析ReAct特有配置
        react_agent_config = AgentDlAdapter._parse_react_agent_config(agent_config, agent_dl)

        # 3. 拼接记忆prompt到react_agent_config
        AgentDlAdapter._parse_memory_config_to_react_agent_config(react_agent_config, agent_dl)

        # 4. 配置完成

        return react_agent_config

    @staticmethod
    def _dl_to_workflow_agent_config(agent_dl: WorkflowAgentDL) -> WorkflowAgentConfig:
        # WorkflowAgentConfig暂时无独有配置，使用通用Agent配置
        workflow_agent_config = AgentDlAdapter._parse_base_agent_config(agent_dl)

        # 添加WorkflowAgent特有字段
        if hasattr(agent_dl, 'default_response'):
            # 设置默认值：如果未传入或为空字符串，使用默认响应
            if agent_dl.default_response and agent_dl.default_response.strip():
                default_response = agent_dl.default_response
            else:
                default_response = "抱歉，我无法理解您的问题，请换一种方式表达"
            workflow_agent_config.default_response = DefaultResponse(text=default_response)

        # 配置完成

        return workflow_agent_config

    @staticmethod
    def convert_to_agent_config(agent_dl_json: str) -> Union[ReActAgentConfig, WorkflowAgentConfig]:
        """
        将DL配置JSON字符串转换为Agent配置对象

        Args:
            agent_dl_json: Agent配置的JSON字符串

        Returns:
            Union[ReActAgentConfig, WorkflowAgentConfig]: 转换后的具体配置对象
        """
        agent_dl = AgentDL.model_validate_json(agent_dl_json)

        if agent_dl.agent_type == AgentType.ReAct:
            react_agent_dl = ReactAgentDL.model_validate_json(agent_dl_json)
            return AgentDlAdapter._dl_to_react_agent_config(react_agent_dl)
        elif agent_dl.agent_type == AgentType.Workflow:
            workflow_agent_dl = WorkflowAgentDL.model_validate_json(agent_dl_json)
            return AgentDlAdapter._dl_to_workflow_agent_config(workflow_agent_dl)
        else:
            raise ValueError(f"Unsupported agent type: {agent_dl.agent_type}")

    @staticmethod
    def get_knowledge_config(agent_dl_json: str):
        agent_dl = AgentDL.model_validate_json(agent_dl_json)
        kb_ids = []
        if agent_dl.knowledges:
            for kb in agent_dl.knowledges:
                kb_ids.append(kb.id)
        return kb_ids, agent_dl.kb_retrieval

    @staticmethod
    def get_memory_base_id(agent_dl_json: str):
        agent_dl = AgentDL.model_validate_json(agent_dl_json)
        memory_base_dict = agent_dl.configs.get("memory_base")
        if not isinstance(memory_base_dict, dict):
            memory_base_dict = {}
        mdb_id = memory_base_dict.get("mdb_id", "")
        return mdb_id
