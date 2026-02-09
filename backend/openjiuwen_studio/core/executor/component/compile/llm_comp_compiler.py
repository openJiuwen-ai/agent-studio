#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

from typing import Any, Dict
from openjiuwen.core.workflow import LLMCompConfig, LLMComponent
from openjiuwen.core.foundation.llm import ModelRequestConfig, ModelClientConfig, SystemMessage, UserMessage

from openjiuwen_studio.core.common.dsl import LLMConfig as LLMConfigDL
from openjiuwen_studio.core.executor.component.compile.base_comp_compiler import BaseCompCompiler

client_provider_mapping = {
    'siliconflow': "SiliconFlow",
    'openai': "OpenAI",
}


def parse_model_config(comp_config_dict: Dict[str, Any]) -> tuple[ModelRequestConfig, ModelClientConfig, str]:
    """
    解析模型配置，返回 ModelRequestConfig、ModelClientConfig 和 model_id
    Args:
        comp_config_dict: LLM组件配置字典
    Returns:
        tuple: (model_request_config, model_client_config, model_id)
    """
    llm_config_dl = LLMConfigDL.model_validate(comp_config_dict)
    base_model_request_config = llm_config_dl.model.request_config
    base_model_client_config = llm_config_dl.model.model_client_config

    # 创建 ModelRequestConfig
    model_request_config = ModelRequestConfig(
        model=base_model_request_config.model_name,
        temperature=base_model_request_config.temperature,
        top_p=base_model_request_config.top_p,
    )

    # 创建 ModelClientConfig
    model_client_config = ModelClientConfig(
        client_provider=client_provider_mapping[base_model_client_config.client_provider],
        api_key=base_model_client_config.api_key,
        api_base=base_model_client_config.api_base,
        timeout=base_model_client_config.timeout,
        max_retries=1,
        verify_ssl=False,
    )

    # model_id 使用 model_name
    model_id = base_model_request_config.model_name
    return model_request_config, model_client_config, model_id


def parse_template_content(template_content: list) -> tuple[SystemMessage, UserMessage]:
    """
    从 template_content 中解析出 system_prompt_template 和 user_prompt_template
    Args:
        template_content: 模板内容列表，每个元素是 {"role": "system"/"user", "content": "..."}
    Returns:
        tuple: (system_prompt_template, user_prompt_template)
    """
    system_prompt_template = None
    user_prompt_template = None
    if not template_content:
        return None, None

    for msg in template_content:
        if not isinstance(msg, dict):
            continue
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role == "system":
            system_prompt_template = SystemMessage(content=content)
        elif role == "user":
            user_prompt_template = UserMessage(content=content)
    return system_prompt_template, user_prompt_template


class LLMCompCompiler(BaseCompCompiler):
    def __init__(self, llm_comp_config_dict: Dict[str, Any]) -> None:
        super().__init__()
        self.llm_comp_config_dict = llm_comp_config_dict
        self.llm_config_dl = LLMConfigDL.model_validate(llm_comp_config_dict)

    def compile(self) -> LLMComponent:
        model_request_config, model_client_config, model_id = parse_model_config(self.llm_comp_config_dict)
        # 解析 template_content 模板内容
        system_prompt_template, user_prompt_template = parse_template_content(self.llm_config_dl.template_content)

        # 创建 LLMCompConfig
        llm_comp_config = LLMCompConfig(
            model_id=None,  # 不能给，给了会走到Runner.get_model
            model_config=model_request_config,
            model_client_config=model_client_config,
            system_prompt_template=system_prompt_template,
            user_prompt_template=user_prompt_template,
            template_content=self.llm_config_dl.template_content,  # 下一个core版本要删除
            response_format={
                "type": self.llm_config_dl.response_format_type,
            },
            output_config=self.llm_config_dl.output_config,
            enable_history=self.llm_config_dl.enable_history,
        )

        return LLMComponent(llm_comp_config)
