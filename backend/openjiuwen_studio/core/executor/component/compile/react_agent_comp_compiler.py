#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

from typing import Any, Dict
from openjiuwen.core.workflow.components.llm.react import ReActAgentComp, ReActAgentCompConfig
from openjiuwen.core.foundation.llm import ModelRequestConfig, ModelClientConfig, SystemMessage, UserMessage
from openjiuwen.core.context_engine import ContextEngineConfig

from openjiuwen_studio.core.common.dsl import ReactAgentConfig as ReactAgentConfigDL
from openjiuwen_studio.core.executor.component.compile.base_comp_compiler import BaseCompCompiler

client_provider_mapping = {
    'siliconflow': "SiliconFlow",
    'openai': "OpenAI",
}


def parse_model_config(comp_config_dict: Dict[str, Any]) -> tuple[ModelRequestConfig, ModelClientConfig, str]:
    """
    Parse model configuration and return ModelRequestConfig, ModelClientConfig, and model_id
    Args:
        comp_config_dict: React agent component configuration dictionary
    Returns:
        tuple: (model_request_config, model_client_config, model_id)
    """
    react_agent_config_dl = ReactAgentConfigDL.model_validate(comp_config_dict)
    base_model_request_config = react_agent_config_dl.model.request_config
    base_model_client_config = react_agent_config_dl.model.model_client_config

    # Create ModelRequestConfig
    model_request_config = ModelRequestConfig(
        model=base_model_request_config.model_name,
        temperature=base_model_request_config.temperature,
        top_p=base_model_request_config.top_p,
    )

    # Create ModelClientConfig
    model_client_config = ModelClientConfig(
        client_provider=client_provider_mapping.get(
            base_model_client_config.client_provider,
            base_model_client_config.client_provider
        ),
        api_key=base_model_client_config.api_key,
        api_base=base_model_client_config.api_base,
        timeout=base_model_client_config.timeout,
        max_retries=1,
        verify_ssl=False,
    )

    # model_id uses model_name
    model_id = base_model_request_config.model_name
    return model_request_config, model_client_config, model_id


def parse_template_content(template_content: list) -> tuple[SystemMessage, UserMessage]:
    """
    Parse system_prompt_template and user_prompt_template from template_content
    Args:
        template_content: Template content list, each element is {"role": "system"/"user", "content": "..."}
    Returns:
        tuple: (system_prompt_template, user_prompt_template)
    """
    system_prompt_template = None
    user_prompt_template = None
    if not template_content:
        return None, None

    for msg in template_content:
        if not isinstance(msg, dict):
            continue
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role == "system":
            system_prompt_template = SystemMessage(content=content)
        elif role == "user":
            user_prompt_template = UserMessage(content=content)
    return system_prompt_template, user_prompt_template


class ReactAgentCompCompiler(BaseCompCompiler):
    def __init__(self, react_agent_config_dict: Dict[str, Any]) -> None:
        super().__init__()
        self.config_dict = react_agent_config_dict
        self.config = ReactAgentConfigDL.model_validate(react_agent_config_dict)

    def compile(self) -> ReActAgentComp:
        """
        Compile the React Agent component configuration into a ReActAgentComp instance
        Returns:
            ReActAgentComp: The compiled React Agent workflow component
        """
        # Parse model configuration
        model_request_config, model_client_config, model_id = parse_model_config(self.config_dict)

        # Parse prompt templates
        system_prompt_template, user_prompt_template = parse_template_content(self.config.prompt_template)

        # Build context engine config
        context_engine_config = ContextEngineConfig(
            max_context_message_num=self.config.max_context_message_num or 200,
            default_window_round_num=self.config.default_window_round_num or 10
        )

        # Create ReActAgentCompConfig
        react_agent_workflow_config = ReActAgentCompConfig(
            mem_scope_id=self.config.mem_scope_id or "",
            model_name=model_id,
            model_provider=model_client_config.client_provider,
            api_key=model_client_config.api_key,
            api_base=model_client_config.api_base,
            prompt_template_name=self.config.prompt_template_name,
            prompt_template=self.config.prompt_template,
            max_iterations=self.config.max_iterations,
            model_client_config=model_client_config,
            model_config_obj=model_request_config,
            sys_operation_id=self.config.sys_operation_id,
            context_engine_config=context_engine_config,
        )

        # Create and return the ReActAgentComp component
        return ReActAgentComp(react_agent_workflow_config)
