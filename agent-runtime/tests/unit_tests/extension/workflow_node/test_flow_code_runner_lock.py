# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# 本文件以白盒方式钉住懒初始化互斥语义：并发去重计数没有公开入口可观测，
# 必须直接驱动受保护的懒初始化方法并读取受保护字段，故按测试需要直接访问。
# pylint: disable=protected-access
"""FlowCode._ensure_code_runner 线程安全测试（issue #1705 / P2-1）。

懒初始化 check-then-act 无互斥：单事件循环下同步实现原子，但若经线程池
调用（或未来引入）两线程同时通过 ``self._code_runner is not None`` 检查，
会重复创建 CodeRunner。本用例用真线程 + 工厂内阻塞制造交错判别。
"""
import threading
import time
from unittest.mock import MagicMock

from agent_runtime.extension.workflow_node.flow_code import FlowCode, FlowCodeConfig


def test_ensure_code_runner_concurrent_threads_create_once(monkeypatch):
    """并发首调只创建一个 CodeRunner（加锁后第二个线程命中锁内双检）。"""
    comp = FlowCode(
        FlowCodeConfig(code="def main(args): return {}", exec_env="sandbox")
    )

    sys_op = MagicMock()
    sys_op.code.return_value = MagicMock()
    from openjiuwen.core.runner import Runner

    monkeypatch.setattr(
        Runner.resource_mgr, "get_sys_operation", lambda *args, **kwargs: sys_op
    )

    created = []
    create_entered = threading.Event()
    release_create = threading.Event()

    class _Strategy:
        @staticmethod
        def create(code_op):
            created.append(code_op)
            create_entered.set()
            # 阻塞直到主线程确认第二个线程的落点后再返回：无锁实现下第二个
            # 线程会在此期间进入 create，created 长度变 2。
            release_create.wait(timeout=2)
            return MagicMock()

    from agent_runtime.extension.workflow_node.code_runner import runner as runner_mod

    monkeypatch.setattr(
        runner_mod.CodeRunnerFactory, "_runners", {"sandbox": _Strategy()}
    )

    errors = []

    def _call():
        try:
            comp._ensure_code_runner()
        except Exception as exc:  # noqa: BLE001 - 线程内异常回传主线程断言
            errors.append(exc)

    first = threading.Thread(target=_call)
    first.start()
    assert create_entered.wait(timeout=2), "first thread did not enter create"

    second = threading.Thread(target=_call)
    second.start()
    # 无锁实现：第二个线程也通过 check 并进入 create（created 变 2）而转红。
    time.sleep(0.2)
    assert len(created) == 1

    release_create.set()
    first.join(timeout=2)
    second.join(timeout=2)

    assert not errors
    assert len(created) == 1
    assert comp._code_runner is not None
