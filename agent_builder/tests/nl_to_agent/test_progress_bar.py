#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

"""progress_bar 单元测试"""

import pytest
from agent_builder.nl_to_agent.workflow_agent.progress_bar import (
    MESSAGE_TYPE,
    ANSWER,
    STATUS,
    RESULT,
    PROCESS,
    CONTENT,
    SOP,
    MERMAID,
    WORKFLOW_AGENT_DL,
    WORKFLOW_AGENT_IR,
    MODIFY_PROMPT,
    CHITCHAT,
    QUESTION,
    LLM_AGENT_IR,
    QUESTION_WITHOUT_OPTION,
    MERMAID_CHUNK,
    SOP_CHUNK,
    CHITCHAT_CHUNK,
    LLM_AGENT_IR_CHUNK,
    HD0,
    HD1,
    HD2,
    HD3,
    HD4,
    NODE_PROCESS,
    status_msg,
    progress_msg,
    content_msg,
    result_msg,
    mermaid_msg,
    modify_msg,
    HD0_INIT,
    HD0_SOP_JUDGE,
    HD0_CREATE_SOP,
    HD0_TRANSFORM_SOP,
    HD1_DESIGN_SOP,
    HD2_DESIGN_MERMAID,
    HD3_MODIFY_MERMAID,
    HD4_CREATE_DL,
    HD4_VERIFY_DL,
    HD4_CREATE_DSL,
    AGENT_HD0,
    AGENT_HD1,
    AGENT_HD2,
    AGENT_HD3,
    AGENT_HD4,
)


class TestConstants:
    """常量值验证测试"""

    @staticmethod
    def test_base_constants():
        assert MESSAGE_TYPE == "message_type"
        assert ANSWER == "answer"
        assert STATUS == "status"
        assert RESULT == "result"
        assert PROCESS == "progress"
        assert CONTENT == "content"

    @staticmethod
    def test_result_type_constants():
        assert SOP == "sop"
        assert MERMAID == "mermaid"
        assert WORKFLOW_AGENT_DL == "workflow_agent_dl"
        assert WORKFLOW_AGENT_IR == "workflow_agent_ir"
        assert MODIFY_PROMPT == "modify_prompt"
        assert CHITCHAT == "chitchat"
        assert QUESTION == "question"
        assert LLM_AGENT_IR == "llm_agent_ir"
        assert QUESTION_WITHOUT_OPTION == "question_no_opt"

    @staticmethod
    def test_content_type_constants():
        assert MERMAID_CHUNK == "mermaid_chunk"
        assert SOP_CHUNK == "sop_chunk"
        assert CHITCHAT_CHUNK == "chitchat_chunk"
        assert LLM_AGENT_IR_CHUNK == "llm_agent_ir_chunk"

    @staticmethod
    def test_workflow_status_constants():
        assert HD0 == "state_0"
        assert HD1 == "state_1"
        assert HD2 == "state_2"
        assert HD3 == "state_3"
        assert HD4 == "state_4"

    @staticmethod
    def test_progress_constant():
        assert NODE_PROCESS == "node_process"

    @staticmethod
    def test_agent_status_constants():
        assert AGENT_HD0 == "state_0"
        assert AGENT_HD1 == "state_1"
        assert AGENT_HD2 == "state_2"
        assert AGENT_HD3 == "state_3"
        assert AGENT_HD4 == "state_4"


class TestStatusMsg:
    """status_msg 函数测试"""

    @staticmethod
    def test_basic_status_message():
        result = status_msg("测试消息", "state_0")
        assert result == {
            "type_label": STATUS,
            "answer": "测试消息",
            "message_type": "state_0",
            "status_id": "null",
        }

    @staticmethod
    def test_status_message_with_custom_status_id():
        result = status_msg("测试消息", "state_1", "CUSTOM_ID")
        assert result["status_id"] == "CUSTOM_ID"

    @staticmethod
    def test_status_message_type_label_is_status():
        result = status_msg("任意消息", "any_type", "any_id")
        assert result["type_label"] == STATUS

    @staticmethod
    def test_status_message_default_status_id():
        result = status_msg("消息", "type")
        assert result["status_id"] == "null"


class TestProgressMsg:
    """progress_msg 函数测试"""

    @staticmethod
    def _make_node(node_id="node_1", node_type="llm", parameters=None, next_nodes=None):
        if parameters is None:
            parameters = {"key": "val"}
        if next_nodes is None:
            next_nodes = ["node_2"]
        return {"id": node_id, "type": node_type, "parameters": parameters, "next": next_nodes}

    @staticmethod
    def test_basic_progress_message():
        node = TestProgressMsg._make_node()
        result = progress_msg(node, 2, 5, 10, 0.4)
        assert result["type_label"] == PROCESS
        assert result["message_type"] == NODE_PROCESS
        assert result["progress"] == 0.4
        assert "已生成节点: node_1 (llm)" == result["answer"]

    @staticmethod
    def test_progress_details_fields():
        node = TestProgressMsg._make_node()
        result = progress_msg(node, 2, 5, 10, 0.4)
        details = result["details"]
        assert details["generated_count"] == 2
        assert details["elapsed_time"] == 10
        assert details["total_num"] == 5
        assert "remaining_time" in details
        assert "node" in details

    @staticmethod
    def test_progress_node_details():
        node = TestProgressMsg._make_node(node_id="n1", node_type="code", parameters={"p": 1}, next_nodes=["n2"])
        result = progress_msg(node, 1, 3, 5, 0.33)
        node_detail = result["details"]["node"]
        assert node_detail["id"] == "n1"
        assert node_detail["type"] == "code"
        assert node_detail["parameters"] == {"p": 1}
        assert node_detail["next"] == ["n2"]

    @staticmethod
    def test_progress_remaining_time_normal():
        node = TestProgressMsg._make_node()
        result = progress_msg(node, 2, 5, 10, 0.4)
        avg_time = 10 / 2
        expected_remaining = int(avg_time * 3)
        assert result["details"]["remaining_time"] == expected_remaining

    @staticmethod
    def test_progress_remaining_time_zero_generated():
        node = TestProgressMsg._make_node()
        result = progress_msg(node, 0, 5, 0, 0.0)
        assert result["details"]["remaining_time"] == 0

    @staticmethod
    def test_progress_remaining_time_all_generated():
        node = TestProgressMsg._make_node()
        result = progress_msg(node, 5, 5, 10, 1.0)
        assert result["details"]["remaining_time"] == 0

    @staticmethod
    def test_progress_remaining_time_integer_truncation():
        node = TestProgressMsg._make_node()
        result = progress_msg(node, 3, 5, 10, 0.6)
        avg_time = 10 / 3
        expected = int(avg_time * 2)
        assert result["details"]["remaining_time"] == expected
        assert isinstance(result["details"]["remaining_time"], int)

    @staticmethod
    def test_progress_node_missing_keys():
        node = {}
        result = progress_msg(node, 1, 3, 5, 0.33)
        node_detail = result["details"]["node"]
        assert node_detail["id"] == "null"
        assert node_detail["type"] == "null"
        assert node_detail["parameters"] == "null"
        assert node_detail["next"] == "null"

    @staticmethod
    def test_progress_node_partial_keys():
        node = {"id": "n1", "type": "llm"}
        result = progress_msg(node, 1, 3, 5, 0.33)
        node_detail = result["details"]["node"]
        assert node_detail["id"] == "n1"
        assert node_detail["type"] == "llm"
        assert node_detail["parameters"] == "null"
        assert node_detail["next"] == "null"

    @staticmethod
    def test_progress_answer_format():
        node = TestProgressMsg._make_node(node_id="my_node", node_type="api")
        result = progress_msg(node, 1, 2, 3, 0.5)
        assert result["answer"] == "已生成节点: my_node (api)"


class TestContentMsg:
    """content_msg 函数测试"""

    @staticmethod
    def test_basic_content_message():
        result = content_msg("流式内容", "mermaid_chunk")
        assert result == {
            "type_label": CONTENT,
            "answer": "流式内容",
            "message_type": "mermaid_chunk",
        }

    @staticmethod
    def test_content_message_type_label():
        result = content_msg("任意内容", "any_type")
        assert result["type_label"] == CONTENT

    @staticmethod
    def test_content_message_with_empty_answer():
        result = content_msg("", "sop_chunk")
        assert result["answer"] == ""


class TestResultMsg:
    """result_msg 函数测试"""

    @staticmethod
    def test_basic_result_message():
        result = result_msg("最终结果", "sop")
        assert result == {
            "type_label": RESULT,
            "answer": "最终结果",
            "message_type": "sop",
        }

    @staticmethod
    def test_result_message_type_label():
        result = result_msg("结果", "mermaid")
        assert result["type_label"] == RESULT

    @staticmethod
    def test_result_message_with_dict_answer():
        data = {"workflow": "definition"}
        result = result_msg(data, "workflow_agent_dl")
        assert result["answer"] == data


class TestMermaidMsg:
    """mermaid_msg 函数测试"""

    @staticmethod
    def test_basic_mermaid_message():
        info = {"nodes": [], "edges": []}
        result = mermaid_msg("流程图结果", "mermaid", info)
        assert result == {
            "type_label": RESULT,
            "answer": "流程图结果",
            "message_type": "mermaid",
            "mermaid_info": info,
        }

    @staticmethod
    def test_mermaid_message_type_label():
        result = mermaid_msg("msg", "mermaid", {})
        assert result["type_label"] == RESULT

    @staticmethod
    def test_mermaid_message_with_string_info():
        result = mermaid_msg("msg", "mermaid", "graph TD; A-->B;")
        assert result["mermaid_info"] == "graph TD; A-->B;"

    @staticmethod
    def test_mermaid_message_with_complex_info():
        info = {"nodes": [{"id": "A"}], "edges": [{"from": "A", "to": "B"}]}
        result = mermaid_msg("msg", "mermaid", info)
        assert result["mermaid_info"] == info


class TestModifyMsg:
    """modify_msg 函数测试"""

    @staticmethod
    def test_basic_modify_message():
        result = modify_msg("修改结果", "modify_prompt", 2, 5)
        assert result == {
            "type_label": RESULT,
            "answer": "修改结果",
            "message_type": "modify_prompt",
            "current_turn": 2,
            "max_turn": 5,
        }

    @staticmethod
    def test_modify_message_type_label():
        result = modify_msg("msg", "modify_prompt", 1, 3)
        assert result["type_label"] == RESULT

    @staticmethod
    def test_modify_message_turn_values():
        result = modify_msg("msg", "modify_prompt", 3, 10)
        assert result["current_turn"] == 3
        assert result["max_turn"] == 10

    @staticmethod
    def test_modify_message_zero_turn():
        result = modify_msg("msg", "modify_prompt", 0, 5)
        assert result["current_turn"] == 0
        assert result["max_turn"] == 5


class TestPredefinedStatusMessages:
    """预定义状态消息验证测试"""

    @staticmethod
    def _assert_status_msg_structure(msg, expected_answer, expected_msg_type, expected_status_id):
        assert msg["type_label"] == STATUS
        assert msg["answer"] == expected_answer
        assert msg["message_type"] == expected_msg_type
        assert msg["status_id"] == expected_status_id

    @staticmethod
    def test_hd0_init():
        TestPredefinedStatusMessages._assert_status_msg_structure(
            HD0_INIT, "已接受用户输入，准备开始", HD0, "HD0_INIT"
        )

    @staticmethod
    def test_hd0_sop_judge():
        TestPredefinedStatusMessages._assert_status_msg_structure(
            HD0_SOP_JUDGE, "正在根据用户输入是否需要构造SOP", HD0, "HD0_SOP_JUDGE"
        )

    @staticmethod
    def test_hd0_create_sop():
        TestPredefinedStatusMessages._assert_status_msg_structure(
            HD0_CREATE_SOP, "用户未提供SOP，正在创建SOP", HD0, "HD0_CREATE_SOP"
        )

    @staticmethod
    def test_hd0_transform_sop():
        TestPredefinedStatusMessages._assert_status_msg_structure(
            HD0_TRANSFORM_SOP, "用户已经提供SOP，正在优化用户SOP", HD0, "HD0_TRANSFORM_SOP"
        )

    @staticmethod
    def test_hd1_design_sop():
        TestPredefinedStatusMessages._assert_status_msg_structure(
            HD1_DESIGN_SOP, "开始构建用户SOP", HD1, "HD1_DESIGN_SOP"
        )

    @staticmethod
    def test_hd2_design_mermaid():
        TestPredefinedStatusMessages._assert_status_msg_structure(
            HD2_DESIGN_MERMAID, "开始构建工作流流程图", HD2, "HD2_DESIGN_MERMAID"
        )

    @staticmethod
    def test_hd3_modify_mermaid():
        TestPredefinedStatusMessages._assert_status_msg_structure(
            HD3_MODIFY_MERMAID, "正在根据用户输入修改流程图", HD3, "HD3_MODIFY_MERMAID"
        )

    @staticmethod
    def test_hd4_create_dl():
        TestPredefinedStatusMessages._assert_status_msg_structure(
            HD4_CREATE_DL, "正在根据流程图创建工作流", HD4, "HD4_CREATE_DL"
        )

    @staticmethod
    def test_hd4_verify_dl():
        TestPredefinedStatusMessages._assert_status_msg_structure(
            HD4_VERIFY_DL, "WorkflowDL已生成，正在校验格式", HD4, "HD4_VERIFY_DL"
        )

    @staticmethod
    def test_hd4_create_dsl():
        TestPredefinedStatusMessages._assert_status_msg_structure(
            HD4_CREATE_DSL, "校验通过正在创建工作流", HD4, "HD4_CREATE_DSL"
        )

    @staticmethod
    def test_all_predefined_messages_are_dicts():
        messages = [
            HD0_INIT, HD0_SOP_JUDGE, HD0_CREATE_SOP, HD0_TRANSFORM_SOP,
            HD1_DESIGN_SOP, HD2_DESIGN_MERMAID, HD3_MODIFY_MERMAID,
            HD4_CREATE_DL, HD4_VERIFY_DL, HD4_CREATE_DSL,
        ]
        for msg in messages:
            assert isinstance(msg, dict)

    @staticmethod
    def test_all_predefined_messages_have_required_keys():
        required_keys = {"type_label", "answer", "message_type", "status_id"}
        messages = [
            HD0_INIT, HD0_SOP_JUDGE, HD0_CREATE_SOP, HD0_TRANSFORM_SOP,
            HD1_DESIGN_SOP, HD2_DESIGN_MERMAID, HD3_MODIFY_MERMAID,
            HD4_CREATE_DL, HD4_VERIFY_DL, HD4_CREATE_DSL,
        ]
        for msg in messages:
            assert set(msg.keys()) == required_keys


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
