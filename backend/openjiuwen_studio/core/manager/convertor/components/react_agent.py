#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from typing import Any, Dict

from openjiuwen_studio.core.common import dsl
from openjiuwen_studio.core.common.dsl import ComponentType
from openjiuwen_studio.core.database import SessionLocal
from openjiuwen_studio.core.exceptions import ModelApiKeyDecryptError
from openjiuwen_studio.core.manager.convertor.components.common import outputs_convert, input_params_convert
from openjiuwen_studio.core.manager.model_manager.managers import ModelConfigManager
from openjiuwen_studio.core.manager.model_manager.utils import SecurityUtils
from openjiuwen_studio.models.model_config import ModelConfig
from openjiuwen_studio.schemas.node import Node
from openjiuwen_studio.schemas.model_config import ModelParameters


def get_model_config(model_id: int, space_id: str) -> ModelConfig:
    """Get model configuration from database and decrypt API key"""
    db = SessionLocal()
    manager = ModelConfigManager(db)
    model = manager.get_config_by_id(model_id, space_id)
    if model.api_key:
        try:
            model.api_key = SecurityUtils().decrypt_api_key(model.api_key)
        except Exception as e:
            raise ModelApiKeyDecryptError(f"API key decryption failed: {str(e)}") from e
    return model


def react_agent_convert(node: Node, space_id: str) -> dsl.Component:
    """Convert React Agent node to DSL Component"""
    try:
        data = node.data
        inputs = data.inputs
        if inputs is None:
            raise ValueError("react_agent_convert inputs is none")

        # Convert input parameters
        input_parameters = inputs.input_parameters
        if input_parameters is None:
            raise ValueError("react_agent_convert input_parameters is empty")
        converted_inputs = input_params_convert(input_parameters)

        # Convert outputs
        data_outputs = data.outputs
        if data_outputs is None:
            raise ValueError("react_agent_convert outputs is none")
        converted_outputs = outputs_convert(data_outputs)

        # Get LLM parameters
        llm_params = inputs.llm_param
        if llm_params is None:
            raise ValueError("llm_param is none")

        # Build model configuration
        model_client_config = dsl.ModelClientConfig(
            client_provider="",
            api_key="",
            api_base="",
            timeout=30
        )
        request_config = dsl.ModelRequestConfig(
            model_name="",
            temperature=0.7,
            top_p=0.9
        )

        model = dsl.ModelConfig(
            model_client_config=model_client_config,
            request_config=request_config
        )

        # Get model configuration from database
        model_id = int(llm_params.model.id)
        model_config = get_model_config(model_id, space_id)
        request_config.model_name = llm_params.model.type
        model_client_config.api_key = model_config.api_key
        model_client_config.api_base = model_config.base_url
        model_client_config.timeout = model_config.timeout
        model_client_config.client_provider = model_config.provider

        # Parse model parameters (temperature, top_p)
        if model_config.parameters:
            if isinstance(model_config.parameters, dict):
                model_params = ModelParameters(**model_config.parameters)
            else:
                model_params = model_config.parameters

            request_config.temperature = model_params.temperature
            request_config.top_p = model_params.top_p

        # Parse prompt templates
        prompt_template = [
            {"role": "system", "content": llm_params.system_prompt.content},
            {"role": "user", "content": llm_params.prompt.content},
        ]

        # Extract max_iterations (default to 5 if not provided)
        max_iterations = getattr(data, 'max_iterations', 5)

        # Extract skills (plugins and workflows)
        skills_param = getattr(inputs, 'skills_param', None)
        selected_plugins = []
        selected_workflows = []

        if skills_param:
            # Extract plugin IDs
            plugins = getattr(skills_param, 'plugins', [])
            if plugins:
                selected_plugins = [plugin.get('id', '') for plugin in plugins if isinstance(plugin, dict)]

            # Extract workflow IDs
            workflows = getattr(skills_param, 'workflows', [])
            if workflows:
                selected_workflows = [workflow.get('id', '') for workflow in workflows if isinstance(workflow, dict)]

        # Build ReactAgentConfig
        react_agent_config = dsl.ReactAgentConfig(
            model=model,
            prompt_template=prompt_template,
            prompt_template_name="",  # Can be customized later
            max_iterations=max_iterations,
            mem_scope_id=None,  # Can be added later for memory support
            sys_operation_id=None,  # Can be added later
            selected_plugins=selected_plugins,
            selected_workflows=selected_workflows,
            max_context_message_num=None,  # Can be added later
            default_window_round_num=None,  # Can be added later
        )

        # Build and return the DSL Component
        react_agent_component = dsl.Component(
            id=getattr(node, 'id', ""),
            type=ComponentType.COMPONENT_TYPE_REACT_AGENT,
            type_version="1.0.0",
            inputs=converted_inputs,
            outputs=converted_outputs,
            configs=react_agent_config.model_dump(),
            name=data.title
        )

        return react_agent_component

    except Exception as e:
        raise RuntimeError(f"Failed to convert React Agent node: {str(e)}") from e
