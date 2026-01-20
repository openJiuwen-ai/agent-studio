#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from typing import List

from openjiuwen_studio.core.common import dsl
from openjiuwen_studio.schemas.node import Node, Outputs, BaseValue
from openjiuwen_studio.core.common.dsl import ComponentType


def _input_config_convert(outputs: Outputs) -> dsl.UserInputsConfig:
    configs = dsl.UserInputsConfig()
    for key, value in outputs.properties.items():
        base_value = BaseValue(**value)
        required = False
        if key in outputs.required:
            required = True
        default = ""
        if isinstance(base_value.default, str):
            default = base_value.default
        configs.inputs.append(dsl.UserInputElem(
            input_name=key,
            description=base_value.description,
            type=base_value.type,
            required=required,
            default=default,
        ))
    return configs


def input_convert(node: Node) -> dsl.Component:
    try:
        data = node.data
        outputs = data.outputs
        if outputs is None:
            raise TypeError("outputs is none")

        configs = _input_config_convert(outputs)

        return dsl.Component(
            id=node.id,
            type=ComponentType.COMPONENT_TYPE_INPUT,
            type_version="1.0.0",
            configs=configs.model_dump(),
            description="",
            name=data.title
        )
    except Exception as e:
        raise ValueError(f"Failed to convert user input node: {str(e)}") from e
