"""COM-03 §6.2: 流式状态与唯一终态守卫。

流状态：NOT_STARTED → STREAMING → TERMINATED / CANCELLED。

规则：
- NOT_STARTED 失败：走普通 HTTP 构建器，不产生 SSE 帧；
- STREAMING 失败：原子切换为 TERMINATED，最多写一个 SSE error；
- error 写出后禁止继续发送 message、success end 或 done；
- 客户端取消/正常断开转为 CANCELLED，只清理资源，不发 error；
- 写 error 自身失败时只记录一次安全内部日志并关闭，不递归创建第二个 error。
"""

from __future__ import annotations

import threading
from enum import Enum, auto


class StreamState(Enum):
    NOT_STARTED = auto()
    STREAMING = auto()
    TERMINATED = auto()
    CANCELLED = auto()


class SseTerminalGuard:
    """线程安全的唯一终态守卫。确保每个流最多一个 error 终态。"""

    def __init__(self) -> None:
        self._state = StreamState.NOT_STARTED
        self._lock = threading.Lock()
        self._error_sent = False

    @property
    def state(self) -> StreamState:
        with self._lock:
            return self._state

    def begin_streaming(self) -> bool:
        """从 NOT_STARTED 切换到 STREAMING。返回是否成功（已开始则 False）。"""
        with self._lock:
            if self._state != StreamState.NOT_STARTED:
                return False
            self._state = StreamState.STREAMING
            return True

    def should_send_error(self) -> bool:
        """是否应发送 SSE error。NOT_STARTED 不发（走 HTTP），TERMINATED/CANCELLED 不发。"""
        with self._lock:
            return self._state == StreamState.STREAMING and not self._error_sent

    def try_send_error(self) -> bool:
        """COM-03 §6.2: 原子状态迁移 STREAMING → TERMINATED。

        只有赢家（返回 True）允许写 SSE error；并发失败者返回 None。
        替代非原子的 should_send_error() + 发送 + mark_error_sent() 三步。
        """
        with self._lock:
            if self._state == StreamState.STREAMING and not self._error_sent:
                self._error_sent = True
                self._state = StreamState.TERMINATED
                return True
            return False

    def mark_error_sent(self) -> None:
        """标记已发送 error，原子切换为 TERMINATED。"""
        with self._lock:
            self._error_sent = True
            if self._state == StreamState.STREAMING:
                self._state = StreamState.TERMINATED

    def allow_message(self) -> bool:
        """error 发出后是否还允许 message。TERMINATED/CANCELLED 不允许。"""
        with self._lock:
            return self._state == StreamState.STREAMING and not self._error_sent

    def cancel(self) -> None:
        """客户端取消/正常断开。转为 CANCELLED，不发 error。"""
        with self._lock:
            if self._state != StreamState.TERMINATED:
                self._state = StreamState.CANCELLED

    @property
    def error_sent(self) -> bool:
        with self._lock:
            return self._error_sent
