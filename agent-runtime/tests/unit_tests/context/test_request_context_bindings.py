# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""FEAT-093 请求级绑定 setter 的 ContextVar 语义测试。

copy-on-write 契约：setter 经 dataclasses.replace 构造新实例后
ContextVar.set——ContextVar 的 default 是进程级共享实例，不继承
contextvars 的执行（桥线程/线程池 worker）.get() 拿到的正是它，
原地改写会把本次请求的变量/凭证泄漏给所有无自有上下文的执行。
"""
# pylint: disable=protected-access  # 单测需直接操作 _request_ctx（仓库既有惯例）

from agent_runtime.context import request_context as rc


def _reset_ctx():
    """清空当前上下文的三类绑定并还原为干净实例。"""
    rc._request_ctx.set(rc.RequestContext())


def test_setters_write_new_instance_not_shared_default():
    """setter 写新实例：当前上下文与共享 default 实例解耦。"""
    _reset_ctx()
    shared_default = rc._request_ctx.get()

    rc.set_request_global_variables({"userToken": "tok-a"})
    rc.set_request_memory_variables({"mem": "m"})
    rc.set_request_mcp_input_parameters({"srv": {"Authorization": "{{inputs.userToken}}"}})

    # 当前上下文读到新值
    assert rc.get_request_global_variables() == {"userToken": "tok-a"}
    assert rc.get_request_memory_variables() == {"mem": "m"}
    assert rc.get_request_mcp_input_parameters() == {"srv": {"Authorization": "{{inputs.userToken}}"}}
    # 共享 default 实例未被原地污染（仍是写入前的空值）
    assert shared_default.global_variables == {}
    assert shared_default.memory_variables == {}
    assert shared_default.mcp_input_parameters == {}


def test_contextless_thread_reads_clean_default():
    """不继承 contextvars 的新线程读到干净的 default（桥线程场景）。"""
    import threading

    _reset_ctx()
    rc.set_request_global_variables({"userToken": "tok-owner"})

    observed = {}

    def worker():
        # 新线程不继承主线程 ContextVar set 的值——.get() 落到 default 实例
        observed["globals"] = rc.get_request_global_variables()
        observed["templates"] = rc.get_request_mcp_input_parameters()

    t = threading.Thread(target=worker)
    t.start()
    t.join()

    assert observed["globals"] == {}
    assert observed["templates"] == {}


def test_clear_request_runtime_bindings():
    """clear 清空三类绑定（run_streaming finally 契约）。"""
    _reset_ctx()
    rc.set_request_global_variables({"userToken": "tok-a"})
    rc.set_request_memory_variables({"mem": "m"})
    rc.set_request_mcp_input_parameters({"srv": {"Authorization": "{{inputs.userToken}}"}})

    rc.clear_request_runtime_bindings()

    assert rc.get_request_global_variables() == {}
    assert rc.get_request_memory_variables() == {}
    assert rc.get_request_mcp_input_parameters() == {}


def test_setters_hold_caller_dict_reference():
    """setter 就地持有调用方 dict 引用（后续默认值合并对读取方可见）。"""
    _reset_ctx()
    variables = {"userToken": "tok-a"}
    rc.set_request_global_variables(variables)
    # react 执行器在 setter 之后的入参默认值合并（就地变更同一 dict）
    variables["extra"] = "default-value"
    assert rc.get_request_global_variables().get("extra") == "default-value"
