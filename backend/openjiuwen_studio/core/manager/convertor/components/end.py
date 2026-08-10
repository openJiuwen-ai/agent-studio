#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from typing import List, Any

from openjiuwen_studio.core.common import dsl
from openjiuwen_studio.schemas.node import Node, NodeData
from openjiuwen_studio.core.manager.convertor.components.common import input_params_convert
from openjiuwen_studio.core.common.dsl import ComponentType
from openjiuwen_studio.core.manager.internal.workflow import InputElem


def end_outputs_convert(data: NodeData) -> list[dict[str, Any]]:
    """
    Convert end node data to output parameters list
    """
    inputs = data.inputs
    if inputs is None:
        raise TypeError("end node inputs is none")
    
    input_parameters = inputs.input_parameters
    if input_parameters is None:
        raise TypeError("end node input_parameters is none")

    outputs_res: list[dict[str, Any]] = []
    for key, value in input_parameters.items():
        outputs_res.append(InputElem(
            name=key,
            type=value.type,
            description=value.description,
            required=True,
        ).model_dump())
    
    return outputs_res


def end_convert(node: Node) -> dsl.Component:
    try:
        data = node.data
        inputs = data.inputs
        if inputs is None:
            raise TypeError("inputs is none")
        input_parameters = inputs.input_parameters
        if input_parameters is None:
            raise TypeError("input_parameters is none")

        convert_inputs = input_params_convert(input_parameters)

        content = inputs.content
        if content is None:
            configs = dsl.EndConfig(
                stream_output=False,
                response_template="",
            )
        else:
            # A plugin node may emit a non-string payload (dict / list / number).
            # Normalize it to a string so the End node's response_template stays
            # serializable and the second dialogue round loads correctly (#1282).
            raw_content = content.content
            response_template = raw_content if isinstance(raw_content, str) else str(raw_content or "")
            configs = dsl.EndConfig(
                stream_output=inputs.streaming,
                response_template=response_template,
            )

        end_node = dsl.Component(
            id=node.id,
            type=ComponentType.COMPONENT_TYPE_END,
            type_version="1.0.0",
            description="",
            configs=configs.model_dump(),
            inputs=convert_inputs,
            name=data.title
        )
        return end_node
    except Exception as e:
        raise RuntimeError(f"Failed to convert end node: {str(e)}") from e
