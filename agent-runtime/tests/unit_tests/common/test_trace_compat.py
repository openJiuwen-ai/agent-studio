# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""trace_compat 单元测试 — 验证 trace_id 透传兼容层的行为。

测试场景：
1. 底层不支持 trace_id（当前 0.1.16）→ 不传 trace_id，session 正常创建
2. 底层支持 trace_id（mock 签名）→ 透传 trace_id
3. get_x_request_id() 为空 → 不传 trace_id
"""

import unittest
from unittest.mock import patch, MagicMock

from agent_runtime.common.trace_compat import (
    create_agent_session_with_trace,
    create_workflow_session_with_trace,
    _agent_accepts_trace_id,
    _wf_accepts_trace_id,
)


class TraceCompatTest(unittest.IsolatedAsyncioTestCase):
    """create_*_session_with_trace 兼容层测试。"""

    def test_agent_session_created_without_trace_id_on_old_version(self):
        """底层不支持时，create_agent_session_with_trace 仍能正常创建 session。"""
        if _agent_accepts_trace_id:
            self.skipTest("底层已支持 trace_id，跳过旧版本兼容测试")
        # 不设置 jiuwen context，get_x_request_id() 返回空串
        session = create_agent_session_with_trace(session_id="test-agent-1")
        self.assertIsNotNone(session)

    def test_workflow_session_created_without_trace_id_on_old_version(self):
        """底层不支持时，create_workflow_session_with_trace 仍能正常创建 session。"""
        if _wf_accepts_trace_id:
            self.skipTest("底层已支持 trace_id，跳过旧版本兼容测试")
        session = create_workflow_session_with_trace(session_id="test-wf-1")
        self.assertIsNotNone(session)

    def test_agent_session_trace_id_passed_when_supported(self):
        """底层支持时，trace_id 从 get_x_request_id() 透传到 create_agent_session。"""
        test_trace_id = "abc123def456"
        with patch(
            "agent_runtime.common.trace_compat._agent_accepts_trace_id", True
        ), patch(
            "agent_runtime.common.trace_compat.get_x_request_id",
            return_value=test_trace_id,
        ), patch(
            "agent_runtime.common.trace_compat._create_agent_session"
        ) as mock_create:
            mock_create.return_value = MagicMock()
            create_agent_session_with_trace(session_id="test-agent-2", card=None)
            mock_create.assert_called_once_with(
                session_id="test-agent-2", card=None, trace_id=test_trace_id
            )

    def test_workflow_session_trace_id_passed_when_supported(self):
        """底层支持时，trace_id 从 get_x_request_id() 透传到 create_workflow_session。"""
        test_trace_id = "wf789xyz012"
        with patch(
            "agent_runtime.common.trace_compat._wf_accepts_trace_id", True
        ), patch(
            "agent_runtime.common.trace_compat.get_x_request_id",
            return_value=test_trace_id,
        ), patch(
            "agent_runtime.common.trace_compat._create_workflow_session"
        ) as mock_create:
            mock_create.return_value = MagicMock()
            create_workflow_session_with_trace(session_id="test-wf-2", envs={"k": "v"})
            mock_create.assert_called_once_with(
                session_id="test-wf-2", envs={"k": "v"}, trace_id=test_trace_id
            )

    def test_no_trace_id_passed_when_request_id_empty(self):
        """get_x_request_id() 为空时，不传 trace_id。"""
        with patch(
            "agent_runtime.common.trace_compat._wf_accepts_trace_id", True
        ), patch(
            "agent_runtime.common.trace_compat.get_x_request_id", return_value=""
        ), patch(
            "agent_runtime.common.trace_compat._create_workflow_session"
        ) as mock_create:
            mock_create.return_value = MagicMock()
            create_workflow_session_with_trace(session_id="test-wf-3")
            # trace_id 不应在 kwargs 中
            call_kwargs = mock_create.call_args.kwargs
            self.assertNotIn("trace_id", call_kwargs)

    def test_extra_kwargs_forwarded(self):
        """额外的 kwargs 透传到底层函数。"""
        with patch(
            "agent_runtime.common.trace_compat._wf_accepts_trace_id", False
        ), patch(
            "agent_runtime.common.trace_compat._create_workflow_session"
        ) as mock_create:
            mock_create.return_value = MagicMock()
            create_workflow_session_with_trace(
                session_id="test-wf-4", envs={"x": 1}
            )
            mock_create.assert_called_once_with(
                session_id="test-wf-4", envs={"x": 1}
            )


if __name__ == "__main__":
    unittest.main()
