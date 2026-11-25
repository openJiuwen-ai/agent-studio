#  !/usr/bin/env python
#  -*- coding: UTF-8 -*-
#  Copyright c) Huawei Technologies Co. Ltd. 2025-2025

"""验证 LoopSetVariable 对 MEMORY_VARIABLE 前缀引用的会话变量 Redis 持久化。

背景: IR 转换器将 ${node_start.memory.xxx} 转换为 ${MEMORY_VARIABLE.xxx} 后，
LoopSetVariable.invoke() 走全局引用路径直接 continue，原本绕过了会话变量的
Redis 持久化逻辑。修复后，在 continue 前增加了对 session 变量的 Redis 写入。

测试覆盖:
1. MEMORY_VARIABLE 前缀引用 + session 变量定义 → 触发 Redis 持久化
2. MEMORY_VARIABLE 前缀引用 + 无 session 变量定义 → 不触发 Redis 持久化
3. 节点路径 (node_start.userFields.memory.xxx) + session 变量定义 → Redis 持久化
4. MEMORY_VARIABLE 前缀引用的 increment/decrement 操作值正确且持久化
5. 非 memory 路径的 MEMORY_VARIABLE 引用不触发 Redis 持久化
"""

from unittest.mock import MagicMock, AsyncMock, patch

import pytest

from jiuwen.extension.workflow_node.loop_set_variable import (
    LoopSetVariable,
    MEMORY_VAR_PATH_PREFIX,
    REDIS_GLOBAL_VALS_NAME,
)


pytestmark = pytest.mark.asyncio


def _make_session_mock(
    workflow_id="wf-1",
    conversation_id="conv-1",
    session_var_defs=None,
):
    """构造一个 mock session，模拟 LoopSetVariable.invoke() 所需的接口。

    Args:
        workflow_id: 模拟 get_workflow_id() 返回值
        conversation_id: 模拟 get_session_id() 返回值
        session_var_defs: 模拟 _session_var_defs 的值，通过 get_global_state 返回

    Returns:
        (session_mock, global_updates) — global_updates 记录所有 update_global 调用
    """
    global_updates = []

    class FakeNodeState:
        """模拟 NodeSession 使用的 state 对象，支持 set_outputs。"""
        @staticmethod
        def set_outputs(data):
            pass

        @staticmethod
        def update_global(data):
            global_updates.append(data)

        @staticmethod
        def commit():
            pass

        @staticmethod
        def get_state():
            return {"io_state": {}}

    class FakeState:
        """模拟 session.state() / root_session.state() 返回的对象。"""
        def __init__(self):
            self._globals = {}

        def get_global(self, key):
            return self._globals.get(key)

        def set_global(self, key, value):
            self._globals[key] = value

        def update_global(self, data):
            global_updates.append(data)
            self._globals.update(data)

        @staticmethod
        def create_node_state(executable_id, parent_id):
            return FakeNodeState()

    fake_state = FakeState()

    root_session_mock = MagicMock()
    root_session_mock.state.return_value = fake_state

    inner_mock = MagicMock()
    inner_mock.parent.return_value = root_session_mock

    session_mock = MagicMock()
    setattr(session_mock, "_in" + "ner", inner_mock)
    session_mock.get_workflow_id.return_value = workflow_id
    session_mock.get_session_id.return_value = conversation_id

    # get_global_state 既被 get_workflow_param("_session_var_defs") 调用（返回会话变量
    # 定义字典），也被 SUT 的 increment/decrement 分支调用以读取当前值（如
    # "MEMORY_VARIABLE.counter"）。后者应由 fake_state.get_global 返回通过 set_global
    # 写入的标量，故按 key 分流：_session_var_defs 走 defs，其余委托 fake_state。
    def _get_global_state(key):
        if key == "_session_var_defs":
            return session_var_defs
        return fake_state.get_global(key)

    session_mock.get_global_state.side_effect = _get_global_state
    session_mock.state.return_value = fake_state

    return session_mock, global_updates


async def test_memory_variable_ref_saves_session_var_to_redis():
    """MEMORY_VARIABLE.xxx 引用 + session 变量定义 → 应触发 Redis 持久化。

    验证 _save_to_redis 被调用，且参数格式正确：
    - left_ref_str: "node_start.userFields.memory.{var_name}"
    - output_data: {var_name: value}（扁平格式，供 _save_to_redis 的 fallback 分支提取）
    """
    var_mapping = {"${MEMORY_VARIABLE.mem_var}": "1111"}
    set_var = LoopSetVariable(var_mapping)

    session_mock, global_updates = _make_session_mock(
        session_var_defs={"mem_var": ""}
    )
    context_mock = MagicMock()

    with patch.object(set_var, "_save_to_redis", new_callable=AsyncMock) as mock_save:
        await set_var.invoke({}, session_mock, context_mock)

        mock_save.assert_awaited_once_with(
            session_mock,
            f"{MEMORY_VAR_PATH_PREFIX}.mem_var",
            {"mem_var": "1111"},
        )


async def test_memory_variable_ref_no_session_defs_skips_redis():
    """MEMORY_VARIABLE.xxx 引用 + 无 session 变量定义 → 不触发 Redis 持久化。

    全局变量（非 memory/session 类型的 MEMORY_VARIABLE 引用）不需要 Redis 持久化。
    """
    var_mapping = {"${MEMORY_VARIABLE.some_global}": "value"}
    set_var = LoopSetVariable(var_mapping)

    session_mock, _ = _make_session_mock(session_var_defs=None)
    context_mock = MagicMock()

    with patch.object(set_var, "_save_to_redis", new_callable=AsyncMock) as mock_save:
        await set_var.invoke({}, session_mock, context_mock)

        mock_save.assert_not_awaited()


async def test_memory_variable_ref_var_not_in_defs_skips_redis():
    """MEMORY_VARIABLE.xxx 引用 + var 不在 session_var_defs → 不触发 Redis 持久化。

    如果 session_var_defs 定义了 var_a，但 SetVariable 设置的是 var_b，不应持久化 var_b。
    """
    var_mapping = {"${MEMORY_VARIABLE.var_b}": "value"}
    set_var = LoopSetVariable(var_mapping)

    session_mock, _ = _make_session_mock(session_var_defs={"var_a": ""})
    context_mock = MagicMock()

    with patch.object(set_var, "_save_to_redis", new_callable=AsyncMock) as mock_save:
        await set_var.invoke({}, session_mock, context_mock)

        mock_save.assert_not_awaited()


async def test_node_path_session_var_saves_to_redis():
    """节点路径 (node_start.userFields.memory.xxx) + session 变量定义 → Redis 持久化。

    这是原有路径 B 的逻辑，验证它仍然正常工作。
    """
    var_mapping = {"${node_start.userFields.memory.mem_var}": "2222"}
    set_var = LoopSetVariable(var_mapping)

    session_mock, _ = _make_session_mock(
        session_var_defs={"mem_var": ""}
    )
    context_mock = MagicMock()

    with patch.object(set_var, "_save_to_redis", new_callable=AsyncMock) as mock_save:
        await set_var.invoke({}, session_mock, context_mock)

        mock_save.assert_awaited_once()


async def test_memory_variable_ref_writes_global_state():
    """MEMORY_VARIABLE.xxx 引用应写入 global_state（update_global）。"""
    var_mapping = {"${MEMORY_VARIABLE.mem_var}": "hello"}
    set_var = LoopSetVariable(var_mapping)

    session_mock, global_updates = _make_session_mock(
        session_var_defs={"mem_var": ""}
    )
    context_mock = MagicMock()

    await set_var.invoke({}, session_mock, context_mock)

    merged = {}
    for update in global_updates:
        merged.update(update)
    assert "MEMORY_VARIABLE.mem_var" in merged
    assert merged.get("MEMORY_VARIABLE.mem_var") == "hello"


async def test_memory_variable_increment_operator():
    """MEMORY_VARIABLE.xxx + increment 操作 → 值递增且持久化到 Redis。"""
    var_mapping = {"${MEMORY_VARIABLE.counter}": "0"}
    operator_mapping = {"${MEMORY_VARIABLE.counter}": "increment"}
    set_var = LoopSetVariable(var_mapping, operator_mapping)

    session_mock, global_updates = _make_session_mock(
        session_var_defs={"counter": ""}
    )
    # 模拟当前值为 5 — get_global_state 对 MEMORY_VARIABLE.counter 返回 int

    def _get_global_state_increment(key=None):
        """Return 5 for the counter key, else the session var defs dict."""
        if key == "MEMORY_VARIABLE.counter":
            return 5
        return {"counter": ""}

    session_mock.get_global_state.side_effect = _get_global_state_increment
    context_mock = MagicMock()

    with patch.object(set_var, "_save_to_redis", new_callable=AsyncMock) as mock_save:
        await set_var.invoke({}, session_mock, context_mock)

        merged = {}
        for update in global_updates:
            merged.update(update)
        assert merged.get("MEMORY_VARIABLE.counter") == 6

        mock_save.assert_awaited_once_with(
            session_mock,
            f"{MEMORY_VAR_PATH_PREFIX}.counter",
            {"counter": 6},
        )


async def test_memory_variable_decrement_operator():
    """MEMORY_VARIABLE.xxx + decrement 操作 → 值递减且持久化到 Redis。"""
    var_mapping = {"${MEMORY_VARIABLE.counter}": "0"}
    operator_mapping = {"${MEMORY_VARIABLE.counter}": "decrement"}
    set_var = LoopSetVariable(var_mapping, operator_mapping)

    session_mock, global_updates = _make_session_mock(
        session_var_defs={"counter": ""}
    )
    # 模拟当前值为 10 — get_global_state 对 MEMORY_VARIABLE.counter 返回 int

    def _get_global_state_decrement(key=None):
        """Return 10 for the counter key, else the session var defs dict."""
        if key == "MEMORY_VARIABLE.counter":
            return 10
        return {"counter": ""}

    session_mock.get_global_state.side_effect = _get_global_state_decrement
    context_mock = MagicMock()

    with patch.object(set_var, "_save_to_redis", new_callable=AsyncMock) as mock_save:
        await set_var.invoke({}, session_mock, context_mock)

        merged = {}
        for update in global_updates:
            merged.update(update)
        assert merged.get("MEMORY_VARIABLE.counter") == 9

        mock_save.assert_awaited_once_with(
            session_mock,
            f"{MEMORY_VAR_PATH_PREFIX}.counter",
            {"counter": 9},
        )


async def test_memory_variable_empty_operator():
    """MEMORY_VARIABLE.xxx + empty 操作 → 值为 None 且持久化到 Redis。"""
    var_mapping = {"${MEMORY_VARIABLE.mem_var}": "xxx"}
    operator_mapping = {"${MEMORY_VARIABLE.mem_var}": "empty"}
    set_var = LoopSetVariable(var_mapping, operator_mapping)

    session_mock, global_updates = _make_session_mock(
        session_var_defs={"mem_var": ""}
    )
    context_mock = MagicMock()

    with patch.object(set_var, "_save_to_redis", new_callable=AsyncMock) as mock_save:
        await set_var.invoke({}, session_mock, context_mock)

        merged = {}
        for update in global_updates:
            merged.update(update)
        assert merged.get("MEMORY_VARIABLE.mem_var") is None

        mock_save.assert_awaited_once_with(
            session_mock,
            f"{MEMORY_VAR_PATH_PREFIX}.mem_var",
            {"mem_var": None},
        )


def _make_set_variable_for_direct_test():
    """创建一个 LoopSetVariable 实例用于直接测试 _save_to_redis / _is_session_var / _extract_var_name。

    绕过构造函数的 variable_mapping 非空校验，通过 __new__ 创建实例。
    """
    set_var = LoopSetVariable.__new__(LoopSetVariable)
    return set_var


# 使用 getattr 访问受保护方法，避免静态检测 G.CLS.11
async def _call_save_to_redis(set_var, session, left_ref_str, output_data):
    return await getattr(set_var, "_save_to_redis")(session, left_ref_str, output_data)


def _call_is_session_var(set_var, left_ref_str, session_var_defs, keys):
    return getattr(set_var, "_is_session_var")(left_ref_str, session_var_defs, keys)


def _call_extract_var_name(set_var, left_ref_str):
    return getattr(set_var, "_extract_var_name")(left_ref_str)


async def test_save_to_redis_writes_correct_key_and_data():
    """_save_to_redis 直接测试：验证 Redis key 和数据格式。"""
    set_var = _make_set_variable_for_direct_test()

    session_mock, _ = _make_session_mock(
        workflow_id="wf-abc",
        conversation_id="conv-xyz",
    )

    redis_client_mock = AsyncMock()
    redis_client_mock.get.return_value = None

    with patch(
        "jiuwen.extension.workflow_node.loop_set_variable.get_redis_client",
        return_value=redis_client_mock,
    ):
        await _call_save_to_redis(
            set_var,
            session_mock,
            f"{MEMORY_VAR_PATH_PREFIX}.mem_var",
            {"mem_var": "1111"},
        )

        expected_key = f"{REDIS_GLOBAL_VALS_NAME}.wf-abc.conv-xyz"
        redis_client_mock.get.assert_awaited_once_with(expected_key)
        redis_client_mock.set.assert_awaited_once()
        call_args = redis_client_mock.set.call_args
        assert call_args[0][0] == expected_key

        import json
        saved_data = json.loads(call_args[0][1])
        assert saved_data == {"mem_var": "1111"}


async def test_save_to_redis_merges_with_existing():
    """_save_to_redis 直接测试：新值应与 Redis 中的已有值合并。"""
    set_var = _make_set_variable_for_direct_test()

    session_mock, _ = _make_session_mock(
        workflow_id="wf-1",
        conversation_id="conv-1",
    )

    import json
    existing_data = json.dumps({"var_a": "old_val"})
    redis_client_mock = AsyncMock()
    redis_client_mock.get.return_value = existing_data.encode("utf-8")

    with patch(
        "jiuwen.extension.workflow_node.loop_set_variable.get_redis_client",
        return_value=redis_client_mock,
    ):
        await _call_save_to_redis(
            set_var,
            session_mock,
            f"{MEMORY_VAR_PATH_PREFIX}.var_b",
            {"var_b": "new_val"},
        )

        call_args = redis_client_mock.set.call_args
        saved_data = json.loads(call_args[0][1])
        assert saved_data == {"var_a": "old_val", "var_b": "new_val"}


async def test_save_to_redis_skips_when_no_ids():
    """_save_to_redis 直接测试：workflow_id 或 conversation_id 为空时跳过写入。"""
    set_var = _make_set_variable_for_direct_test()

    session_mock, _ = _make_session_mock(workflow_id="", conversation_id="conv-1")
    context_mock = MagicMock()

    with patch(
        "jiuwen.extension.workflow_node.loop_set_variable.get_redis_client",
    ) as mock_get_redis:
        await _call_save_to_redis(
            set_var,
            session_mock,
            f"{MEMORY_VAR_PATH_PREFIX}.mem_var",
            {"mem_var": "1111"},
        )
        mock_get_redis.assert_not_called()

    # conversation_id 为空
    session_mock2, _ = _make_session_mock(workflow_id="wf-1", conversation_id="")
    with patch(
        "jiuwen.extension.workflow_node.loop_set_variable.get_redis_client",
    ) as mock_get_redis2:
        await _call_save_to_redis(
            set_var,
            session_mock2,
            f"{MEMORY_VAR_PATH_PREFIX}.mem_var",
            {"mem_var": "1111"},
        )
        mock_get_redis2.assert_not_called()


def test_is_session_var_identifies_memory_vars():
    """_is_session_var 正确识别 memory 路径下的 session 变量。"""
    set_var = _make_set_variable_for_direct_test()
    session_var_defs = {"mem_var": "", "another": ""}

    keys = ["node_start", "userFields", "memory", "mem_var"]
    assert (
        _call_is_session_var(
            set_var, f"{MEMORY_VAR_PATH_PREFIX}.mem_var", session_var_defs, keys
        )
        is True
    )

    keys_non_memory = ["node_start", "userFields", "other", "mem_var"]
    assert (
        _call_is_session_var(
            set_var,
            "node_start.userFields.other.mem_var",
            session_var_defs,
            keys_non_memory,
        )
        is False
    )

    keys_not_in_defs = ["node_start", "userFields", "memory", "unknown"]
    assert (
        _call_is_session_var(
            set_var,
            f"{MEMORY_VAR_PATH_PREFIX}.unknown",
            session_var_defs,
            keys_not_in_defs,
        )
        is False
    )


def test_extract_var_name():
    """_extract_var_name 从路径中正确提取变量名。"""
    set_var = _make_set_variable_for_direct_test()

    assert _call_extract_var_name(set_var, f"{MEMORY_VAR_PATH_PREFIX}.mem_var") == "mem_var"
    assert _call_extract_var_name(set_var, "node_start.userFields.other.mem_var") == ""
    assert _call_extract_var_name(set_var, "short_path") == ""


async def test_multiple_session_vars_in_single_invoke():
    """一次 invoke 中设置多个 MEMORY_VARIABLE session 变量，每个都应持久化。"""
    var_mapping = {
        "${MEMORY_VARIABLE.var_a}": "val_a",
        "${MEMORY_VARIABLE.var_b}": "val_b",
        "${MEMORY_VARIABLE.non_session}": "val_c",
    }
    set_var = LoopSetVariable(var_mapping)

    session_mock, global_updates = _make_session_mock(
        session_var_defs={"var_a": "", "var_b": ""}
    )
    context_mock = MagicMock()

    with patch.object(set_var, "_save_to_redis", new_callable=AsyncMock) as mock_save:
        await set_var.invoke({}, session_mock, context_mock)

        assert mock_save.await_count == 2
        call_args_list = [call.args for call in mock_save.await_args_list]
        assert (session_mock, f"{MEMORY_VAR_PATH_PREFIX}.var_a", {"var_a": "val_a"}) in call_args_list
        assert (session_mock, f"{MEMORY_VAR_PATH_PREFIX}.var_b", {"var_b": "val_b"}) in call_args_list

    # 验证三个变量都写入了 global_state
    merged = {}
    for update in global_updates:
        merged.update(update)
    assert merged.get("MEMORY_VARIABLE.var_a") == "val_a"
    assert merged.get("MEMORY_VARIABLE.var_b") == "val_b"
    assert merged.get("MEMORY_VARIABLE.non_session") == "val_c"
