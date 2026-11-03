# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Tests for MessageConverter.create_workflow_completion_message 消息 key。

背景 bug：content 的 key 误写为全角冒号 ``"workflow_id："``，所有按
``"workflow_id"`` 读取该消息的消费方（控制器消息路由 / 调试信息组装）都取到
None，工作流完成事件中的 workflow_id 恒丢失。
"""

from jiuwen.controller.context_manager.workflow_context import WorkflowContext
from jiuwen.controller.utils.utils import MessageConverter


def _build_context():
    return WorkflowContext(
        workflow_id="wf-123",
        workflow_name="demo-flow",
        description="",
    )


class TestWorkflowCompletionMessageKeys:
    @staticmethod
    def test_content_keys_are_canonical():
        message = MessageConverter.create_workflow_completion_message(
            _build_context(), exec_res={"result": "ok"}
        )
        assert set(message.content.keys()) == {
            "workflow_name",
            "workflow_id",
            "workflow_type",
            "exec_res",
        }

    @staticmethod
    def test_workflow_id_value_readable():
        message = MessageConverter.create_workflow_completion_message(
            _build_context(), exec_res={}
        )
        assert message.content["workflow_id"] == "wf-123"
        assert message.content["workflow_name"] == "demo-flow"
