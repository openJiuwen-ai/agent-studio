# -*- coding:utf-8 -*-
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
import string

PRESET = "preset"


class ResourceRetriever:
    def __init__(self, resources, agent_type: str = None):
        """
        初始化资源检索器

        Args:
            resources (dict): 包含plugins、knowledge_base、workflows的字典
            agent_type (str): agent类型，如 "agents" 或 "workflows"
        """
        self.resource = resources
        self.agent_type = agent_type

        # 从resources中获取数据
        raw_plugin_data = self.resource.get("plugins", {})
        raw_knowledge_data = self.resource.get("knowledge_base", {})
        raw_workflow_data = self.resource.get("workflows", {})

        plugin_list = raw_plugin_data.get("plugin_list", [])
        knowledge_list = raw_knowledge_data.get("items", [])  # 知识库数据在 items 键中
        workflow_list = raw_workflow_data.get("workflow_version_list", [])

        self.plugin_data = self._process_plugin_data(plugin_list)
        self.knowledge_data = self._process_knowledge_data(knowledge_list)
        self.workflow_data = self._process_workflow_data(workflow_list)

    def _process_plugin_data(self, raw_data):
        """
        处理插件数据，构建输入输出映射
        :param raw_data: 原始插件数据（直接是插件列表）
        :return: 处理后的插件列表
        """
        if not raw_data:
            return []

        # 创建映射：tool_id -> input_schema
        input_schema_map = {}
        for plugin in raw_data:
            for input_item in plugin.get("input_schema", []):
                input_schema_map[input_item["tool_id"]] = input_item["input_schema"]

        # 创建映射：tool_id -> output_schema
        output_schema_map = {}
        for plugin in raw_data:
            for output_item in plugin.get("output_schema", []):
                output_schema_map[output_item["tool_id"]] = output_item["output_schema"]

        # 构建新的插件列表
        processed_plugins = []
        for plugin in raw_data:
            plugin_id = plugin["plugin_id"]
            plugin_display_name = plugin["plugin_display_name"]
            plugin_chinese_name = plugin["plugin_chinese_name"]
            plugin_desc = plugin["plugin_desc"]

            if self.agent_type in ("agents", "llm_agent"):
                plugin_version_id = plugin.get(
                    "last_version_id", ""
                )  # 新增九问后续处理所需字段数据
                preset = PRESET in plugin["plugin_id"]  # 预置插件均以”preset“开头
                if plugin_version_id == "" and not preset:
                    continue  # 如果没有 last_version_id，跳过该插件，表明未发布
            else:
                plugin_version_id = plugin.get(
                    "last_version_id"
                )  # 新增九问后续处理所需字段数据
                if plugin_version_id is None:
                    continue  # 如果没有 last_version_id，跳过该插件，表明未发布

            for tool in plugin["request_info"]["tool_info"]:
                tool_id = tool["tool_id"]
                tool_display_name = tool["tool_display_name"]
                tool_chinese_name = tool["tool_chinese_name"]
                tool_desc = tool["tool_desc"]

                # 获取输入和输出
                tool_inputs = input_schema_map.get(tool_id, "")
                tool_outputs = output_schema_map.get(tool_id, "")

                # 构建新对象
                processed_plugin = {
                    "plugin_id": plugin_id,
                    "plugin_display_name": plugin_display_name,
                    "plugin_chinese_name": plugin_chinese_name,
                    "plugin_desc": plugin_desc,
                    "tool_id": tool_id,
                    "tool_display_name": tool_display_name,
                    "tool_chinese_name": tool_chinese_name,
                    "tool_desc": tool_desc,
                    "tool_inputs": tool_inputs,
                    "tool_outputs": tool_outputs,
                    "plugin_version_id": plugin_version_id,
                }
                processed_plugins.append(processed_plugin)

        return processed_plugins

    def _process_knowledge_data(self, raw_data):
        """
        处理知识库数据
        :param raw_data: 原始知识库数据（直接是知识库列表）
        :return: 处理后的知识库列表
        """
        if not raw_data:
            return []

        processed_knowledge = []
        for item in raw_data:
            processed_knowledge.append(
                {
                    "resource_id": item.get("knowledge_base_id", ""),
                    "name": item.get("name", ""),
                    "description": item.get("description", ""),
                }
            )

        return processed_knowledge

    def _process_workflow_data(self, raw_data):
        """
        处理工作流数据
        :param raw_data: 原始工作流数据（直接是工作流列表）
        :return: 处理后的工作流列表
        """
        if not raw_data:
            return []

        processed_workflow = []
        items = {
            "inputs": [
                {
                    "name": "query",
                    "type": "string",
                    "description": "用户输入",
                    "required": True,
                    "source": "system",
                    "field_type": "input",
                    "reflection": False,
                    "value": {"type": "literal", "content": "", "hint": "用户输入"},
                }
            ],
            "outputs": [
                {
                    "name": "response_content",
                    "type": "string",
                    "description": "最终输出",
                    "required": True,
                    "source": "system",
                    "reflection": False,
                    "value": {"type": "generated"},
                }
            ],
        }
        for item in raw_data:
            processed_workflow.append(
                {
                    "workflow_id": item.get("workflow_id", ""),
                    "version_id": item.get("version_id", ""),
                    "name": item.get("name", ""),
                    "description": item.get("description", ""),
                    "name_en": item.get("code", ""),
                    "version_name": item.get("version_name", ""),
                    "inputs": items.get("inputs", []),
                    "outputs": items.get("outputs", []),
                }
            )

        return processed_workflow

    def calculate_similarity_score(self, text: str, query: str) -> float:
        """
        计算文本与查询关键词的相似度分数

        :param text: 待匹配的文本
        :param query: 查询关键词
        :return: 相似度分数 (0.0-1.0)
        """
        if not text or not query:
            return 0.0

        # 转换为小写进行不区分大小写的匹配
        text_lower = text.lower()
        query_lower = query.lower()

        # 去除文本中的标点符号
        translator = str.maketrans("", "", string.punctuation)
        text_lower = text_lower.translate(translator)

        # 分割查询关键词
        query_words = query_lower

        # 计算关键词匹配度
        matched_words = 0
        total_words = len(query_words)

        for word in query_words:
            if word in text_lower:
                matched_words += 1

        # 基础匹配分数
        base_score = matched_words / total_words if total_words > 0 else 0.0

        # 计算匹配位置加权分数（关键词越靠前分数越高）
        position_weight = 0.0
        for word in query_words:
            word_pos = text_lower.find(word)
            if word_pos != -1:
                # 位置权重：越靠前分数越高，最高0.3
                position_weight += max(0, 0.3 - (word_pos / len(text)) * 0.3)

        # 计算文本长度权重（避免过短文本获得过高分数）
        length_weight = min(1.0, len(text) / 100)  # 假设100字符为基准

        # 综合分数计算
        final_score = base_score * 0.6 + position_weight * 0.3 + length_weight * 0.1

        return min(1.0, max(0.0, final_score))

    def retrieve(self, resource_type, query_keyword, top_k, min_score):
        """
        根据资源类型、检索关键词、返回结果数量、最低分数检索相应资源
        :param resource_type: 检索资源类型
        :param query_keyword: 检索关键词
        :param top_k: 检索返回结果的上限数量
        :param min_score: 匹配的最小分数
        :return 检索的资源list：
        """
        resource_list = []

        # 根据资源类型选择对应的数据源
        if resource_type == "plugin":
            processed_data = self.plugin_data
            for item in processed_data:
                # 构建搜索文本（名称 + 描述）
                search_text = f"{item['tool_chinese_name']} {item['tool_desc']} {item['plugin_chinese_name']} {item['plugin_desc']}"

                # 计算相似度分数
                similarity_score = self.calculate_similarity_score(
                    search_text, query_keyword
                )

                # 只考虑分数不低于最低阈值的候选结果
                if similarity_score >= min_score:
                    # 构建返回结果
                    resource_list.append(item)
        elif resource_type == "knowledge":
            processed_data = self.knowledge_data
            for item in processed_data:
                # 构建搜索文本（名称 + 描述）
                search_text = f"{item['name']} {item['description']}"

                # 计算相似度分数
                similarity_score = self.calculate_similarity_score(
                    search_text, query_keyword
                )

                # 只考虑分数不低于最低阈值的候选结果
                if similarity_score >= min_score:
                    # 构建返回结果
                    resource_list.append(item)
        elif resource_type == "workflow":
            processed_data = self.workflow_data
            for item in processed_data:
                # 构建搜索文本（名称 + 描述）
                search_text = f"{item['name']} {item['description']}"

                # 计算相似度分数
                similarity_score = self.calculate_similarity_score(
                    search_text, query_keyword
                )

                # 只考虑分数不低于最低阈值的候选结果
                if similarity_score >= min_score:
                    # 构建返回结果
                    resource_list.append(item)
        else:
            raise NotImplementedError

        # 按分数降序排序
        resource_list.sort(
            key=lambda x: self.calculate_similarity_score(
                (
                    f"{x.get('tool_chinese_name', '')} {x.get('tool_desc', '')} {x.get('plugin_chinese_name', '')} {x.get('plugin_desc', '')}"
                    if resource_type == "plugin"
                    else f"{x.get('name', '')} {x.get('description', '')}"
                ),
                query_keyword,
            ),
            reverse=True,
        )

        # 应用top_k限制
        final_results = resource_list[:top_k]

        return final_results
