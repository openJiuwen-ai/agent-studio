#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""FlowCode 结果缓存测试 — (code, exec_env, inputs, outputs_schema) hash LRU 缓存."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from agent_runtime.extension.workflow_node.flow_code import FlowCode, FlowCodeConfig
from agent_runtime.extension.workflow_node.code_runner.result_cache import (
    CodeResultCache,
    make_cache_key,
)


def _make_flow_code(code="def main(args): return {'result': args['x'] + 1}"):
    return FlowCode(FlowCodeConfig(code=code, exec_env="local"))


def _make_session():
    mock_session = MagicMock()
    mock_session.get_component_id.return_value = "test"
    mock_session.get_session_id.return_value = "sess"
    mock_session.get_workflow_id.return_value = "wf"
    mock_session.trace = AsyncMock()
    return mock_session


def _make_runner(return_value):
    runner = AsyncMock()
    runner.run = AsyncMock(return_value=return_value)
    runner.function_log = "hello from code"
    return runner


async def _invoke(flow_code, user_fields):
    """执行一次 invoke，返回 (输出, session mock)。"""
    from openjiuwen.core.common.constants.constant import USER_FIELDS

    session = _make_session()
    result = await flow_code.invoke(
        inputs={USER_FIELDS: user_fields},
        session=session,
        context=MagicMock(),
    )
    return result, session


class TestCodeResultCache:
    @staticmethod
    def test_put_get_roundtrip():
        cache = CodeResultCache(maxsize=4)
        cache.put("k", {"a": 1}, "log")
        result, log = cache.get("k")
        assert result == {"a": 1}
        assert log == "log"

    @staticmethod
    def test_get_miss_returns_none():
        cache = CodeResultCache(maxsize=4)
        assert cache.get("missing") is None
        assert cache.stats()["misses"] == 1

    @staticmethod
    def test_lru_eviction():
        cache = CodeResultCache(maxsize=2)
        cache.put("k1", {}, "")
        cache.put("k2", {}, "")
        cache.get("k1")  # k1 变为最近使用
        cache.put("k3", {}, "")  # 淘汰 k2
        assert cache.get("k2") is None
        assert cache.get("k1") is not None
        assert cache.get("k3") is not None

    @staticmethod
    def test_returned_value_isolated_from_cache():
        cache = CodeResultCache(maxsize=4)
        cache.put("k", {"a": 1}, "")
        result, _ = cache.get("k")
        result["a"] = 999
        again, _ = cache.get("k")
        assert again == {"a": 1}

    @staticmethod
    def test_maxsize_zero_disables_storage():
        cache = CodeResultCache(maxsize=0)
        cache.put("k", {"a": 1}, "")
        assert cache.get("k") is None


class TestMakeCacheKey:
    @staticmethod
    def test_same_inputs_different_key_order_same_key():
        k1 = make_cache_key("code", "local", {"a": 1, "b": [2, 3]}, [])
        k2 = make_cache_key("code", "local", {"b": [2, 3], "a": 1}, [])
        assert k1 == k2

    @staticmethod
    def test_different_code_different_key():
        assert make_cache_key("code1", "local", {}, []) != make_cache_key(
            "code2", "local", {}, []
        )

    @staticmethod
    def test_different_inputs_different_key():
        assert make_cache_key("code", "local", {"a": 1}, []) != make_cache_key(
            "code", "local", {"a": 2}, []
        )

    @staticmethod
    def test_different_exec_env_different_key():
        assert make_cache_key("code", "local", {}, []) != make_cache_key(
            "code", "sandbox", {}, []
        )

    @staticmethod
    def test_different_outputs_schema_different_key():
        assert make_cache_key("code", "local", {}, []) != make_cache_key(
            "code", "local", {}, [{"id": "result", "type": "string"}]
        )


class TestFlowCodeResultCache:
    @staticmethod
    @pytest.mark.asyncio
    async def test_second_invoke_with_same_inputs_hits_cache():
        flow_code = _make_flow_code()
        runner = _make_runner({"result": 2})
        flow_code._code_runner = runner

        cache = CodeResultCache(maxsize=4)
        with patch(
            "agent_runtime.extension.workflow_node.flow_code.get_code_result_cache",
            return_value=cache,
        ), patch.object(flow_code, "_check_blacklist"):
            first, _ = await _invoke(flow_code, {"x": 1})
            second, _ = await _invoke(flow_code, {"x": 1})

        assert first == second
        assert runner.run.call_count == 1  # 第二次命中缓存，未再执行
        assert cache.stats()["hits"] == 1
        assert cache.stats()["misses"] == 1

    @staticmethod
    @pytest.mark.asyncio
    async def test_different_inputs_misses_cache():
        flow_code = _make_flow_code()
        runner = _make_runner({"result": 2})
        flow_code._code_runner = runner

        cache = CodeResultCache(maxsize=4)
        with patch(
            "agent_runtime.extension.workflow_node.flow_code.get_code_result_cache",
            return_value=cache,
        ), patch.object(flow_code, "_check_blacklist"):
            await _invoke(flow_code, {"x": 1})
            await _invoke(flow_code, {"x": 2})
        assert runner.run.call_count == 2
        assert cache.stats()["hits"] == 0

    @staticmethod
    @pytest.mark.asyncio
    async def test_cache_disabled_runs_every_time():
        flow_code = _make_flow_code()
        runner = _make_runner({"result": 2})
        flow_code._code_runner = runner

        with patch(
            "agent_runtime.extension.workflow_node.flow_code.get_code_result_cache",
            return_value=None,
        ), patch.object(flow_code, "_check_blacklist"):
            await _invoke(flow_code, {"x": 1})
            await _invoke(flow_code, {"x": 1})

        assert runner.run.call_count == 2

    @staticmethod
    @pytest.mark.asyncio
    async def test_failed_execution_not_cached():
        flow_code = _make_flow_code()
        runner = _make_runner({"result": 2})
        runner.run = AsyncMock(side_effect=ValueError("boom"))
        flow_code._code_runner = runner

        cache = CodeResultCache(maxsize=4)
        with patch(
            "agent_runtime.extension.workflow_node.flow_code.get_code_result_cache",
            return_value=cache,
        ), patch.object(flow_code, "_check_blacklist"):
            with pytest.raises(Exception):
                await _invoke(flow_code, {"x": 1})

        assert cache.stats()["size"] == 0
        assert runner.run.call_count == 1

    @staticmethod
    @pytest.mark.asyncio
    async def test_function_log_replayed_on_cache_hit():
        flow_code = _make_flow_code()
        runner = _make_runner({"result": 2})
        runner.function_log = "printed output"
        flow_code._code_runner = runner

        cache = CodeResultCache(maxsize=4)
        with patch(
            "agent_runtime.extension.workflow_node.flow_code.get_code_result_cache",
            return_value=cache,
        ), patch.object(flow_code, "_check_blacklist"):
            _, first_session = await _invoke(flow_code, {"x": 1})
            runner.function_log = ""  # 后续执行不再产生 log
            _, second_session = await _invoke(flow_code, {"x": 1})

        # 命中时仍从缓存回放 function_log 并 trace
        first_logs = [
            call.kwargs.get("data", {}).get("function_log")
            for call in first_session.trace.call_args_list
        ]
        second_logs = [
            call.kwargs.get("data", {}).get("function_log")
            for call in second_session.trace.call_args_list
        ]
        assert "printed output" in first_logs
        assert "printed output" in second_logs

    @staticmethod
    @pytest.mark.asyncio
    async def test_mutated_output_not_polluting_cache():
        flow_code = _make_flow_code()
        runner = _make_runner({"result": {"nested": 1}})
        flow_code._code_runner = runner

        cache = CodeResultCache(maxsize=4)
        with patch(
            "agent_runtime.extension.workflow_node.flow_code.get_code_result_cache",
            return_value=cache,
        ), patch.object(flow_code, "_check_blacklist"):
            from openjiuwen.core.common.constants.constant import USER_FIELDS

            first, _ = await _invoke(flow_code, {"x": 1})
            first[USER_FIELDS]["result"]["nested"] = 999  # 上游污染返回值
            second, _ = await _invoke(flow_code, {"x": 1})

        assert second[USER_FIELDS]["result"]["nested"] == 1
