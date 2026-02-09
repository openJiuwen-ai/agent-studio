#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from typing import Any, Dict

from openjiuwen.core.common.logging import logger

from openjiuwen_studio.core.common import dsl
from openjiuwen_studio.core.common.dsl import ComponentType
from openjiuwen_studio.schemas.node import Node

from .common import input_params_convert, outputs_convert


def sub_workflow_convert(node: Node, space_id: str) -> dsl.Component:
    data = node.data
    
    sub_workflow_config = None
    if hasattr(data, 'configs') and data.configs and hasattr(data.configs, 'sub_workflow'):
        sub_workflow_config = data.configs.sub_workflow
    
    if not sub_workflow_config:
        logger.warning(f"Sub-workflow config is None for node {node.id}")
        raise TypeError("Sub-workflow config is None")

    converted_inputs = {}
    if hasattr(data, 'inputs') and data.inputs and hasattr(data.inputs, 'input_parameters'):
        converted_inputs = input_params_convert(data.inputs.input_parameters or {})
    
    converted_outputs = {}
    if hasattr(data, 'outputs') and data.outputs:
        converted_outputs = outputs_convert(data.outputs)
    
    # Create sub-workflow reference configuration as BaseInfo instance
    sub_workflow_info = dsl.BaseInfo(
        id=sub_workflow_config.workflow_id,
        version=sub_workflow_config.workflow_version,
        name=sub_workflow_config.workflow_name or "",
        description=sub_workflow_config.workflow_description or ""
    )
    
    # Create and return DSL component
    component = dsl.Component(
        id=node.id,
        type=ComponentType.COMPONENT_TYPE_SUB_WORKFLOW,
        type_version="1.0.0",
        inputs=converted_inputs,
        outputs=converted_outputs,
        configs={"sub_workflow_info": sub_workflow_info},
        name=data.title if hasattr(data, 'title') else ""
    )
    
    return component