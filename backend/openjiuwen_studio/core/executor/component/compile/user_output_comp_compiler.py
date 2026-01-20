#!/usr/bin/env python3.10
# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

from typing import Any, Dict
import re
from openjiuwen_studio.core.common.dsl import UserOutputConfig
from openjiuwen_studio.core.executor.component.component_impl.user_output_comp import UserOutputComponent
from openjiuwen_studio.core.executor.component.compile.base_comp_compiler import BaseCompCompiler
from openjiuwen_studio.core.common.exceptions import JiuWenExecuteException
from openjiuwen_studio.core.common.status_code import StatusCode
from openjiuwen.core.common.logging import logger


def find_llm_to_stream_out(target_comp_id, inputs, stream_output_dict):
    pattern = r'llm_\w+'
    for key, value in inputs.items():
        match = re.search(pattern, value)
        if match:
            source_id = match.group()
            # 如果source_id已存在，确保值是列表
            if source_id in stream_output_dict:
                if not isinstance(stream_output_dict[source_id], list):
                    # 如果当前不是列表，先转换为列表
                    stream_output_dict[source_id] = [stream_output_dict[source_id]]
                # 添加新的target_comp_id（避免重复）
                if target_comp_id not in stream_output_dict[source_id]:
                    stream_output_dict[source_id].append(target_comp_id)
            else:
                stream_output_dict[source_id] = target_comp_id
    logger.debug(f"find node to stream connect: {stream_output_dict}")
    return stream_output_dict


def change_stream_input(inputs):
    pattern = r'llm_\w+'
    stream_inputs = {}
    new_inputs = {}
    for key, value in inputs.items():
        if isinstance(value, str) and re.search(pattern, value):
            stream_inputs[key] = value
        else:
            new_inputs[key] = value
    if not stream_inputs:
        stream_inputs=None
    if not new_inputs:
        new_inputs=None
    return stream_inputs, new_inputs


class UserOutputCompCompiler(BaseCompCompiler):
    def __init__(self, node_id: str, useroutput_comp_config_dict: Dict[str, Any], inputs,
                 need_stream_output_comp) -> None:
        super().__init__()
        self.useroutput_comp_config_dict: Dict[str, Any] = useroutput_comp_config_dict
        self.node_id: str = node_id
        self.inputs = inputs
        self.need_stream_output_comp = need_stream_output_comp

    def compile(self):
        if not self.useroutput_comp_config_dict:
            raise JiuWenExecuteException(
                StatusCode.USER_OUTPUT_COMP_COMPILER_ERROR.code,
                StatusCode.USER_OUTPUT_COMP_COMPILER_ERROR.errmsg.format(
                    msg=f"node [{self.node_id}] data is empty, please check!"),
                node_id=self.node_id
            )
        output_config = UserOutputConfig.model_validate(self.useroutput_comp_config_dict)
        if output_config.streaming:
            find_llm_to_stream_out(self.node_id, self.inputs, self.need_stream_output_comp)
        return UserOutputComponent(self.node_id, output_config), self.need_stream_output_comp
