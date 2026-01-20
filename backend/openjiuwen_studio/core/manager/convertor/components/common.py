#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from typing import Any, Dict, List
from enum import Enum, IntEnum
import ast

from openjiuwen_studio.core.common import dsl
from openjiuwen_studio.schemas.node import BaseValue, Outputs, ExceptionConfig

from openjiuwen_studio.core.common.dsl import ComponentType


def outputs_convert(outputs: Outputs) -> Dict[str, str]:
    result: Dict[str, str] = {}
    if outputs.type == "object":
        for key, value in outputs.properties.items():
            base_value = BaseValue(**value)
            if base_value.type == "ref":
                result[key] = base_value_convert(base_value)
            else:
                result[key] = "${" + key + "}"

    return result


def base_value_convert(value: BaseValue) -> str:
    value_type = value.type
    content = value.content
    if value_type == "ref":
        if not isinstance(content, List):
            raise TypeError("type is ref, but content type is not list")
        ref_value = ".".join(map(str, content))
        replace_value = ref_value.replace("_locals", "")
        return "${" + replace_value + "}"
    elif value_type == "constant":
        if value.schema is None:
            return content
        if value.schema.type == "string":
            return str(content)
        elif value.schema.type == "object" or value.schema.type == "array":
            return ast.literal_eval(str(content).replace('true', 'True').replace('false', 'False'))
        else:
            return content
    elif value_type == "list":
        return content

    raise TypeError("invalid value type")


def input_params_convert(input_parameters: Dict[str, BaseValue]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for key, value in input_parameters.items():
        result[key] = base_value_convert(value)
    return result


def exception_config_convert(exception_conf: ExceptionConfig) -> dsl.ExceptConfig:
    execute_exception_step = dsl.ExceptRouterConfig()
    execute_step = exception_conf.execute_step
    return_content = exception_conf.return_content
    # set default step or 0
    execute_exception_step.default_router_id = execute_step.default_step if execute_step else "0"
    if exception_conf.process_type == dsl.ExceptHandlingMethod.EXECUTE_EXCEPT_STEP:
        if execute_step is None:
            raise TypeError(f"execute step is none when process type is {exception_conf.process_type}")
        execute_exception_step.error_router_id = execute_step.error_step
    elif exception_conf.process_type == dsl.ExceptHandlingMethod.RETURN_CONTENT:
        if return_content is None:
            raise TypeError(f"return content is none when process type is {exception_conf.process_type}")

    return dsl.ExceptConfig(
        max_retries=exception_conf.retry_times,
        timeout_seconds=exception_conf.timeout_seconds,
        except_handling_method=exception_conf.process_type,
        return_content=return_content,
        execute_exception_step=execute_exception_step,
    )
