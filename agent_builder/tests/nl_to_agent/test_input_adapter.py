#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

"""InputAdapter 单元测试"""

import json
from unittest.mock import MagicMock, patch

import pytest
from agent_builder.nl_to_agent.adapter.input_adapter import InputAdapter
from agent_builder.nl_to_agent.base import OperatorInput


def _make_plugin_detail(**kwargs):
    defaults = {
        "plugin_id": "p1",
        "plugin_display_name": "插件1",
        "plugin_chinese_name": "中文插件1",
        "plugin_desc": "插件描述",
        "tool_id": "t1",
        "tool_display_name": "工具1",
        "tool_chinese_name": "中文工具1",
        "tool_desc": "工具描述",
        "plugin_version_id": "v1",
        "tool_inputs": '{"properties": {"input1": {"type": "string", "description": "输入1"}}}',
        "tool_outputs": '{"properties": {"output1": {"type": "string", "description": "输出1"}}}',
    }
    defaults.update(kwargs)
    return defaults


def _make_workflow_detail(**kwargs):
    defaults = {
        "workflow_id": "wf1",
        "version_id": "ver1",
        "name": "工作流1",
        "description": "工作流描述",
        "name_en": "workflow_en",
        "version_name": "v1",
        "inputs": '{"properties": {"query": {"type": "string", "description": "用户输入"}}}',
        "outputs": '{"properties": {"response_content": {"type": "string", "description": "最终输出"}}}',
    }
    defaults.update(kwargs)
    return defaults


class TestInputAdapterInit:
    """InputAdapter 初始化测试"""

    @patch(
        "agent_builder.nl_to_agent.adapter.input_adapter.ResourceRetriever"
    )
    @staticmethod
    def test_stores_detail_config(self, mock_retriever):
        """初始化时存储 detail_config"""
        mock_retriever.return_value = MagicMock()
        config = {"key": "value"}
        resource = {"plugins": {}}
        adapter = InputAdapter(config, resource)
        assert adapter.detail_config == config

    @patch(
        "agent_builder.nl_to_agent.adapter.input_adapter.ResourceRetriever"
    )
    @staticmethod
    def test_creates_resource_retriever_with_resource(self, mock_retriever):
        """初始化时使用 resource 创建 ResourceRetriever"""
        mock_retriever.return_value = MagicMock()
        resource = {"plugins": {}, "knowledge_base": {}, "workflows": {}}
        adapter = InputAdapter({}, resource)
        mock_retriever.assert_called_once_with(resource, agent_type=None)

    @patch(
        "agent_builder.nl_to_agent.adapter.input_adapter.ResourceRetriever"
    )
    @staticmethod
    def test_initial_resource_config(self, mock_retriever):
        """初始化时 resource_config 包含空列表"""
        mock_retriever.return_value = MagicMock()
        adapter = InputAdapter({}, {})
        assert adapter.resource_config == {
            "plugin": [],
            "knowledge": [],
            "workflow": [],
        }


class TestRetrieverAdapter:
    """retriever_adapter 方法测试"""

    @patch(
        "agent_builder.nl_to_agent.adapter.input_adapter.ResourceRetriever"
    )
    @staticmethod
    def test_returns_operator_input_with_query(self, mock_retriever):
        """返回的 OperatorInput 包含查询字符串"""
        mock_instance = MagicMock()
        mock_instance.retrieve.return_value = []
        mock_retriever.return_value = mock_instance
        adapter = InputAdapter({}, {})
        result = adapter.retriever_adapter("test query")
        assert isinstance(result, OperatorInput)
        assert result.query == "test query"

    @patch(
        "agent_builder.nl_to_agent.adapter.input_adapter.ResourceRetriever"
    )
    @staticmethod
    def test_calls_retriever_for_each_type(self, mock_retriever):
        """对 plugin、knowledge、workflow 三种类型分别调用 retriever.retrieve"""
        mock_instance = MagicMock()
        mock_instance.retrieve.return_value = []
        mock_retriever.return_value = mock_instance
        adapter = InputAdapter({}, {})
        adapter.retriever_adapter("query", res_num=5, min_score=0.5)
        assert mock_instance.retrieve.call_count == 3
        call_args_list = [call.args for call in mock_instance.retrieve.call_args_list]
        types_called = [args[0] for args in call_args_list]
        assert "plugin" in types_called
        assert "knowledge" in types_called
        assert "workflow" in types_called

    @patch(
        "agent_builder.nl_to_agent.adapter.input_adapter.ResourceRetriever"
    )
    @staticmethod
    def test_filtered_true_processes_plugins_for_llm_agent(self, mock_retriever):
        """filtered=True 时对 plugin 和 workflow 结果进行 llm_agent 格式处理"""
        plugin_data = [_make_plugin_detail()]
        workflow_data = [_make_workflow_detail()]
        mock_instance = MagicMock()

        def mock_retrieve(resource_type, query, res_num, min_score):
            if resource_type == "plugin":
                return plugin_data
            elif resource_type == "workflow":
                return workflow_data
            return []

        mock_instance.retrieve.side_effect = mock_retrieve
        mock_retriever.return_value = mock_instance
        adapter = InputAdapter({}, {})
        result = adapter.retriever_adapter("query", filtered=True)
        assert result.plugin_info is not None
        assert isinstance(result.plugin_info, list)
        if result.plugin_info:
            assert "resource_id" in result.plugin_info[0]
            assert "description" in result.plugin_info[0]
            assert "name" in result.plugin_info[0]

    @patch(
        "agent_builder.nl_to_agent.adapter.input_adapter.ResourceRetriever"
    )
    @staticmethod
    def test_filtered_false_returns_raw_data(self, mock_retriever):
        """filtered=False 时返回原始检索数据"""
        plugin_data = [_make_plugin_detail()]
        mock_instance = MagicMock()

        def mock_retrieve(resource_type, query, res_num, min_score):
            if resource_type == "plugin":
                return plugin_data
            return []

        mock_instance.retrieve.side_effect = mock_retrieve
        mock_retriever.return_value = mock_instance
        adapter = InputAdapter({}, {})
        result = adapter.retriever_adapter("query", filtered=False)
        assert result.plugin_info == plugin_data

    @patch(
        "agent_builder.nl_to_agent.adapter.input_adapter.ResourceRetriever"
    )
    @staticmethod
    def test_resource_config_updated(self, mock_retriever):
        """检索结果更新到 resource_config"""
        plugin_data = [_make_plugin_detail()]
        knowledge_data = [{"name": "kb1"}]
        mock_instance = MagicMock()

        def mock_retrieve(resource_type, query, res_num, min_score):
            if resource_type == "plugin":
                return plugin_data
            elif resource_type == "knowledge":
                return knowledge_data
            return []

        mock_instance.retrieve.side_effect = mock_retrieve
        mock_retriever.return_value = mock_instance
        adapter = InputAdapter({}, {})
        adapter.retriever_adapter("query")
        assert plugin_data[0] in adapter.resource_config["plugin"]
        assert knowledge_data[0] in adapter.resource_config["knowledge"]


class TestWorkflowRetrieveAdapter:
    """workflow_retrieve_adapter 方法测试"""

    @patch(
        "agent_builder.nl_to_agent.adapter.input_adapter.ResourceRetriever"
    )
    @staticmethod
    def test_returns_tuple_of_three(self, mock_retriever):
        """返回三元组 (OperatorInput, plugin_dict, workflow_dict)"""
        mock_instance = MagicMock()
        mock_instance.retrieve.return_value = []
        mock_retriever.return_value = mock_instance
        adapter = InputAdapter({}, {})
        result = adapter.workflow_retrieve_adapter("query")
        assert isinstance(result, tuple)
        assert len(result) == 3
        assert isinstance(result[0], OperatorInput)
        assert isinstance(result[1], dict)
        assert isinstance(result[2], dict)

    @patch(
        "agent_builder.nl_to_agent.adapter.input_adapter.ResourceRetriever"
    )
    @staticmethod
    def test_operator_input_has_query(self, mock_retriever):
        """返回的 OperatorInput 包含查询字符串"""
        mock_instance = MagicMock()
        mock_instance.retrieve.return_value = []
        mock_retriever.return_value = mock_instance
        adapter = InputAdapter({}, {})
        result = adapter.workflow_retrieve_adapter("test query")
        assert result[0].query == "test query"

    @patch(
        "agent_builder.nl_to_agent.adapter.input_adapter.ResourceRetriever"
    )
    @staticmethod
    def test_with_plugin_and_workflow_data(self, mock_retriever):
        """有插件和工作流数据时正确处理"""
        plugin_data = [_make_plugin_detail()]
        workflow_data = [_make_workflow_detail()]
        mock_instance = MagicMock()

        def mock_retrieve(resource_type, query, res_num, min_score):
            if resource_type == "plugin":
                return plugin_data
            elif resource_type == "workflow":
                return workflow_data
            return []

        mock_instance.retrieve.side_effect = mock_retrieve
        mock_retriever.return_value = mock_instance
        adapter = InputAdapter({}, {})
        inputs, plugin_dict, workflow_dict = adapter.workflow_retrieve_adapter("query")
        assert len(plugin_dict) == 1
        assert len(workflow_dict) == 1
        key = f"{plugin_data[0]['plugin_id']}#{plugin_data[0]['tool_id']}"
        assert key in plugin_dict
        assert workflow_data[0]["workflow_id"] in workflow_dict


if __name__ == "__main__":
    pytest.main([__file__, "-v"])