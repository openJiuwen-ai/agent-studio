# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""execution_session_ctx：studio 侧执行期状态 ContextVar 通道单测。

执行期 session/context 通道已归上游（``openjiuwen.core.session.
execution_session_ctx``），本模块只保留 studio 专用通道，故此处只钉这两个：

- ``_stream_final_output``：流式末帧输出，**不 reset**（引擎
  ``Vertex._post_stream`` 在 generator 耗尽后读取）；
- ``_component_state``：组件执行期状态对象，set + token 式 reset。
"""
import pytest

from jiuwen.extension.workflow import execution_session_ctx as ctx


class TestStreamFinalOutputChannel:
    @staticmethod
    def test_set_without_reset_is_visible():
        # 语义：不 reset——引擎 Vertex._post_stream 在 generator 耗尽后读取
        ctx.set_stream_final_output({"userFields": "x"})
        assert ctx.get_stream_final_output() == {"userFields": "x"}
        ctx.set_stream_final_output(None)
        assert ctx.get_stream_final_output() is None


class TestComponentStateChannel:
    @staticmethod
    def test_set_and_reset():
        state = object()
        token = ctx.set_component_state(state)
        assert ctx.current_component_state() is state
        ctx.reset_component_state(token)
        assert ctx.current_component_state() is None

    @staticmethod
    def test_default_is_none():
        assert ctx.current_component_state() is None
