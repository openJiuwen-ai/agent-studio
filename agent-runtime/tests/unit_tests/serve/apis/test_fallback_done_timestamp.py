# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Tests for _fallback_terminal_done 兜底终态帧的时间戳单位。

背景 bug：兜底 done 帧的 createdTime 用秒级时间戳（int(time.time())），而全仓
其余事件（chunk_wrapper、各 adapter、event_handler）均为毫秒
（int(time.time() * 1000)）。前端按时间排序/计算耗时会把它判到 1970 年附近，
或当作乱序帧丢弃。
"""

import json

from agent_runtime.serve.apis.orchestration import _fallback_terminal_done


class TestFallbackTerminalDoneTimestamp:
    @staticmethod
    def test_created_time_is_milliseconds():
        frame = _fallback_terminal_done("exec-1")
        payload = json.loads(frame[len("data: "):].strip())
        # 毫秒级时间戳（当前 ~1.7e12），秒级（~1.7e9）应被判错
        assert payload["createdTime"] > 10**12

    @staticmethod
    def test_frame_fields():
        frame = _fallback_terminal_done("exec-1")
        payload = json.loads(frame[len("data: "):].strip())
        assert payload["event"] == "done"
        assert payload["executionId"] == "exec-1"
        assert payload["data"] == {}
