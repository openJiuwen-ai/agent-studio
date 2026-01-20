#!/usr/bin/env python3.10
# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

from typing import Any, Dict

from openjiuwen_studio.core.common.dsl import VariMergeConfig
from openjiuwen_studio.core.executor.component.component_impl.variable_merge_comp import VariableMergeComponent
from openjiuwen_studio.core.executor.component.compile.base_comp_compiler import BaseCompCompiler
from openjiuwen_studio.core.common.exceptions import JiuWenExecuteException
from openjiuwen_studio.core.common.status_code import StatusCode


class VariableMergeCompCompiler(BaseCompCompiler):
    def __init__(self, comp_config_dict: Dict[str, Any], node_id: str) -> None:
        super().__init__()
        self.comp_config_dict: Dict[str, Any] = comp_config_dict
        self.node_id = node_id

    def compile(self) -> VariableMergeComponent:
        if not self.comp_config_dict:
            raise JiuWenExecuteException(
                StatusCode.VARIABLE_MERGE_COMP_COMPILER_ERROR.code,
                StatusCode.VARIABLE_MERGE_COMP_COMPILER_ERROR.errmsg.format(
                    msg=f"node [{self.node_id}] is empty, please check!"),
                node_id=self.node_id
            )
        merge_config = VariMergeConfig.model_validate(self.comp_config_dict)
        return VariableMergeComponent(merge_config)