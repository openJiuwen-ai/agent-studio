# Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
"""WorkflowWrapper 异常上报不得再因内建异常无 .code 而二次翻车。"""

from __future__ import annotations

from jiuwen.extension.wrapper.workflow_wrapper import WorkflowWrapper


class TestFormatStreamException:
    @staticmethod
    def test_typeerror_without_code_keeps_root_message():
        code, msg = WorkflowWrapper.format_stream_exception(
            TypeError("argument of type 'NoneType' is not iterable")
        )
        assert code == -1
        assert "NoneType" in msg
        assert "has no attribute" not in msg

    @staticmethod
    def test_jiuwen_exception_uses_error_code():
        from jiuwen.extension.workflow_node.utils import JiuWenBaseException

        exc = JiuWenBaseException(error_code=121007, message="业务失败")
        code, msg = WorkflowWrapper.format_stream_exception(exc)
        assert code == 121007
        assert msg == "业务失败"
