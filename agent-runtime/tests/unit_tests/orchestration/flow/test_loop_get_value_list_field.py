# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Tests for get_value_from_nested_structure_by_path_list — list 字段抽取分支。

背景 bug：路径形如 ``node_x.items.name``（items 为 list[dict]）时，原实现先执行
``final_result = []`` 再 ``for item in final_result`` 自遍历刚置空的列表，循环体
永不执行，该形态路径恒返回 ``[]``，导致循环中断条件（如 ``length(...)>0``）与
SetVariable 右值解析永久失效。
"""

from jiuwen.orchestration.flow.components.loop import (
    get_value_from_nested_structure_by_path_list,
)


class TestListFieldExtraction:
    """list + 字符串键：应对每个 dict 元素抽取同名字段（map 语义）。"""

    @staticmethod
    def test_list_of_dicts_extracts_field():
        data = {"node_x": {"items": [{"name": "a"}, {"name": "b"}]}}
        assert (
            get_value_from_nested_structure_by_path_list(data, "node_x.items.name")
            == ["a", "b"]
        )

    @staticmethod
    def test_list_of_dicts_missing_key_fills_none():
        data = {"node_x": {"items": [{"name": "a"}, {"other": 1}]}}
        assert (
            get_value_from_nested_structure_by_path_list(data, "node_x.items.name")
            == ["a", None]
        )

    @staticmethod
    def test_list_of_dicts_empty_list():
        data = {"node_x": {"items": []}}
        assert get_value_from_nested_structure_by_path_list(data, "node_x.items.name") == []

    @staticmethod
    def test_list_containing_non_dict_returns_none():
        data = {"node_x": {"items": [{"name": "a"}, "not-a-dict"]}}
        assert get_value_from_nested_structure_by_path_list(data, "node_x.items.name") is None


class TestExistingBehaviorRegression:
    """dict 路径 / 列表下标 / 键不存在等既有行为不应受影响。"""

    @staticmethod
    def test_dict_path():
        data = {"node_x": {"userFields": {"query": "hi"}}}
        assert (
            get_value_from_nested_structure_by_path_list(data, "node_x.userFields.query")
            == "hi"
        )

    @staticmethod
    def test_list_index_path():
        data = {"node_x": {"items": [{"name": "a"}, {"name": "b"}]}}
        assert (
            get_value_from_nested_structure_by_path_list(data, "node_x.items[1].name")
            == "b"
        )

    @staticmethod
    def test_missing_dict_key_returns_none():
        data = {"node_x": {"userFields": {}}}
        assert (
            get_value_from_nested_structure_by_path_list(data, "node_x.userFields.query")
            is None
        )

    @staticmethod
    def test_index_out_of_range_returns_none():
        data = {"node_x": {"items": [{"name": "a"}]}}
        assert get_value_from_nested_structure_by_path_list(data, "node_x.items[3]") is None
