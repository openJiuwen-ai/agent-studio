#  !/usr/bin/env python
#  -*- coding: UTF-8 -*-
#  Copyright c) Huawei Technologies Co., Ltd. 2025-2025

# pylint: disable=protected-access
"""验证 loop body 里 QA 能从 session 父链读到 conversationHistory 的修复。

背景: LoopComponent.invoke 没有把 context 传给 loop body 图，
导致 body 图的 Vertex context=None。QA 在 body 里调
_get_latest_chat_history(context) 时 context=None，拿不到对话历史，
LLM 只看到最后一条用户回复（如"可以"），提取不到 city 字段 → 追问 →
interaction required。

不能直接传 context=context，会跟同事的并行数据隔离 fix（67595d7e）
冲突——传 context 后 body 图的所有节点共享父级 ModelContext，
导致 intent 检测等子工作流数据串了。

修复: 不传 context，改为 patch
QuestionerDirectReplyHandler._get_latest_chat_history，在 context=None
时沿 session._inner.parent() 父链向上找
io_state.global_variables.sys.conversationHistory（Start 节点在顶层
session 写的）。这样 QA 只读 session 级状态，不走 context 共享，
不跟并行数据隔离 fix 冲突。

测试覆盖:
1. context=None + get_state_info 抛异常 → 兜底用 self._query（不崩溃）
2. context=None + 没有历史 → 兜底用 self._query
3. context 有值但返回空 → fallback 到 session 父链（通过 mock get_state_info 验证）
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# 触发 agent_runtime.common 子模块挂到 agent_runtime 上，否则
# unittest.mock.patch("agent_runtime.common.session_state_access.get_state_info")
# 会因 getattr(agent_runtime, "common") 失败而 AttributeError
import agent_runtime.common.session_state_access  # noqa: F401
import jiuwen.extension.patches.workflow_sub_stream_patch  # noqa: F401

pytestmark = pytest.mark.asyncio


def _make_handler(session, query="", with_chat_history=False):
    """构造一个最小可用的 QuestionerDirectReplyHandler 实例。"""
    from agent_runtime.extension.workflow_node.questioner import (
        QuestionerDirectReplyHandler,
        QuestionerConfig,
        QuestionerState,
        ExecutionStatus,
    )

    handler = QuestionerDirectReplyHandler()
    config = MagicMock(spec=QuestionerConfig)
    config.with_chat_history = with_chat_history
    config.chat_history_max_rounds = 5
    handler._config = config
    handler._session = session
    handler._query = query
    handler._state = MagicMock(spec=QuestionerState)
    handler._state.status = ExecutionStatus.USER_INTERACT
    handler._state.response_num = 0
    handler._state.question = "test question"
    return handler


def _make_session_mock():
    """构造一个 mock session，_inner 有 parent 链。"""
    parent_inner = MagicMock()
    parent_inner.parent.return_value = None
    body_inner = MagicMock()
    body_inner.parent.return_value = parent_inner
    session = MagicMock()
    session._inner = body_inner
    return session


class TestQAGetLatestChatHistoryFallback:
    """验证 patched _get_latest_chat_history 的 fallback 逻辑。"""

    async def test_context_none_no_history_fallback_to_query(self):
        """context=None + 没有历史 → 兜底用 self._query。"""
        from jiuwen.extension.patches.workflow_sub_stream_patch import (
            apply_workflow_sub_stream_patch,
        )
        apply_workflow_sub_stream_patch()

        from agent_runtime.extension.workflow_node.questioner import (
            QuestionerDirectReplyHandler,
        )

        session = _make_session_mock()
        handler = _make_handler(session, query="可以的", with_chat_history=True)

        # get_state_info 在所有层都返回空
        with patch(
            "agent_runtime.common.session_state_access.get_state_info",
            return_value={},
        ):
            result = await handler._get_latest_chat_history(context=None)

        assert len(result) == 1
        assert result[0].role == "user"
        assert result[0].content == "可以的"

    async def test_context_none_with_history_from_parent(self):
        """context=None + 父链有 conversationHistory → 返回完整对话历史。

        通过 monkey-patch get_state_info 函数本身来模拟父链返回的数据。
        patch 应用在 apply_workflow_sub_stream_patch 调用前，
        这样 closure 捕获的 get_state_info 就是被 mock 过的版本。
        """
        conv_history = [
            {"role": "user", "content": "北京"},
            {"role": "assistant", "content": "北京可以吗?"},
            {"role": "user", "content": "可以"},
        ]
        io_state = {
            "global_variables": {
                "sys": {"conversationHistory": conv_history}
            }
        }

        # 先 mock get_state_info，再 apply patch（closure 会捕获 mock 版本）
        call_count = [0]

        def mock_get_state_info(session, key=None):
            call_count[0] += 1
            if call_count[0] == 1:
                return {}  # body session 空
            return io_state  # parent session 有历史

        with patch(
            "agent_runtime.common.session_state_access.get_state_info",
            mock_get_state_info,
        ):
            from jiuwen.extension.patches.workflow_sub_stream_patch import (
                apply_workflow_sub_stream_patch,
            )
            # 重置 _PATCH_APPLIED 让 patch 重新 apply（这次会捕获 mock 版本）
            import jiuwen.extension.patches.workflow_sub_stream_patch as pmod
            pmod._PATCH_APPLIED = False
            apply_workflow_sub_stream_patch()

            from agent_runtime.extension.workflow_node.questioner import (
                QuestionerDirectReplyHandler,
            )

            session = _make_session_mock()
            handler = _make_handler(session, query="可以", with_chat_history=True)

            result = await handler._get_latest_chat_history(context=None)

        assert len(result) == 3
        assert result[0].role == "user"
        assert result[0].content == "北京"
        assert result[1].role == "assistant"
        assert result[1].content == "北京可以吗?"
        assert result[2].role == "user"
        assert result[2].content == "可以"

    async def test_context_present_but_empty_fallback_to_session(self):
        """context 有值但返回空消息 → fallback 到 session 父链。"""
        conv_history = [
            {"role": "user", "content": "从session读到的历史"},
        ]
        io_state = {
            "global_variables": {
                "sys": {"conversationHistory": conv_history}
            }
        }

        call_count = [0]

        def mock_get_state_info(session, key=None):
            call_count[0] += 1
            if call_count[0] == 1:
                return {}
            return io_state

        with patch(
            "agent_runtime.common.session_state_access.get_state_info",
            mock_get_state_info,
        ):
            import jiuwen.extension.patches.workflow_sub_stream_patch as pmod
            pmod._PATCH_APPLIED = False
            from jiuwen.extension.patches.workflow_sub_stream_patch import (
                apply_workflow_sub_stream_patch,
            )
            apply_workflow_sub_stream_patch()

            from agent_runtime.extension.workflow_node.questioner import (
                QuestionerDirectReplyHandler,
            )

            session = _make_session_mock()
            handler = _make_handler(session, query="test", with_chat_history=True)

            mock_context = MagicMock()
            mock_context_window = MagicMock()
            mock_context_window.get_messages.return_value = []
            mock_context.get_context_window = AsyncMock(return_value=mock_context_window)

            result = await handler._get_latest_chat_history(context=mock_context)

        assert len(result) == 1
        assert result[0].content == "从session读到的历史"
