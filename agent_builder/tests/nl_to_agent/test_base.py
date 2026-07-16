#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

"""OperatorInput 与 OperatorOutput 数据类单元测试"""

from agent_builder.nl_to_agent.base import OperatorInput, OperatorOutput


class TestOperatorInput:

    @staticmethod
    def test_default_values_all_none():
        inp = OperatorInput()
        assert inp.query is None
        assert inp.plugin_info is None
        assert inp.knowledge_info is None
        assert inp.sub_workflow_info is None

    @staticmethod
    def test_assignment_and_attribute_access():
        inp = OperatorInput()
        inp.query = "hello"
        inp.plugin_info = [{"id": 1}]
        inp.knowledge_info = [{"name": "kb"}]
        inp.sub_workflow_info = [{"wf": "x"}]
        assert inp.query == "hello"
        assert inp.plugin_info == [{"id": 1}]
        assert inp.knowledge_info == [{"name": "kb"}]
        assert inp.sub_workflow_info == [{"wf": "x"}]

    @staticmethod
    def test_all_fields_populated():
        inp = OperatorInput(
            query="test query",
            plugin_info=[{"plugin": "p1"}],
            knowledge_info=[{"knowledge": "k1"}],
            sub_workflow_info=[{"workflow": "w1"}],
        )
        assert inp.query == "test query"
        assert inp.plugin_info == [{"plugin": "p1"}]
        assert inp.knowledge_info == [{"knowledge": "k1"}]
        assert inp.sub_workflow_info == [{"workflow": "w1"}]

    @staticmethod
    def test_partial_fields_populated():
        inp = OperatorInput(query="only query")
        assert inp.query == "only query"
        assert inp.plugin_info is None
        assert inp.knowledge_info is None
        assert inp.sub_workflow_info is None

    @staticmethod
    def test_reassign_fields():
        inp = OperatorInput(query="old")
        inp.query = "new"
        assert inp.query == "new"

    @staticmethod
    def test_equality_same_values():
        a = OperatorInput(query="q", plugin_info=[1])
        b = OperatorInput(query="q", plugin_info=[1])
        assert a == b

    @staticmethod
    def test_equality_different_values():
        a = OperatorInput(query="q1")
        b = OperatorInput(query="q2")
        assert a != b


class TestOperatorOutput:

    @staticmethod
    def test_result_field():
        out = OperatorOutput(result="done")
        assert out.result == "done"

    @staticmethod
    def test_result_empty_string():
        out = OperatorOutput(result="")
        assert out.result == ""

    @staticmethod
    def test_equality_same_result():
        a = OperatorOutput(result="ok")
        b = OperatorOutput(result="ok")
        assert a == b

    @staticmethod
    def test_equality_different_result():
        a = OperatorOutput(result="a")
        b = OperatorOutput(result="b")
        assert a != b


if __name__ == "__main__":
    pytest.main([__file__, "-v"])