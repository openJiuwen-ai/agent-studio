#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from typing import Dict, List

from openjiuwen.core.common.logging import logger
from openjiuwen_studio.core.common import dsl
from openjiuwen_studio.core.manager.convertor.components.common import input_params_convert
from openjiuwen_studio.core.common.dsl import ComponentType
from openjiuwen_studio.core.manager.convertor.components.llm import get_model_config
from openjiuwen_studio.schemas.node import Node, Outputs, BaseValue
from openjiuwen_studio.schemas.model_config import ModelParameters


def _output_and_extract_field_convert(outputs: Outputs):
    result: List[dsl.FieldInfo] = []
    output: Dict[str, str] = {}
    if outputs.type == "object":
        for key, value in outputs.properties.items():
            base_value = BaseValue(**value)
            if key == "user_response":
                output[key] = "${" + key + "}"
                continue

            required = False
            if key in outputs.required:
                required = True
            field_info = dsl.FieldInfo(
                field_name=key,
                description=base_value.description,
                cn_field_name="",
                default_value=base_value.default,
                required=required,
                type=value.get("type"),
            )
            result.append(field_info)

    return output, result


def questioner_convert(node: Node, space_id: str) -> dsl.Component:
    try:
        data = node.data
        inputs = data.inputs
        if inputs is None:
            raise ValueError("inputs is none")
        input_parameters = inputs.input_parameters
        if input_parameters is None:
            raise ValueError("input_parameters is empty")

        converted_inputs = input_params_convert(input_parameters)

        data_outputs = data.outputs
        if data_outputs is None:
            raise ValueError("outputs is none")
        converted_outputs, converted_fields = _output_and_extract_field_convert(data_outputs)
        if not converted_outputs:
            raise ValueError("code output is empty")

        llm_params = inputs.llm_param
        if llm_params is None:
            raise ValueError("llm_param is none")

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

        questioner_configs = dsl.QuestionerConfig(
            model=model,
            field_names=converted_fields,
            max_response=inputs.max_response,
            with_chat_history=inputs.enable_history,
        )

        model_id = int(llm_params.model.id)
        model_config = get_model_config(model_id, space_id)
        request_config.model_name = llm_params.model.type
        model_client_config.api_key = model_config.api_key
        model_client_config.api_base = model_config.base_url
        model_client_config.timeout = model_config.timeout
        model_client_config.client_provider = model_config.provider

        # 从模型配置中读取temperature和top_p参数
        logger.info(
            f"[QUESTIONER_CONVERT] Reading model config for "
            f"model_id={model_id}, space_id={space_id}"
        )
        logger.info(
            f"[QUESTIONER_CONVERT] Model config parameters type: "
            f"{type(model_config.parameters)}, value: {model_config.parameters}"
        )
        
        if model_config.parameters:
            if isinstance(model_config.parameters, dict):
                # 如果parameters是字典，使用ModelParameters解析
                model_params = ModelParameters(**model_config.parameters)
            else:
                # 如果已经是ModelParameters对象
                model_params = model_config.parameters
            
            request_config.temperature = model_params.temperature
            request_config.top_p = model_params.top_p
            logger.info(
                f"[QUESTIONER_CONVERT] Set temperature={request_config.temperature}, "
                f"top_p={request_config.top_p} from model config"
            )
        else:
            logger.warning(
                f"[QUESTIONER_CONVERT] Model config has no parameters, "
                f"using defaults: temperature=0.7, top_p=0.9"
            )

        return dsl.Component(
            id=getattr(node, 'id', ""),
            type=ComponentType.COMPONENT_TYPE_QUESTION,
            type_version="1.0.0",
            inputs=converted_inputs,
            outputs=converted_outputs,
            configs=questioner_configs.model_dump(),
            name=data.title
        )
    except Exception as e:
        raise RuntimeError(f"Failed to convert questioner node: {str(e)}") from e
