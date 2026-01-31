#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

from typing import Any, Dict, List

from openjiuwen.core.component.questioner_comp import QuestionerConfig, FieldInfo
from openjiuwen_studio.core.executor.component.component_impl.questioner_comp import QuestionerComponent
from openjiuwen_studio.core.executor.component.compile.llm_comp_compiler import parse_model_config
from openjiuwen_studio.core.executor.component.compile.base_comp_compiler import BaseCompCompiler


class QuestionerCompCompiler(BaseCompCompiler):

    def __init__(self, questioner_comp_config_dict: Dict[str, Any]) -> None:
        super().__init__()
        self.questioner_comp_config_dict: Dict[str, Any] = questioner_comp_config_dict

    def compile(self) -> QuestionerComponent:
        model_config = parse_model_config(self.questioner_comp_config_dict)

        field_infos: List[FieldInfo] = []
        for field_info_dict in self.questioner_comp_config_dict.get('field_names', []):
            field_info = FieldInfo(
                field_name=field_info_dict['field_name'],
                description=field_info_dict['description'],
                cn_field_name=field_info_dict['cn_field_name'],
                required=field_info_dict['required'],
                default_value=field_info_dict['default_value']
            )

            field_infos.append(field_info)

        # 获取 max_response 配置和 with_chat_history配置，有默认值保护
        max_response = self.questioner_comp_config_dict.get('max_response', 3)
        with_chat_history = self.questioner_comp_config_dict.get('with_chat_history', False)

        questioner_comp_config = QuestionerConfig(
            model=model_config,
            field_names=field_infos,
            with_chat_history=with_chat_history,
            max_response=max_response
        )

        return QuestionerComponent(questioner_comp_config)
