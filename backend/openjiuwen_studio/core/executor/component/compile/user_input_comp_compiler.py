#!/usr/bin/env python3.10
# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

from typing import Any, Dict

from openjiuwen_studio.core.common.dsl import UserInputsConfig
from openjiuwen_studio.core.executor.component.component_impl.user_input_comp import UserInputComponent
from openjiuwen_studio.core.executor.component.compile.base_comp_compiler import BaseCompCompiler
from openjiuwen_studio.core.common.exceptions import JiuWenExecuteException
from openjiuwen_studio.core.common.status_code import StatusCode


class UserInputCompCompiler(BaseCompCompiler):
    def __init__(self, userinput_comp_config_dict: Dict[str, Any], node_id: str) -> None:
        super().__init__()
        self.userinput_comp_config_dict: Dict[str, Any] = userinput_comp_config_dict
        self.node_id = node_id

    def compile(self) -> UserInputComponent:
        if not self.userinput_comp_config_dict:
            raise JiuWenExecuteException(
                StatusCode.USER_INPUT_COMP_COMPILER_ERROR.code,
                StatusCode.USER_INPUT_COMP_COMPILER_ERROR.errmsg.format(
                    msg=f"node [{self.node_id}] is empty, please check!"),
                node_id=self.node_id
            )
        userinputs_config = UserInputsConfig.model_validate(self.userinput_comp_config_dict)
        return UserInputComponent(userinputs_config)
