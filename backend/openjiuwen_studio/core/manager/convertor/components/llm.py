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
from openjiuwen_studio.schemas.node import Node, Outputs, BaseValue
from openjiuwen_studio.schemas.model_config import ModelParameters

response_format_mapping = {
    "0": dsl.LLMResponseFormatType.Text,
    "1": dsl.LLMResponseFormatType.Markdown,
    "2": dsl.LLMResponseFormatType.Json,
}


def get_model_config(model_id: int, space_id: str) -> ModelConfig:
    db = SessionLocal()
    manager = ModelConfigManager(db)
    model = manager.get_config_by_id(model_id, space_id)
    if model.api_key:
        try:
            model.api_key = SecurityUtils().decrypt_api_key(model.api_key)
        except Exception as e:
            raise ModelApiKeyDecryptError(f"API key decryption failed: {str(e)}") from e
    return model


def _llm_output_config_object_convert(is_first: bool, outputs: Outputs):
    result: Dict[str, Any] = {}
    if outputs.type != "object":
        return result, []

    if outputs.properties is None:
        return result, []

    if is_first:
        for key, value in outputs.properties.items():
            base_value = BaseValue(**value)
            required = False
            if key in outputs.required:
                required = True
            if base_value.type == "object":
                properties, convert_required = _llm_output_config_object_convert(False, Outputs(**value))
                result[key] = {
                    "type": base_value.type,
                    "description": base_value.description,
                    "properties": properties,
                    "required": convert_required,
                }
            else:
                result[key] = {"type": base_value.type, "description": base_value.description, "required": required}
    else:
        for key, value in outputs.properties.items():
            base_value = BaseValue(**value)
            if base_value.type == "object":
                properties, required = _llm_output_config_object_convert(False, Outputs(**value))
                result[key] = {"type": base_value.type,
                               "description": base_value.description,
                               "properties": properties,
                               "required": required,
                               }
            else:
                result[key] = {"type": base_value.type, "description": base_value.description}
                result["required"] = outputs.required

    return result, outputs.required


def _llm_output_config_convert(outputs: Outputs) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    if outputs.type == "object":
        for key, value in outputs.properties.items():
            base_value = BaseValue(**value)
            required = False
            if key in outputs.required:
                required = True
            if base_value.type == "object":
                properties, _ = _llm_output_config_object_convert(True, Outputs(**value))
                result[key] = {
                    "type": base_value.type,
                    "description": base_value.description,
                    "properties": properties,
                    "required": required
                }
            elif base_value.type == "array":
                result[key] = {
                    "type": base_value.type,
                    "description": base_value.description,
                    "items": base_value.items,
                    "required": required
                }
            else:
                result[key] = {"type": base_value.type, "description": base_value.description, "required": required}

    return result


def llm_convert(node: Node, space_id: str) -> dsl.Component:
    try:
        data = node.data
        inputs = data.inputs
        if inputs is None:
            raise ValueError("llm_convert inputs is none")
        input_parameters = inputs.input_parameters
        if input_parameters is None:
            raise ValueError("llm_convert input_parameters is empty")

        converted_inputs = input_params_convert(input_parameters)

        data_outputs = data.outputs
        if data_outputs is None:
            raise ValueError("llm_convert outputs is none")
        converted_outputs = outputs_convert(data_outputs)

        llm_params = inputs.llm_param
        if llm_params is None:
            raise ValueError("llm_param is none")

        model_info = dsl.BaseModelInfo(
            model_name="",
            temperature=0.7,
            top_p=0.9,
            streaming=True,
            timeout=30.0
        )

        model = dsl.ModelConfig(
            model_provider="",
            model_info=model_info
        )

        llm_configs = dsl.LLMConfig(
            model=model,
            response_format_type=data.output_format,
            output_config=_llm_output_config_convert(data_outputs),
            template_content=[
                {"role": "system", "content": llm_params.system_prompt.content},
                {"role": "user", "content": llm_params.prompt.content},
            ],
            enable_history=inputs.enable_history,
        )

        model_id = int(llm_params.model.id)

        model_config = get_model_config(model_id, space_id)
        model_info.model_name = llm_params.model.type
        model_info.api_key = model_config.api_key
        model_info.api_base = model_config.base_url
        model_info.timeout = model_config.timeout
        model.model_provider = model_config.provider
        
        # 从模型配置中读取temperature和top_p参数
        if model_config.parameters:
            if isinstance(model_config.parameters, dict):
                # 如果parameters是字典，使用ModelParameters解析
                model_params = ModelParameters(**model_config.parameters)
            else:
                # 如果已经是ModelParameters对象
                model_params = model_config.parameters
            
            model_info.temperature = model_params.temperature
            model_info.top_p = model_params.top_p

        # 构建转换后的LLM组件配置
        llm_component = dsl.Component(
            id=getattr(node, 'id', ""),
            type=ComponentType.COMPONENT_TYPE_LLM,
            type_version="1.0.0",
            inputs=converted_inputs,
            outputs=converted_outputs,
            configs=llm_configs.model_dump(),
            name=data.title
        )
        return llm_component
    except Exception as e:
        raise RuntimeError(f"Failed to convert LLM node: {str(e)}") from e
