#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

"""ResourceRetriever 单元测试"""

import json
import math
from unittest.mock import MagicMock, patch

import pytest
from agent_builder.nl_to_agent.adapter.resource_retriever import ResourceRetriever


def _make_plugin_raw(**kwargs):
    defaults = {
        "plugin_id": "p1",
        "plugin_display_name": "插件1",
        "plugin_chinese_name": "中文插件1",
        "plugin_desc": "插件描述1",
        "last_version_id": "v1",
        "tool_id": "t1",
        "tool_display_name": "工具1",
        "tool_chinese_name": "中文工具1",
        "tool_desc": "工具描述1",
        "tool_input_schema": "{}",
        "tool_output_schema": "{}",
    }
    defaults.update(kwargs)
    return {
        "plugin_id": defaults["plugin_id"],
        "plugin_display_name": defaults["plugin_display_name"],
        "plugin_chinese_name": defaults["plugin_chinese_name"],
        "plugin_desc": defaults["plugin_desc"],
        "last_version_id": defaults["last_version_id"],
        "input_schema": [{"tool_id": defaults["tool_id"], "input_schema": defaults["tool_input_schema"]}],
        "output_schema": [{"tool_id": defaults["tool_id"], "output_schema": defaults["tool_output_schema"]}],
        "request_info": {
            "tool_info": [
                {
                    "tool_id": defaults["tool_id"],
                    "tool_display_name": defaults["tool_display_name"],
                    "tool_chinese_name": defaults["tool_chinese_name"],
                    "tool_desc": defaults["tool_desc"],
                }
            ]
        },
    }


def _make_knowledge_raw(kb_id="kb1", name="知识库1", description="知识库描述1"):
    return {
        "knowledge_base_id": kb_id,
        "name": name,
        "description": description,
    }


def _make_workflow_raw(
    wf_id="wf1", name="工作流1", description="工作流描述1", code="workflow_en"
):
    return {
        "workflow_id": wf_id,
        "version_id": "ver1",
        "name": name,
        "description": description,
        "code": code,
        "version_name": "v1",
    }


def _make_resources(plugins=None, knowledge=None, workflows=None):
    return {
        "plugins": {"plugin_list": plugins or []},
        "knowledge_base": {"items": knowledge or []},
        "workflows": {"workflow_version_list": workflows or []},
    }


def _patch_request_context(agent_type="agents"):
    return patch("jiuwen.serve.common.context.request")


class TestCalculateSimilarityScore:
    """calculate_similarity_score 方法测试"""

    @staticmethod
    def _create_retriever_with_empty():
        resources = _make_resources()
        return ResourceRetriever(resources, agent_type="agents")

    @staticmethod
    def test_empty_text_returns_zero():
        retriever = TestCalculateSimilarityScore._create_retriever_with_empty()
        score = retriever.calculate_similarity_score("", "query")
        assert math.isclose(score, 0.0, abs_tol=1e-9)

    @staticmethod
    def test_empty_query_returns_zero():
        retriever = TestCalculateSimilarityScore._create_retriever_with_empty()
        score = retriever.calculate_similarity_score("some text", "")
        assert math.isclose(score, 0.0, abs_tol=1e-9)

    @staticmethod
    def test_both_empty_returns_zero():
        retriever = TestCalculateSimilarityScore._create_retriever_with_empty()
        score = retriever.calculate_similarity_score("", "")
        assert math.isclose(score, 0.0, abs_tol=1e-9)

    @staticmethod
    def test_exact_match_returns_high_score():
        retriever = TestCalculateSimilarityScore._create_retriever_with_empty()
        score = retriever.calculate_similarity_score("天气查询", "天气查询")
        assert score > 0.5

    @staticmethod
    def test_partial_match_returns_medium_score():
        retriever = TestCalculateSimilarityScore._create_retriever_with_empty()
        score = retriever.calculate_similarity_score("天气查询工具", "天气")
        assert 0.0 < score < 1.0

    @staticmethod
    def test_no_match_returns_low_score():
        retriever = TestCalculateSimilarityScore._create_retriever_with_empty()
        score = retriever.calculate_similarity_score("完全无关的文本", "xyzabc")
        assert score < 0.3

    @staticmethod
    def test_score_within_range():
        retriever = TestCalculateSimilarityScore._create_retriever_with_empty()
        score = retriever.calculate_similarity_score("some text", "some")
        assert 0.0 <= score <= 1.0


class TestRetrieve:
    """retrieve 方法测试"""

    @staticmethod
    def _create_retriever_with_data():
        plugins = [
            _make_plugin_raw(
                plugin_id="p1",
                plugin_chinese_name="天气插件",
                plugin_desc="查询天气信息",
                tool_id="t1",
                tool_chinese_name="天气查询",
                tool_desc="查询城市天气",
            ),
            _make_plugin_raw(
                plugin_id="p2",
                plugin_chinese_name="翻译插件",
                plugin_desc="翻译文本内容",
                tool_id="t2",
                tool_chinese_name="文本翻译",
                tool_desc="将文本翻译为指定语言",
            ),
        ]
        knowledge = [
            _make_knowledge_raw(kb_id="kb1", name="天气知识库", description="天气相关知识"),
            _make_knowledge_raw(kb_id="kb2", name="历史知识库", description="历史事件知识"),
        ]
        workflows = [
            _make_workflow_raw(wf_id="wf1", name="天气工作流", description="天气相关流程"),
            _make_workflow_raw(wf_id="wf2", name="审批工作流", description="审批流程"),
        ]
        resources = _make_resources(plugins=plugins, knowledge=knowledge, workflows=workflows)
        return ResourceRetriever(resources, agent_type="agents")

    @staticmethod
    def test_plugin_type_retrieval():
        retriever = TestRetrieve._create_retriever_with_data()
        results = retriever.retrieve("plugin", "天气", top_k=10, min_score=0)
        assert isinstance(results, list)

    @staticmethod
    def test_knowledge_type_retrieval():
        retriever = TestRetrieve._create_retriever_with_data()
        results = retriever.retrieve("knowledge", "天气", top_k=10, min_score=0)
        assert isinstance(results, list)

    @staticmethod
    def test_workflow_type_retrieval():
        retriever = TestRetrieve._create_retriever_with_data()
        results = retriever.retrieve("workflow", "天气", top_k=10, min_score=0)
        assert isinstance(results, list)

    @staticmethod
    def test_unknown_type_raises_not_implemented():
        retriever = TestRetrieve._create_retriever_with_data()
        with pytest.raises(NotImplementedError):
            retriever.retrieve("unknown_type", "query", top_k=5, min_score=0)

    @staticmethod
    def test_top_k_limits_results():
        retriever = TestRetrieve._create_retriever_with_data()
        results = retriever.retrieve("plugin", "插件", top_k=1, min_score=0)
        assert len(results) <= 1

    @staticmethod
    def test_min_score_filters_results():
        retriever = TestRetrieve._create_retriever_with_data()
        results_low = retriever.retrieve("plugin", "天气", top_k=10, min_score=0)
        results_high = retriever.retrieve("plugin", "天气", top_k=10, min_score=0.9)
        assert len(results_high) <= len(results_low)

    @staticmethod
    def test_empty_resources_returns_empty():
        resources = _make_resources()
        retriever = ResourceRetriever(resources, agent_type="agents")
        results = retriever.retrieve("plugin", "query", top_k=5, min_score=0)
        assert results == []


class TestProcessPluginData:
    """_process_plugin_data 内部处理逻辑测试"""

    @staticmethod
    def test_agents_type_filters_unpublished_non_preset():
        plugins = [
            _make_plugin_raw(
                plugin_id="p1",
                last_version_id="",
            ),
            _make_plugin_raw(
                plugin_id="preset_p2",
                last_version_id="",
            ),
            _make_plugin_raw(
                plugin_id="p3",
                last_version_id="v3",
            ),
        ]
        resources = _make_resources(plugins=plugins)
        retriever = ResourceRetriever(resources, agent_type="agents")
        assert len(retriever.plugin_data) == 2

    @staticmethod
    def test_non_agents_type_filters_none_version():
        plugins = [
            _make_plugin_raw(plugin_id="p1", last_version_id="v1"),
            _make_plugin_raw(plugin_id="p2", last_version_id=None),
        ]
        resources = _make_resources(plugins=plugins)
        retriever = ResourceRetriever(resources, agent_type="workflows")
        assert len(retriever.plugin_data) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
