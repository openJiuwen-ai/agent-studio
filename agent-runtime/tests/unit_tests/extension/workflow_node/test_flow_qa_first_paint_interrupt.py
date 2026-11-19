# Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
# pylint: disable=protected-access
"""FlowQA 首问必须中断：父工作流 INTERACTIVE_INPUT 残留不得跳过 GraphInterrupt。"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from openjiuwen.core.common.constants.constant import USER_FIELDS
from openjiuwen.core.graph.pregel import GraphInterrupt

from jiuwen.extension.workflow_node.flow_qa import FlowQA

pytestmark = pytest.mark.asyncio


def _make_session() -> MagicMock:
    session = MagicMock()
    session.get_component_id.return_value = "node_qa"
    session.get_workflow_id.return_value = "wf_param_check"
    session.get_session_id.return_value = "sess-1"
    session.get_state.return_value = {}
    session.update_state = MagicMock()
    state = MagicMock()
    state.update_and_commit_workflow_state = MagicMock()
    state.commit = MagicMock()
    session._inner.state.return_value = state
    session._interaction = object()  # 模拟已有 interaction 缓存
    session.write_custom_stream = AsyncMock()
    return session


class TestFlowQAFirstPaintInterrupt:
    async def test_start_forces_interrupt_when_interact_returns_residual(self):
        """父 raw_inputs 泄漏时 interact 直接返回，START 仍须 GraphInterrupt。"""
        qa = FlowQA(
            {
                "name": "调用后台预处理接口",
                "needReply": True,
                "qaStrategy": "index",
                "options": ['{"txType":"002","remitData":{}}'],
                "isStructMessage": False,
                "enable_history": False,
            }
        )
        session = _make_session()
        # 第一次：残留输入被当成回复返回；第二次：真正中断
        session.interact = AsyncMock(
            side_effect=["零花钱卡", GraphInterrupt(("forced",))]
        )

        with pytest.raises(GraphInterrupt):
            await qa.invoke(
                {USER_FIELDS: {"index": 0}},
                session,
                MagicMock(),
            )

        assert session.interact.await_count == 2
        # 静态图复用下执行期状态走 ContextVar 通道（finally 复位防跨执行串扰），
        # invoke 返回后逃逸面不可再读；执行后状态以 session 持久化真源为准：
        # START 轮中断发生前应已把 USER_INTERACT 状态存入 session
        stored = [
            c.args[0]["flow_qa_state"]
            for c in session.update_state.call_args_list
            if c.args and "flow_qa_state" in c.args[0]
        ]
        assert stored and stored[-1]["status"] == "user_interact"
        # （原 ``qa.should_interrupt()`` 断言与上同义：逃逸面在 invoke 返回后
        # 已随 ContextVar 通道复位，该状态改由 session 真源断言承载）

    async def test_start_interrupt_on_first_interact(self):
        """正常路径：第一次 interact 即 GraphInterrupt。"""
        qa = FlowQA(
            {
                "needReply": True,
                "qaStrategy": "index",
                "options": ["hello"],
            }
        )
        session = _make_session()
        session.interact = AsyncMock(side_effect=GraphInterrupt(("ok",)))

        with pytest.raises(GraphInterrupt):
            await qa.invoke({USER_FIELDS: {"index": 0}}, session, MagicMock())

        assert session.interact.await_count == 1

    async def test_resume_rejects_empty_response(self):
        """合法恢复若拿到空串，不得把空 response 交给下游 Code。"""
        from jiuwen.extension.workflow_node.flow_qa import (
            ExecutionStatus,
            QAState,
        )
        from openjiuwen.core.common.exception.errors import BaseError

        qa = FlowQA(
            {
                "needReply": True,
                "qaStrategy": "index",
                "options": ['{"ok":1}'],
            }
        )
        qa._node_state = QAState(
            status=ExecutionStatus.USER_INTERACT,
            question='{"ok":1}',
            inputs={},
        )
        session = _make_session()
        # 伪装已有 flow_qa_state，走 USER_INTERACT 分支
        session.get_state.return_value = {
            "flow_qa_state": {
                "status": "user_interact",
                "inputs": {},
                "question": '{"ok":1}',
            }
        }
        session.interact = AsyncMock(return_value="   ")

        with pytest.raises(BaseError) as ei:
            await qa.invoke({USER_FIELDS: {"index": 0}}, session, MagicMock())
        assert "empty" in str(ei.value).lower() or "空" in str(ei.value)