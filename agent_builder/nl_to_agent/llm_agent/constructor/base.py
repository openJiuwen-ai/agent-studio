# -*- coding:utf-8 -*-
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

import json
import re

from agent_builder.common.logging.base import logger
from agent_builder.nl_to_agent.base import OperatorInput
from agent_builder.nl_to_agent.llm_agent.constructor.prompt import (
    META_PROMPT,
    CONSTRUCTOR_PROMPT,
)
from agent_builder.nl_to_agent.llm_agent.utils import (
    call_model,
    format_dialogue_history,
    FINAL_MSG,
    AGENT_MSG,
    call_model_async,
)


class AgentConstructor:
    def __init__(self, llm, controller):
        self.llm = llm
        self.controller = controller
        self.replacements = {}

    @staticmethod
    def parse_content(content):
        """解析生成的提示词内容"""
        # 匹配提示词
        pattern = r"<提示词>((?:(?!<提示词>|</提示词>).)*)</提示词>"
        prompt_match = re.search(pattern, content, re.DOTALL)
        prompt_parse = prompt_match.group(1).strip() if prompt_match else ""
        # 匹配角色名称
        pattern = r"<角色名称>([^<]*)</角色名称>"
        prompt_match = re.search(pattern, content, re.DOTALL)
        role_name = prompt_match.group(1).strip() if prompt_match else ""
        # 匹配角色描述
        pattern = r"<角色描述>([^<]*)</角色描述>"
        prompt_match = re.search(pattern, content, re.DOTALL)
        role_desc = prompt_match.group(1).strip() if prompt_match else ""

        def parse_resources(_pattern, _content):
            """解析资源信息"""
            match = re.search(_pattern, _content, re.DOTALL)
            if not match:
                return []
            # 将单引号转换为双引号以符合JSON格式
            json_str = match.group(1).replace("'", '"')
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                return []

        # 匹配工具列表
        pattern = r"<选择的插件列表>\s*(\[(?:(?!<选择的插件列表>|</选择的插件列表>)[\s\S]){0,1000}?\])\s*</选择的插件列表>"
        tools_parse = parse_resources(pattern, content)
        # 匹配知识库列表
        pattern = r"<选择的知识库列表>\s*(\[(?:(?!<选择的知识库列表>|</选择的知识库列表>)[\s\S]){0,1000}?\])\s*</选择的知识库列表>"
        knowledge_parse = parse_resources(pattern, content)
        # 匹配工作流列表
        pattern = r"<选择的工作流列表>\s*(\[(?:(?!<选择的工作流列表>|</选择的工作流列表>)[\s\S]){0,1000}?\])\s*</选择的工作流列表>"
        workflow_parse = parse_resources(pattern, content)
        # 匹配技能列表
        pattern = r"<选择的技能列表>\s*(\[(?:(?!<选择的技能列表>|</选择的技能列表>)[\s\S]){0,1000}?\])\s*</选择的技能列表>"
        skills_parse = parse_resources(pattern, content)
        return [
            role_name,
            role_desc,
            prompt_parse,
            tools_parse,
            knowledge_parse,
            workflow_parse,
            skills_parse,
        ]

    @staticmethod
    def resource_id_parse(
        existing_resource_list, integrated_resource_list, unique_key="resource_id"
    ):
        """解析集成的资源列表，如果集成的资源确认在资源库中，则将集成资源的id保存至列表然后返回"""
        resource_id_list = []
        if not integrated_resource_list:
            return resource_id_list
        existing_keys = {
            item[unique_key] for item in existing_resource_list if unique_key in item
        }
        for resource_item in integrated_resource_list:
            if resource_item.get(unique_key) in existing_keys:
                resource_id_list.append(resource_item.get(unique_key))
        return resource_id_list

    @staticmethod
    def tools_version_match_parse(plugin_info, tools_parse, match_type):
        """
        匹配工具列表并提取版本信息
        :param plugin_info: 全量的插件信息列表 (来自 inputs.plugin_info)
        :param tools_parse: 需要解析的工具简略列表
        :return: 包含 tool_id 和 version 的列表
        """
        if not plugin_info or not tools_parse:
            return []

        version_lookup = {
            item["resource_id"]: item.get("version")
            for item in plugin_info
            if "resource_id" in item
        }

        result = []
        for tool in tools_parse:
            res_id = tool.get("resource_id")

            # 只有当 resource_id 在全量信息中存在时才添加
            if res_id in version_lookup:
                if match_type == "tools":
                    result.append(
                        {"tool_id": res_id, "tool_version": version_lookup[res_id]}
                    )
                else:
                    result.append(
                        {
                            "workflow_id": res_id,
                            "workflow_version": version_lookup[res_id],
                        }
                    )

        return result

    @staticmethod
    def skills_version_match_parse(skill_info, skills_parse):
        """
        匹配技能列表并提取版本信息（白名单校验）

        大模型输出的 skill_id 必须存在于候选技能列表中，非法引用剔除并记录日志；
        版本字段一律从候选列表回填，不信任大模型输出。

        :param skill_info: 全量的技能信息列表 (来自 inputs.skill_info)
        :param skills_parse: 需要解析的技能简略列表
        :return: 包含 skill_id 和 skill_version 的列表
        """
        if not skill_info or not skills_parse:
            return []

        version_lookup = {
            item["resource_id"]: item.get("version")
            for item in skill_info
            if "resource_id" in item
        }

        result = []
        for skill in skills_parse:
            res_id = skill.get("resource_id")

            # 只有当 resource_id 在全量信息中存在时才添加
            if res_id in version_lookup:
                result.append(
                    {"skill_id": res_id, "skill_version": version_lookup[res_id]}
                )
            else:
                logger.warning(
                    "LLM selected skill %s not in candidate skill list, dropped.",
                    res_id,
                )

        return result

    def llm_construct(self, prompt):
        """提示词构建"""
        uml_prompts = [{"role": "user", "content": prompt}]
        response = call_model(self.llm, uml_prompts)
        messages = ""
        result = {}
        for chunk_message in response:
            if chunk_message:
                result["cache_token"] = chunk_message
                yield result
                messages += chunk_message
        result[FINAL_MSG] = messages
        yield result

    async def llm_construct_async(self, prompt):
        """提示词构建"""
        uml_prompts = [{"role": "user", "content": prompt}]
        response = call_model_async(self.llm, uml_prompts)
        messages = ""
        result = {}
        async for chunk_message in response:
            if chunk_message:
                result["cache_token"] = chunk_message
                yield result
                messages += chunk_message
        result[FINAL_MSG] = messages
        yield result

    def replacer(self, match):
        """提取花括号中的内容"""
        return self.replacements.get(match.group(1), match.group(0))

    def invoke(self, inputs: OperatorInput):
        """constructor调用函数"""
        dialogue_history = self.controller.context_manager.get_filtered_messages(
            self.controller.task_id, "分类3"
        )
        dialogue_history = format_dialogue_history(dialogue_history)
        self.replacements = {
            "HISTORY_DIALOGUE": str(dialogue_history),
            "PROMPT_TEMPLATE": META_PROMPT,
            "TOOL_LIST": str(inputs.plugin_info),
            "KNOWLEDGE_BASE_LIST": str(inputs.knowledge_info),
            "WORKFLOW_LIST": str(inputs.sub_workflow_info),
            "SKILL_LIST": str(inputs.skill_info),
        }

        filled_template = re.sub(r"\{\{(\w+)\}\}", self.replacer, CONSTRUCTOR_PROMPT)
        result = self.llm_construct(filled_template)
        for item in result:
            if FINAL_MSG in item:
                (
                    role_name,
                    role_desc,
                    prompt_parse,
                    tools_parse,
                    knowledge_parse,
                    workflow_parse,
                    skills_parse,
                ) = self.parse_content(item[FINAL_MSG])

                tools_parse = self.resource_id_parse(inputs.plugin_info, tools_parse)
                knowledge_parse = self.resource_id_parse(
                    inputs.knowledge_info, knowledge_parse
                )
                workflow_parse = self.resource_id_parse(
                    inputs.sub_workflow_info, workflow_parse
                )
                skills_parse = self.resource_id_parse(inputs.skill_info, skills_parse)
                item[AGENT_MSG] = dict(
                    role_name=role_name,
                    role_desc=role_desc,
                    prompt_parse=prompt_parse,
                    tools_id_parse=tools_parse,
                    knowledge_id_parse=knowledge_parse,
                    workflow_id_parse=workflow_parse,
                    skills_id_parse=skills_parse,
                )
                self.controller.reset_llm_agent(item[FINAL_MSG])
            yield item

    async def ainvoke(self, inputs: OperatorInput):
        """constructor调用函数"""
        dialogue_history = self.controller.context_manager.get_filtered_messages(
            self.controller.task_id, "分类3"
        )
        dialogue_history = format_dialogue_history(dialogue_history)
        self.replacements = {
            "HISTORY_DIALOGUE": str(dialogue_history),
            "PROMPT_TEMPLATE": META_PROMPT,
            "TOOL_LIST": str(inputs.plugin_info),
            "KNOWLEDGE_BASE_LIST": str(inputs.knowledge_info),
            "WORKFLOW_LIST": str(inputs.sub_workflow_info),
            "SKILL_LIST": str(inputs.skill_info),
        }

        filled_template = re.sub(r"\{\{(\w+)\}\}", self.replacer, CONSTRUCTOR_PROMPT)
        result = self.llm_construct_async(filled_template)
        async for item in result:
            if FINAL_MSG in item:
                (
                    role_name,
                    role_desc,
                    prompt_parse,
                    tools_parse,
                    knowledge_parse,
                    workflow_parse,
                    skills_parse,
                ) = self.parse_content(item[FINAL_MSG])

                tools_parse = self.tools_version_match_parse(
                    inputs.plugin_info, tools_parse, "tools"
                )
                knowledge_parse = self.resource_id_parse(
                    inputs.knowledge_info, knowledge_parse
                )
                workflow_parse = self.tools_version_match_parse(
                    inputs.sub_workflow_info, workflow_parse, "workflow"
                )
                skills_parse = self.skills_version_match_parse(
                    inputs.skill_info, skills_parse
                )
                item[AGENT_MSG] = dict(
                    role_name=role_name,
                    role_desc=role_desc,
                    prompt_parse=prompt_parse,
                    tools_id_parse=tools_parse,
                    knowledge_id_parse=knowledge_parse,
                    workflow_id_parse=workflow_parse,
                    skills_id_parse=skills_parse,
                )
                await self.controller.async_reset_llm_agent(item[FINAL_MSG])
            yield item
