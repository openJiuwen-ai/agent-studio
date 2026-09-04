# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""trace_id 透传集成测试 — 验证 runner 调用时正确传递 trace_id"""

import unittest
from unittest.mock import patch, MagicMock, AsyncMock


class TestTraceIdPassthrough(unittest.IsolatedAsyncioTestCase):
    """验证各 runner 调用时正确传递 trace_id"""

    async def test_trace_compat_detects_trace_id_support(self):
        """trace_compat should correctly detect if underlying API supports trace_id."""
        from agent_runtime.common.trace_compat import (
            _agent_accepts_trace_id,
            _wf_accepts_trace_id,
        )
        self.assertIsInstance(_agent_accepts_trace_id, bool)
        self.assertIsInstance(_wf_accepts_trace_id, bool)

    async def test_create_agent_session_with_trace_passes_trace_id_when_supported(self):
        """create_agent_session_with_trace should pass trace_id when API supports it."""
        from agent_runtime.common.trace_compat import (
            create_agent_session_with_trace,
            _agent_accepts_trace_id,
        )

        if not _agent_accepts_trace_id:
            self.skipTest("Underlying API does not support trace_id")

        test_trace_id = "aabbccdd11223344556677889900ff00"

        with patch("agent_runtime.common.trace_compat.get_x_request_id", return_value=test_trace_id), \
             patch("agent_runtime.common.trace_compat._create_agent_session") as mock_create:
            mock_create.return_value = MagicMock()
            create_agent_session_with_trace(session_id="test-session", card=None)

            call_kwargs = mock_create.call_args.kwargs
            self.assertIn("trace_id", call_kwargs)
            self.assertEqual(call_kwargs["trace_id"], test_trace_id)

    async def test_create_workflow_session_with_trace_passes_trace_id_when_supported(self):
        """create_workflow_session_with_trace should pass trace_id when API supports it."""
        from agent_runtime.common.trace_compat import (
            create_workflow_session_with_trace,
            _wf_accepts_trace_id,
        )

        if not _wf_accepts_trace_id:
            self.skipTest("Underlying API does not support trace_id")

        test_trace_id = "11223344556677889900aabbccddeeff"

        with patch("agent_runtime.common.trace_compat.get_x_request_id", return_value=test_trace_id), \
             patch("agent_runtime.common.trace_compat._create_workflow_session") as mock_create:
            mock_create.return_value = MagicMock()
            create_workflow_session_with_trace(session_id="test-wf-session", envs={"key": "val"})

            call_kwargs = mock_create.call_args.kwargs
            self.assertIn("trace_id", call_kwargs)
            self.assertEqual(call_kwargs["trace_id"], test_trace_id)

    async def test_create_session_without_trace_id_when_not_supported(self):
        """When API doesn't support trace_id, session should be created without it."""
        from agent_runtime.common.trace_compat import (
            create_workflow_session_with_trace,
            _wf_accepts_trace_id,
        )

        if _wf_accepts_trace_id:
            self.skipTest("Underlying API already supports trace_id")

        with patch("agent_runtime.common.trace_compat.get_x_request_id", return_value="some-id"):
            session = create_workflow_session_with_trace(session_id="test-no-trace")
            self.assertIsNotNone(session)


if __name__ == "__main__":
    unittest.main()
