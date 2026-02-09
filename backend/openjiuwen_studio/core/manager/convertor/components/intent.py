#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from typing import List

from openjiuwen.core.common.logging import logger
from openjiuwen_studio.core.common import dsl
from openjiuwen_studio.core.common.dsl import ComponentType
from openjiuwen_studio.core.database import SessionLocal
from openjiuwen_studio.core.exceptions import ModelApiKeyDecryptError
from openjiuwen_studio.core.manager.convertor.components.common import input_params_convert, outputs_convert
from openjiuwen_studio.core.manager.model_manager.managers import ModelConfigManager
from openjiuwen_studio.core.manager.model_manager.utils import SecurityUtils
from openjiuwen_studio.schemas.model_config import ModelParameters
from openjiuwen_studio.schemas.node import Node, Inputs, Outputs, Edge

DEFAULT_USER_CONTENT = "\n        {{user_prompt}}\n\n        当前可供选择的功能分类如下：\n        {{category_info}}\n\n        用户与助手的对话历史： \n        {{chat_history}}\n\n        当前输入：{{input}}\n\n        请根据当前输入和对话历史分析并输出最适合的功能分类。输出格式为JSON：\n         {\"class\": \"分类xx\"}\n        如果没有合适的分类，请输出 {{default_class}}。\n"


def _intent_inputs_convert(inputs: Inputs) -> dict:
    if inputs is None:
        raise TypeError("inputs is none")

    input_parameters = inputs.input_parameters
    if input_parameters is None:
        raise TypeError("input_parameters is empty")

    converted_inputs = input_params_convert(input_parameters)
    logger.info(f"converted inputs: {converted_inputs}")

    return converted_inputs


def _intent_outputs_convert(outputs: Outputs) -> dict:
    if outputs is None:
        raise TypeError("outputs is none")

    converted_outputs = outputs_convert(outputs)
    logger.info(f"converted outputs: {converted_outputs}")

    return converted_outputs


def _intent_configs_model_convert(model_id: int, space_id: str) -> dsl.ModelConfig:
    db = SessionLocal()
    manager = ModelConfigManager(db)
    model = manager.get_config_by_id(model_id, space_id)

    if model.api_key:
        try:
            model.api_key = SecurityUtils().decrypt_api_key(model.api_key)
        except Exception as e:
            raise ModelApiKeyDecryptError(f"API key decryption failed: {str(e)}") from e

    param = ModelParameters(**model.parameters)

    return dsl.ModelConfig(
        model_client_config=dsl.ModelClientConfig(
            client_provider=model.provider,
            api_key=model.api_key,
            api_base=model.base_url,
            timeout=model.timeout
        ),
        request_config=dsl.ModelRequestConfig(
            model_name=model.model_type,
            temperature=param.temperature,
            top_p=param.top_p,
        )
    )


def _intent_configs_convert(inputs: Inputs, space_id: str) -> dict:
    if inputs is None:
        raise TypeError("inputs is none")

    llm_params = inputs.llm_param
    if llm_params is None:
        raise TypeError("llm_param is none")

    # 提取用户设置的 prompt
    user_prompt = ""
    if llm_params.prompt and llm_params.prompt.content:
        user_prompt = llm_params.prompt.content

    intents = inputs.intents
    category_list: list[str] = []
    category_name_list: list[str] = []
    index: int = 1
    for intent in intents:
        category_index = f"分类{index}"
        category_list.append(category_index)
        category_name_list.append(intent.name)
        index += 1

    model = _intent_configs_model_convert(int(llm_params.model.id), space_id)
    enable_history = inputs.enable_history

    converted_configs = dsl.IntentDetectionConfig(
        user_prompt=user_prompt,  # 添加 user_prompt 字段
        category_list=category_list,
        category_name_list=category_name_list,
        model=model,
        enable_history=enable_history,
    )

    return converted_configs.model_dump()


def intent_convert(node: Node, space_id: str) -> dsl.Component:
    try:
        data = node.data
        converted_inputs = _intent_inputs_convert(data.inputs)
        converted_outputs = _intent_outputs_convert(data.outputs)
        converted_configs = _intent_configs_convert(data.inputs, space_id)

        convert_branches: List[dsl.Branch] = []

        convert_branches.append(dsl.Branch(
            branch_id=data.inputs.default_intent
        ))
        for intent in data.inputs.intents:
            convert_branches.append(dsl.Branch(
                branch_id=intent.id
            ))

        return dsl.Component(
            id=node.id,
            name=data.title,
            type=ComponentType.COMPONENT_TYPE_INTENT,
            type_version="1.0.0",
            inputs=converted_inputs,
            outputs=converted_outputs,
            configs=converted_configs,
            branches=convert_branches,
        )
    except Exception as e:
        raise ValueError(f"Failed to convert intent node: {str(e)}") from e
