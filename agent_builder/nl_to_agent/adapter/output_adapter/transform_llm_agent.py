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

# 对话式生成单次集成的技能数量上限（编辑器人工配置上限为50，生成场景从严控制）
MAX_NL2_SKILL_NUM = 5


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


def collect_skill_references(skill_id_list, skill_list):
    """
    根据白名单校验后的技能id列表，从候选技能列表收集完整技能引用。

    skill_id_list 的元素兼容两种形态：字符串 id（同步链路）与
    含 skill_id 的字典（异步链路的 skills_version_match_parse 产物）。
    版本字段一律取候选列表的权威值，不信任大模型输出。

    :param skill_id_list: 白名单校验后的技能id列表
    :param skill_list: 全量候选技能列表（含 resource_id/name/description/icon/version）
    :return: SkillReference 结构的技能引用列表（数量不超过 MAX_NL2_SKILL_NUM）
    """
    if not skill_id_list or not skill_list:
        return []

    id_set = set()
    for item in skill_id_list:
        if isinstance(item, dict):
            skill_id = item.get("skill_id")
        else:
            skill_id = item
        if skill_id:
            id_set.add(skill_id)

    collected_skills = []
    seen = set()
    for skill in skill_list:
        resource_id = skill.get("resource_id")
        if resource_id in id_set and resource_id not in seen:
            seen.add(resource_id)
            collected_skills.append(
                {
                    "skill_id": resource_id,
                    "skill_name": skill.get("name", ""),
                    "description": skill.get("description", ""),
                    "icon": skill.get("icon", ""),
                    "last_version_id": skill.get("version", ""),
                }
            )
    return collected_skills[:MAX_NL2_SKILL_NUM]


def transform_to_cloud(input_json: dict, full_resource_dict: dict, model_dict: dict = None):
    """转换成格式"""
    knowledge_list = full_resource_dict.get("knowledge", [])
    skill_list = full_resource_dict.get("skill", [])

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

    # 技能（Skill）：按 SkillReference 结构写入，数量不超过 MAX_NL2_SKILL_NUM
    data["skills"] = collect_skill_references(
        input_json.get("skills_id_parse", []), skill_list
    )

    # 获取当前时间 格式化为 "YYYY-MM-DD HH:MM:SS" 格式
    formatted_time = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    data["create_time"] = formatted_time
    data["update_time"] = formatted_time
    return json.dumps(data, ensure_ascii=False)
