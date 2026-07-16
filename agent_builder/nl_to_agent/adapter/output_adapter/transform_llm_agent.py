# -*- coding:utf-8 -*-
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

import copy
import json
import uuid
from datetime import datetime, timezone

from agent_builder.nl_to_agent.adapter.output_adapter.llm_agent_template import (
    CLOUD_LLMAGENT_TEMPLATE,
)
from agent_builder.adapter.jiuwen_bridge import request_json


def collect_resource_list(resource_type, id_list, resource_list):
    """
    根据id_list中的id信息，收集对应的完整资源信息。
    resource_type: 资源类型（plugin、knowledge、workflow、mcp）
    id_list: Agent集成的某类资源id列表。
    resource_list: 完整的某类原始的资源信息列表。
    返回元格式的资源列表。
    """
    if not id_list:
        return []
    collected_resource_list = []

    for resource_id in id_list:
        for resource in resource_list:
            if resource["resource_id"] == resource_id:
                collected_resource_list.append(resource_id)
    return collected_resource_list


def transform_to_cloud(input_json: dict, full_resource_dict: dict, model_dict: dict = None):
    """转换成格式"""
    knowledge_list = full_resource_dict.get("knowledge", [])

    data = copy.deepcopy(CLOUD_LLMAGENT_TEMPLATE)
    data["agent_id"] = str(uuid.uuid4())
    data["name"] = input_json.get("role_name")
    data["description"] = input_json.get("role_desc")
    data["instructions"] = input_json["prompt_parse"]

    if model_dict:
        data["model_deployment_id"] = model_dict.get("deployment_id")
        data["model_name"] = model_dict.get("model_explicit_name")
    else:
        payload = request_json.get({})
        model_info = payload.get("model") or {}
        extension = model_info.get("extension") or {}
        data["model_deployment_id"] = extension.get("deploymentId")
        data["model_name"] = model_info.get("modelExplicitName")

    data["tools"] = input_json["tools_id_parse"]  # 优化格式插件

    knowledge_id_parse = input_json["knowledge_id_parse"]
    data["knowledge_repos"] = collect_resource_list(
        "knowledge", knowledge_id_parse, knowledge_list
    )[:1]
    if data["knowledge_repos"]:
        data["knowledge_retrieve_policy"] = dict(
            search_mode="doc", top_k=3, recall_threshold=0.1, faq_threshold=0.9
        )

    data["workflows"] = []  # 优化格式工作流

    data["mcp_servers"] = []

    # 获取当前时间 格式化为 "YYYY-MM-DD HH:MM:SS" 格式
    formatted_time = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    data["create_time"] = formatted_time
    data["update_time"] = formatted_time
    return json.dumps(data, ensure_ascii=False)
