# -*- coding:utf-8 -*-
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
# N2L临时覆盖，适配该特性：运行时提供可用插件/知识库列表（按NL2Agent/Workflow的结构）
# 将前端传入的resource传入ResourceRetriever
import json

from agent_builder.nl_to_agent.adapter.resource_retriever import ResourceRetriever
from agent_builder.nl_to_agent.base import OperatorInput


class InputAdapter:
    """输入适配器类，用于对接资源配置和模式配置，并提供统一的检索接口。

    该类封装了资源检索逻辑，能够根据输入查询从不同的资源类型中
    （插件、知识、子工作流）检索相关信息，并组织成标准化的输入格式。

    Attributes:
        detail_config (dict): 平台配置字典，包含平台组件相关的详细配置。
        retriever (ResourceRetriever): 资源检索器实例，用于执行具体的检索操作。
    """

    def __init__(self, detail_config: dict, resource: dict, agent_type: str = None) -> None:
        """初始化输入适配器。

        Args:
            detail_config (dict): 平台配置字典，包含平台组件相关的详细配置。
            agent_type (str): agent类型，如 "agents" 或 "workflows"
        """
        self.resource_config = {
            "plugin": [],
            "knowledge": [],
            "workflow": [],
        }  # 用于保留全量字段
        self.detail_config = detail_config
        self.retriever = ResourceRetriever(resource, agent_type=agent_type)

    def process_plugin_list_for_workflow(self, plugin_list: list):
        """为工作流生成准备插件字典和插件描述"""
        plugin_dict = {}
        for detail_plugin in plugin_list:
            plugin = {}
            plugin["version_id"] = detail_plugin["plugin_version_id"]
            plugin["plugin_id"] = detail_plugin["plugin_id"]
            plugin["tool_id"] = detail_plugin["tool_id"]
            plugin["tool_name"] = detail_plugin["tool_display_name"]
            plugin["tool_cn_name"] = detail_plugin["tool_chinese_name"]
            plugin["tool_desc"] = detail_plugin["tool_desc"]
            plugin["origin_input"] = {}
            plugin["inputs"] = []
            plugin["inputs_for_simpleIR"] = []
            input_schema = json.loads(detail_plugin["tool_inputs"])
            for input_name, input_config in input_schema.get("properties", {}).items():
                plugin["origin_input"][input_name] = input_config
                plugin["inputs"].append(
                    {
                        "name": input_name,
                        "type": input_config.get("type"),
                        "description": input_config.get("description"),
                    }
                )
                plugin["inputs_for_simpleIR"].append(
                    {
                        "name": input_name,
                        "type": input_config.get("type"),
                        "description": input_config.get("description"),
                    }
                )
            plugin["origin_output"] = {}
            plugin["outputs"] = []
            plugin["outputs_for_simpleIR"] = []
            plugin["output_schema"] = detail_plugin["tool_outputs"]
            output_schema = json.loads(detail_plugin["tool_outputs"])
            for output_name, output_config in output_schema.get(
                "properties", {}
            ).items():
                plugin["origin_output"][output_name] = output_config
                var_type = output_config.get("type")
                if var_type in ["array", "object"]:
                    plugin = self.get_var_all_output(
                        plugin, output_name, output_config, var_type
                    )
                else:
                    plugin["outputs"].append(
                        {
                            "name": output_name,
                            "type": output_config.get("type"),
                            "description": output_config.get("description"),
                        }
                    )
                    plugin["outputs_for_simpleIR"].append(
                        {
                            "name": output_name,
                            "type": output_config.get("type"),
                            "description": output_config.get("description"),
                        }
                    )
            plugin_dict[f"{plugin.get('plugin_id')}#{plugin.get('tool_id')}"] = plugin
        plugin_info_list = []
        for plugin in plugin_dict.values():
            plugin_info = {}
            plugin_info["resource_id"] = (
                f"{plugin.get('plugin_id')}#{plugin.get('tool_id')}"
            )
            plugin_info["name"] = plugin.get("tool_name")
            plugin_info["description"] = plugin.get("tool_desc")
            plugin_info["inputs"] = plugin.get("inputs_for_simpleIR")
            plugin_info["outputs"] = plugin.get("outputs_for_simpleIR")
            plugin_info_list.append(plugin_info)
        return plugin_dict, plugin_info_list

    def process_workflow_list_for_workflow(self, workflow_list: list):
        """为工作流生成准备工作流字典和工作流描述"""
        workflow_dict = {}
        for detail_workflow in workflow_list:
            workflow = {**detail_workflow}
            workflow["origin_input"] = {}
            workflow["inputs"] = []
            input_schema = json.loads(detail_workflow["inputs"])
            for input_name, input_config in input_schema.get("properties", {}).items():
                workflow["origin_input"][input_name] = input_config
                workflow["inputs"].append(
                    {
                        "name": input_name,
                        "type": input_config.get("type"),
                        "description": input_config.get("description"),
                    }
                )
            workflow["origin_output"] = {}
            workflow["outputs"] = []
            workflow["output_schema"] = detail_workflow["outputs"]
            output_schema = json.loads(detail_workflow["outputs"])
            for output_name, output_config in output_schema.get(
                "properties", {}
            ).items():
                workflow["origin_output"][output_name] = output_config
                var_type = output_config.get("type")
                if var_type in ["array", "object"]:
                    workflow = self.get_var_all_output(
                        workflow, output_name, output_config, var_type
                    )
                else:
                    workflow["outputs"].append(
                        {
                            "name": output_name,
                            "type": output_config.get("type"),
                            "description": output_config.get("description"),
                        }
                    )
            workflow_dict[workflow.get("workflow_id")] = workflow
        workflow_info_list = []
        for workflow in workflow_dict.values():
            workflow_info = {}
            workflow_info["workflow_id"] = workflow.get("workflow_id")
            workflow_info["name"] = workflow.get("tool_name")
            workflow_info["description"] = workflow.get("tool_desc")
            workflow_info["inputs"] = workflow.get("inputs")
            workflow_info["outputs"] = workflow.get("outputs")
            workflow_info_list.append(workflow_info)
        return workflow_dict, workflow_info_list

    def get_var_all_output(self, plugin, output_name, output_config, var_type):
        """处理插件的复杂类型输出变量"""
        if var_type == "array":
            for sub_output_name, sub_output_config in (
                output_config.get("items", {}).get("properties", {}).items()
            ):
                name = f"{sub_output_name}_of_{output_name}"
                sub_output_type = sub_output_config.get("type")
                if sub_output_type in ["array", "object"]:
                    plugin = self.get_var_all_output(
                        plugin, name, sub_output_config, sub_output_type
                    )
                else:
                    plugin["outputs"].append(
                        {
                            "name": name,
                            "type": sub_output_type,
                            "description": sub_output_config.get("description"),
                        }
                    )
                    plugin["outputs_for_simpleIR"].append(
                        {
                            "name": name,
                            "type": sub_output_type,
                            "description": sub_output_config.get("description"),
                        }
                    )
        elif var_type == "object":
            for sub_output_name, sub_output_config in output_config.get(
                "properties", {}
            ).items():
                name = f"{sub_output_name}_of_{output_name}"
                sub_output_type = sub_output_config.get("type")
                if sub_output_type in ["array", "object"]:
                    plugin = self.get_var_all_output(
                        plugin, name, sub_output_config, sub_output_type
                    )
                else:
                    plugin["outputs"].append(
                        {
                            "name": name,
                            "type": sub_output_type,
                            "description": sub_output_config.get("description"),
                        }
                    )
                    plugin["outputs_for_simpleIR"].append(
                        {
                            "name": name,
                            "type": sub_output_type,
                            "description": sub_output_config.get("description"),
                        }
                    )
        return plugin

    def retriever_adapter(
        self,
        query: str,
        res_num: int = 100,
        min_score: float = 0,
        filtered: bool = False,
    ) -> OperatorInput:
        """检索适配器方法。

        根据输入的查询内容，分别从插件、知识和子工作流三类资源中
        检索相关信息，并将结果填充到标准化的输入对象中。

        Args:
            query (str): 查询字符串。
            res_num (int, optional): 每类资源返回的最大结果数，默认为 5。
            min_score (float, optional): 检索结果的最低相关性分数阈值，默认为 0.7。
            filtered (bool): 是否需要过滤部分字段。

        Returns:
            OperatorInput: 包含检索结果的输入对象，包括插件、知识和子工作流信息。
        """

        def process_plugin_for_llm_agent(plugin_info: list) -> list:
            if not plugin_info:
                return []
            processed_plugin_list = []
            for plugin in plugin_info:
                simple_plugin = {
                    "resource_id": f"{plugin['plugin_id']}#{plugin['tool_id']}",
                    "description": plugin["tool_desc"],
                    "name": f"{plugin['plugin_display_name']}#{plugin['tool_display_name']}",
                    "version": plugin.get("plugin_version_id"),
                }
                processed_plugin_list.append(simple_plugin)
            return processed_plugin_list

        def process_workflow_for_llm_agent(workflow_info: list) -> list:
            if not workflow_info:
                return []
            processed_workflow_list = []
            for workflow in workflow_info:
                simple_workflow = {
                    "resource_id": f"{workflow['workflow_id']}#{workflow['version_id']}",
                    "description": workflow["description"],
                    "name": workflow["name"],
                }
                processed_workflow_list.append(simple_workflow)
            return processed_workflow_list

        inputs = OperatorInput(query=query)
        plugin_info_raw = self.retriever.retrieve("plugin", query, res_num, min_score)
        knowledge_info_raw = self.retriever.retrieve(
            "knowledge", query, res_num, min_score
        )
        sub_workflow_info_raw = self.retriever.retrieve(
            "workflow", query, res_num, min_score
        )
        inputs.plugin_info = (
            process_plugin_for_llm_agent(plugin_info_raw)
            if filtered
            else plugin_info_raw
        )
        inputs.knowledge_info = knowledge_info_raw
        inputs.sub_workflow_info = (
            process_workflow_for_llm_agent(sub_workflow_info_raw)
            if filtered
            else sub_workflow_info_raw
        )
        if plugin_info_raw:
            self.resource_config["plugin"].extend(plugin_info_raw)
        if knowledge_info_raw:
            self.resource_config["knowledge"].extend(knowledge_info_raw)
        if sub_workflow_info_raw:
            self.resource_config["workflow"].extend(sub_workflow_info_raw)
        return inputs

    def workflow_retrieve_adapter(
        self, query: str, res_num: int = 5, min_score: float = 0.7
    ):
        """工作流的检索"""
        inputs = OperatorInput(query=query)
        plugin_info_raw = self.retriever.retrieve("plugin", query, res_num, min_score)
        knowledge_info_raw = self.retriever.retrieve(
            "knowledge", query, res_num, min_score
        )
        sub_workflow_info_raw = self.retriever.retrieve(
            "workflow", query, res_num, min_score
        )
        plugin_dict, plugin_info_list = self.process_plugin_list_for_workflow(
            plugin_info_raw
        )
        workflow_dict, workflow_info_list = self.process_workflow_list_for_workflow(
            sub_workflow_info_raw
        )
        inputs.plugin_info = plugin_info_list
        inputs.knowledge_info = knowledge_info_raw
        inputs.sub_workflow_info = workflow_info_list
        return inputs, plugin_dict, workflow_dict
