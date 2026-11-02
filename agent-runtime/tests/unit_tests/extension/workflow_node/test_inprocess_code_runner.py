#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""InprocessCodeRunner 单元测试"""

import asyncio
import os
import sys

import pytest

from agent_runtime.extension.workflow_node.code_runner.inprocess_code_runner import (
    InprocessCodeRunner,
    _exec_process_lock,
)
from agent_runtime.extension.workflow_node.code_runner.base_code_runner import (
    CodeRunResult,
)
from openjiuwen.core.common.exception.errors import BaseError


class TestInprocessCodeRunnerBasicExecution:
    """基本执行测试"""

    @staticmethod
    @pytest.mark.asyncio
    async def test_returns_dict():
        runner = InprocessCodeRunner()
        code = "def main(args): return {'key': args.get('input', '')}"
        result = await runner.run(user_code=code, inputs={"input": "hello"})
        assert isinstance(result, CodeRunResult)
        assert result.result == {"key": "hello"}

    @staticmethod
    @pytest.mark.asyncio
    async def test_returns_empty_dict():
        runner = InprocessCodeRunner()
        code = "def main(args): return {}"
        result = await runner.run(user_code=code, inputs={})
        assert isinstance(result, CodeRunResult)
        assert result.result == {}

    @staticmethod
    @pytest.mark.asyncio
    async def test_passes_all_inputs():
        runner = InprocessCodeRunner()
        code = "def main(args): return args"
        inputs = {"a": 1, "b": "two", "c": [3, 4]}
        result = await runner.run(user_code=code, inputs=inputs)
        assert isinstance(result, CodeRunResult)
        assert result.result == inputs


class TestInprocessCodeRunnerConsoleLog:
    """console_log（function_log）捕获测试"""

    @staticmethod
    @pytest.mark.asyncio
    async def test_print_captured_to_function_log():
        runner = InprocessCodeRunner()
        code = "def main(args):\n    print('hello from code')\n    return {}"
        result = await runner.run(user_code=code, inputs={})
        assert "hello from code" in result.function_log
        assert "hello from code" in runner.function_log

    @staticmethod
    @pytest.mark.asyncio
    async def test_multiple_prints_captured():
        runner = InprocessCodeRunner()
        code = "def main(args):\n    print('line1')\n    print('line2')\n    return {}"
        result = await runner.run(user_code=code, inputs={})
        assert "line1" in result.function_log
        assert "line2" in result.function_log

    @staticmethod
    @pytest.mark.asyncio
    async def test_no_print_gives_empty_function_log():
        runner = InprocessCodeRunner()
        code = "def main(args): return {}"
        result = await runner.run(user_code=code, inputs={})
        assert result.function_log == ""


class TestInprocessCodeRunnerReturnValueValidation:
    """返回值类型校验测试"""

    @staticmethod
    @pytest.mark.asyncio
    async def test_non_dict_return_raises_error():
        runner = InprocessCodeRunner()
        code = "def main(args): return 'not a dict'"
        with pytest.raises(BaseError):
            await runner.run(user_code=code, inputs={})

    @staticmethod
    @pytest.mark.asyncio
    async def test_list_return_raises_error():
        runner = InprocessCodeRunner()
        code = "def main(args): return [1, 2, 3]"
        with pytest.raises(BaseError):
            await runner.run(user_code=code, inputs={})

    @staticmethod
    @pytest.mark.asyncio
    async def test_none_return_raises_error():
        runner = InprocessCodeRunner()
        code = "def main(args): return None"
        with pytest.raises(BaseError):
            await runner.run(user_code=code, inputs={})


class TestInprocessCodeRunnerExceptionPropagation:
    """异常传播测试"""

    @staticmethod
    @pytest.mark.asyncio
    async def test_runtime_error_propagated():
        runner = InprocessCodeRunner()
        code = "def main(args): raise RuntimeError('test error')"
        with pytest.raises(RuntimeError, match="test error"):
            await runner.run(user_code=code, inputs={})

    @staticmethod
    @pytest.mark.asyncio
    async def test_value_error_propagated():
        runner = InprocessCodeRunner()
        code = "def main(args): raise ValueError('bad value')"
        with pytest.raises(ValueError, match="bad value"):
            await runner.run(user_code=code, inputs={})

    @staticmethod
    @pytest.mark.asyncio
    async def test_exception_traceback_in_function_log():
        runner = InprocessCodeRunner()
        code = "def main(args): raise RuntimeError('oops')"
        with pytest.raises(RuntimeError):
            await runner.run(user_code=code, inputs={})
        assert "oops" in runner.function_log


class TestInprocessCodeRunnerInputsIsolation:
    """inputs 不被污染测试"""

    @staticmethod
    @pytest.mark.asyncio
    async def test_inputs_not_mutated():
        runner = InprocessCodeRunner()
        code = "def main(args):\n    args['new_key'] = 'mutated'\n    return args"
        original_inputs = {"a": 1}
        await runner.run(user_code=code, inputs=original_inputs)
        assert "new_key" not in original_inputs
        assert original_inputs == {"a": 1}

    @staticmethod
    @pytest.mark.asyncio
    async def test_nested_dict_not_mutated():
        runner = InprocessCodeRunner()
        code = "def main(args):\n    args['nested']['x'] = 999\n    return args"
        original_inputs = {"nested": {"x": 1}}
        await runner.run(user_code=code, inputs=original_inputs)
        assert original_inputs == {"nested": {"x": 1}}


class TestInprocessCodeRunnerOsSystemMock:
    """os.system mock 测试"""

    @staticmethod
    @pytest.mark.asyncio
    async def test_os_system_returns_negative_one():
        runner = InprocessCodeRunner()
        code = "import os\ndef main(args):\n    ret = os.system('echo test')\n    return {'ret': ret}"
        result = await runner.run(user_code=code, inputs={})
        assert result.result == {"ret": -1}


class TestInprocessCodeRunnerTimeout:
    """超时控制测试"""

    @staticmethod
    @pytest.mark.asyncio
    async def test_timeout_raises_timeout_error():
        """死循环代码在超时后被中断并抛出 TimeoutError"""
        runner = InprocessCodeRunner()
        code = "def main(args):\n    while True:\n        pass\n    return {}"
        with pytest.raises(TimeoutError, match="代码执行超时"):
            await runner.run(user_code=code, inputs={}, timeout=1)

    @staticmethod
    @pytest.mark.asyncio
    async def test_normal_execution_within_timeout():
        """正常代码在超时时间内完成不受影响"""
        runner = InprocessCodeRunner()
        code = "def main(args): return {'ok': True}"
        result = await runner.run(user_code=code, inputs={}, timeout=10)
        assert result.result == {"ok": True}

    @staticmethod
    @pytest.mark.asyncio
    async def test_stdout_restored_after_timeout():
        """超时后 sys.stdout 恢复为执行前的值"""
        runner = InprocessCodeRunner()
        original_stdout = sys.stdout
        code = "def main(args):\n    while True:\n        pass\n    return {}"
        with pytest.raises(TimeoutError):
            await runner.run(user_code=code, inputs={}, timeout=1)
        assert sys.stdout is original_stdout

    @staticmethod
    @pytest.mark.asyncio
    async def test_os_system_restored_after_timeout():
        """超时后 os.system 恢复为执行前的基线（非 MagicMock）"""
        runner = InprocessCodeRunner()
        original_os_system = os.system
        code = "def main(args):\n    while True:\n        pass\n    return {}"
        with pytest.raises(TimeoutError):
            await runner.run(user_code=code, inputs={}, timeout=1)
        assert os.system is original_os_system


class TestInprocessCodeRunnerConcurrentP1:
    """P1：并发超时后全局 stdout / os.system 恢复为真实基线。

    复现检视意见中的场景：A 正常执行期间启动 B，B 进入不可中断的 C 调用并超时；
    断言 B 超时后 stdout 恢复真实基线（而非 A 的遗留 StringIO）、
    os.system 恢复 baseline（而非 MagicMock）。
    """

    @staticmethod
    @pytest.mark.asyncio
    async def test_concurrent_timeout_restores_stdout_and_os_system():
        """A 执行 0.2s，B 在 0.05s 后启动并执行不可中断的 time.sleep，B timeout=1。

        B 卡在 time.sleep（Windows C 扩展，不可被 PyThreadState_SetAsyncExc 立即中断），
        超时后 _force_cleanup 应将 stdout / os.system 恢复为锁内捕获的真实基线。

        注意：time.sleep 在 Windows 上不可被异步异常中断，B 的 worker 线程会
        在 time.sleep 结束后才退出。使用 3 秒（> timeout 1 秒）使其在测试可接受
        范围内自然结束并释放锁，避免污染后续测试。
        """
        original_stdout = sys.stdout
        original_os_system = os.system

        runner = InprocessCodeRunner()
        # A：快速打印并返回（0.2s 内完成），执行期间会短暂替换 sys.stdout
        code_a = (
            "import time\n"
            "def main(args):\n"
            "    print('FIRST')\n"
            "    time.sleep(0.2)\n"
            "    return {}"
        )
        # B：进入不可中断的 time.sleep(3)，会被 timeout 杀掉但线程仍存活
        code_b = (
            "import time\n"
            "def main(args):\n"
            "    time.sleep(3)\n"
            "    return {}"
        )

        # 启动 A，然后延迟 0.05s 启动 B（此时 A 仍在执行，sys.stdout 是 A 的 StringIO）
        task_a = asyncio.ensure_future(
            runner.run(user_code=code_a, inputs={}, timeout=10)
        )
        await asyncio.sleep(0.05)
        # B 启动时 A 仍在执行，sys.stdout 被替换成 A 的 StringIO。
        # 修复前：saved_stdout 在 run() 锁外捕获，会拿到 A 的 StringIO；
        # 修复后：saved_stdout 在 _exec_sync 锁内捕获，A 已释放锁，拿到真实 stdout。
        with pytest.raises(TimeoutError):
            await runner.run(user_code=code_b, inputs={}, timeout=1)

        # 断言全局状态恢复为真实基线（此时 B 的 worker 仍卡在 time.sleep，但
        # _force_cleanup 已用锁内基线恢复 stdout / os.system）
        assert sys.stdout is original_stdout, (
            f"stdout 应恢复为真实基线，实际为 {type(sys.stdout).__name__}"
        )
        assert os.system is original_os_system, (
            f"os.system 应恢复为真实基线，实际为 {type(os.system).__name__}"
        )

        # 等 A 完成（A 不受 B 超时影响，因为 B 的 saved_stdout 捕获的是真实基线）
        await task_a

        # 等待 B 的 worker 线程自然结束（time.sleep(3) 后释放锁），避免污染后续测试
        # B 的 worker 在 time.sleep 结束后会被 _EPILOGUE 的 finally 恢复 stdout，
        # 并释放 _exec_process_lock。
        deadline = asyncio.get_running_loop().time() + 10
        while _exec_process_lock.locked() and asyncio.get_running_loop().time() < deadline:
            await asyncio.sleep(0.1)


class TestInprocessCodeRunnerConcurrentP2:
    """P2：同一 runner 并发调用时各调用获得各自的 function_log。

    复现检视意见：同一 runner 实例并发调用 FIRST / SECOND，
    最终 function_log 串写。修复后从返回值 CodeRunResult.function_log 读取，
    每个调用拿到自己的日志。
    """

    @staticmethod
    @pytest.mark.asyncio
    async def test_concurrent_calls_get_respective_function_log():
        """同一 runner 并发执行两个不同 print 的代码，各自拿到正确 function_log。

        两个调用因 _exec_process_lock 串行执行，但返回值 CodeRunResult 各自独立，
        function_log 不会串写。
        """
        runner = InprocessCodeRunner()
        code_first = (
            "def main(args):\n"
            "    print('FIRST')\n"
            "    return {}"
        )
        code_second = (
            "def main(args):\n"
            "    print('SECOND')\n"
            "    return {}"
        )

        # 并发启动两个调用（会因 _exec_process_lock 串行执行，但返回值各自独立）
        task_first = asyncio.ensure_future(
            runner.run(user_code=code_first, inputs={}, timeout=10)
        )
        task_second = asyncio.ensure_future(
            runner.run(user_code=code_second, inputs={}, timeout=10)
        )

        result_first, result_second = await asyncio.gather(task_first, task_second)

        # 从返回值读取各自 function_log（不依赖 self.function_log）
        assert "FIRST" in result_first.function_log
        assert "SECOND" not in result_first.function_log
        assert "SECOND" in result_second.function_log
        assert "FIRST" not in result_second.function_log

    @staticmethod
    @pytest.mark.asyncio
    async def test_sequential_calls_function_log_not_stale():
        """连续两次调用同一 runner，第二次返回值不含第一次的日志。"""
        runner = InprocessCodeRunner()
        code_a = "def main(args):\n    print('AAA')\n    return {}"
        code_b = "def main(args):\n    print('BBB')\n    return {}"

        result_a = await runner.run(user_code=code_a, inputs={})
        result_b = await runner.run(user_code=code_b, inputs={})

        assert "AAA" in result_a.function_log
        assert "BBB" not in result_a.function_log
        assert "BBB" in result_b.function_log
        assert "AAA" not in result_b.function_log


class TestInprocessCodeRunnerLockSemantics:
    """锁长期占用时的错误语义测试。

    检视意见要求：锁被长期占用时，run(timeout < _LOCK_ACQUIRE_TIMEOUT) 的错误语义
    和 worker 后续行为。

    当 _exec_process_lock 被外部持有时，worker 的 acquire(timeout=30) 会阻塞。
    run(timeout=1) 先超时，抛出 TimeoutError（而非 RuntimeError，因为 worker
    尚未到达 acquire 超时点）。此时 saved_stdout/saved_os_system 为 None（worker
    未到达锁内基线捕获），_force_cleanup 不会错误恢复。worker 为 daemon 线程，
    在 acquire(30) 超时后会抛 RuntimeError 并自然退出。
    """

    @staticmethod
    @pytest.mark.asyncio
    async def test_lock_held_run_timeout_not_runtime_error():
        """锁被外部占用时，run(timeout=1) 抛 TimeoutError（worker 卡在 acquire）。"""
        runner = InprocessCodeRunner()
        # 占用锁不释放，模拟前一次执行卡死
        _exec_process_lock.acquire()
        try:
            code = "def main(args): return {}"
            # run(timeout=1) 先于 acquire(timeout=30) 超时
            with pytest.raises(TimeoutError, match="代码执行超时"):
                await runner.run(user_code=code, inputs={}, timeout=1)
        finally:
            _exec_process_lock.release()
