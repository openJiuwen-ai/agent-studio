#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from typing import Any, List

from openjiuwen.core.workflow import IntentDetectionComponent, IntentDetectionCompConfig
from openjiuwen.core.common.logging import logger

from openjiuwen_studio.core.executor.component.compile import util
from openjiuwen_studio.core.executor.component.compile.llm_comp_compiler import parse_model_config
from openjiuwen_studio.core.common.dsl import Component, Connection
from openjiuwen_studio.core.executor.component.compile.base_comp_compiler import BaseCompCompiler
from openjiuwen_studio.core.common.exceptions import JiuWenExecuteException
from openjiuwen_studio.core.common.status_code import StatusCode


class IntentDetectionCompCompiler(BaseCompCompiler):
    def __init__(
            self,
            intent_detection_comp: Component,
            connections: List[Connection]
    ) -> None:
        super().__init__()
        self.config_dict = intent_detection_comp.configs
        self.connections = connections
        self.branch_list = intent_detection_comp.branches
        self.component_id = intent_detection_comp.id

    def compile(self) -> Any:
        model_config, model_client_config, model_id = parse_model_config(self.config_dict)

        config = IntentDetectionCompConfig(
            model_id=None,  # 不能给，给了会走到Runner.get_model
            model_client_config=model_client_config,
            model_config=model_config,
            category_name_list=self.config_dict.get('category_name_list'),
            user_prompt=self.config_dict.get('user_prompt'),
            enable_history=self.config_dict.get('enable_history'),
        )
        intent_comp = IntentDetectionComponent(config)

        if not self.branch_list:
            logger.error(
                f" The branches in component id: {self.component_id} is empty, please check!"
            )
            raise JiuWenExecuteException(
                StatusCode.INTENT_DETECTION_COMP_COMPILER_ERROR.code,
                StatusCode.INTENT_DETECTION_COMP_COMPILER_ERROR.errmsg.format(
                    msg=f"组件 [{self.component_id}] 的分支配置为空"),
                node_id=self.component_id
            )

        for index, branch_info in enumerate(self.branch_list):
            bool_expression = f'${{{self.component_id}.classification_id}} == {index}'
            targets = util.get_targets(self.component_id, branch_info.branch_id, self.connections)
            logger.info(f"[DEBUG] 调用 intent_comp.add_branch: component_id={self.component_id}, "
                        f"condition={bool_expression}, target={targets}, branch_id={branch_info.branch_id}")
            intent_comp.add_branch(
                condition=bool_expression,
                target=targets, branch_id=branch_info.branch_id)
        return intent_comp
