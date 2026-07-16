# -*- coding:utf-8 -*-
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

from agent_builder.adapter.jiuwen_bridge import HumanMessage, SystemMessage, AIMessage

FINAL_MSG = "final_msg"
AGENT_MSG = "agent_msg"
CACHE_TOKEN = "cache_token"
LLM_AGENT_IR = "llm_agent_ir"


def convert_to_obj_list(dict_list):
    """
    将字典列表转换为对象列表
    :param dict_list: 字典列表，例如 [{"role": "system", "content": "..."}]
    :return: 对象列表，例如 [SystemMessage(content='...'), HumanMessage(content='...')]
    """
    role_mapping = {
        "system": SystemMessage,
        "user": HumanMessage,
        "assistant": AIMessage,
    }
    obj_list = []
    for item in dict_list:
        role = item["role"]
        content = item["content"]
        if role in role_mapping:
            obj_list.append(role_mapping[role](content=content))
        else:
            raise ValueError(f"Unknown role: {role}")
    return obj_list


def call_model(model, query_list):
    """调用模型"""

    def extract_content(response):
        for chunk in response:
            try:
                if chunk.raw_content != "":
                    yield chunk.raw_content
            except AttributeError:
                continue

    new_his = convert_to_obj_list(query_list)
    response = model.chat(new_his, method="stream", add_prefix=False)
    return extract_content(response)


async def call_model_async(model, query_list):
    """调用模型"""
    new_his = convert_to_obj_list(query_list)
    response = model.achat(new_his, method="stream", add_prefix=False)
    async for item in response:
        try:
            if item.raw_content != "":
                yield item.raw_content
        except AttributeError:
            continue


def format_dialogue_history(dialogue_history: list) -> list:
    """提取格式化的对话历史"""
    formatted_dialogue_history = []
    for talk in dialogue_history:
        if talk.get("role") == "user":
            formatted_dialogue_history.append(f"User: {talk['content']}")
        elif talk.get("role") == "assistant":
            formatted_dialogue_history.append(f"Assistant: {talk['content']}")
    return formatted_dialogue_history
