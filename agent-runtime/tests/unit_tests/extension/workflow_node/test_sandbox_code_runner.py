#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""SandboxCodeRunner unit tests — SysOperation SANDBOX mode."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from agent_runtime.extension.workflow_node.code_runner.sandbox_code_runner import (
    SandboxCodeRunner,
)
from agent_runtime.extension.workflow_node.code_runner.base_code_runner import (
    CodeRunResult,
    build_wrapped_code,
)
from openjiuwen.core.common.exception.codes import StatusCode


def make_mock_sys_op(
    exit_code=0, stdout='{"result": 42}', stderr="", status_code="SUCCESS"
):
    mock_raw_result = MagicMock()
    if status_code == "SUCCESS":
        mock_raw_result.code = StatusCode.SUCCESS.code
        mock_raw_result.message = "ok"
    else:
        mock_raw_result.code = "ERROR"
        mock_raw_result.message = "execution error"

    mock_raw_result.data.exit_code = exit_code
    mock_raw_result.data.stdout = stdout
    mock_raw_result.data.stderr = stderr

    mock_code_op = AsyncMock()
    mock_code_op.execute_code = AsyncMock(return_value=mock_raw_result)

    mock_sys_op = MagicMock()
    mock_sys_op.code.return_value = mock_code_op
    return mock_sys_op


class TestSandboxCodeRunnerInit:
    @staticmethod
    def test_init_assigns_sys_operation():
        mock_sys_op = MagicMock()
        runner = SandboxCodeRunner(mock_sys_op)
        assert getattr(runner, "_sys_operation") is mock_sys_op


class TestSandboxCodeRunnerRun:
    @staticmethod
    @pytest.mark.asyncio
    async def test_run_success():
        mock_sys_op = make_mock_sys_op(
            exit_code=0, stdout='{"result": 42}'
        )
        runner = SandboxCodeRunner(mock_sys_op)
        result = await runner.run(
            user_code="def main(args): return {'result': 42}",
            inputs={"x": 1},
            timeout=300,
        )
        assert isinstance(result, CodeRunResult)
        assert result.result == {"result": 42}

    @staticmethod
    @pytest.mark.asyncio
    async def test_run_status_code_not_success():
        mock_sys_op = make_mock_sys_op(status_code="ERROR")
        runner = SandboxCodeRunner(mock_sys_op)
        with pytest.raises(Exception, match="execution error"):
            await runner.run(
                user_code="def main(args): return {}",
                inputs={},
                timeout=300,
            )

    @staticmethod
    @pytest.mark.asyncio
    async def test_run_exit_code_nonzero():
        mock_sys_op = make_mock_sys_op(
            exit_code=1, stderr="NameError: name 'x' is not defined"
        )
        runner = SandboxCodeRunner(mock_sys_op)
        with pytest.raises(Exception, match="NameError"):
            await runner.run(
                user_code="def main(args): return {}",
                inputs={},
                timeout=300,
            )

    @staticmethod
    @pytest.mark.asyncio
    async def test_run_stdout_not_json():
        mock_sys_op = make_mock_sys_op(exit_code=0, stdout="not json")
        runner = SandboxCodeRunner(mock_sys_op)
        with pytest.raises(Exception, match="Failed to parse sandbox code output as JSON"):
            await runner.run(
                user_code="def main(args): return {}",
                inputs={},
                timeout=300,
            )

    @staticmethod
    @pytest.mark.asyncio
    async def test_run_stdout_is_string_not_dict():
        mock_sys_op = make_mock_sys_op(exit_code=0, stdout='"string_value"')
        runner = SandboxCodeRunner(mock_sys_op)
        with pytest.raises(Exception, match="must return a dict"):
            await runner.run(
                user_code="def main(args): return {}",
                inputs={},
                timeout=300,
            )

    @staticmethod
    @pytest.mark.asyncio
    async def test_run_stdout_is_list_not_dict():
        mock_sys_op = make_mock_sys_op(exit_code=0, stdout="[1, 2, 3]")
        runner = SandboxCodeRunner(mock_sys_op)
        with pytest.raises(Exception, match="must return a dict"):
            await runner.run(
                user_code="def main(args): return {}",
                inputs={},
                timeout=300,
            )

    @staticmethod
    @pytest.mark.asyncio
    async def test_run_decimal_default_str():
        mock_sys_op = make_mock_sys_op(
            exit_code=0, stdout='{"val": "123.45"}'
        )
        runner = SandboxCodeRunner(mock_sys_op)
        result = await runner.run(
            user_code="def main(args): return {}",
            inputs={},
            timeout=300,
        )
        assert isinstance(result, CodeRunResult)
        assert result.result == {"val": "123.45"}

    @staticmethod
    @pytest.mark.asyncio
    async def test_run_execute_code_exception_propagates():
        mock_sys_op = MagicMock()
        mock_code_op = AsyncMock()
        mock_code_op.execute_code = AsyncMock(side_effect=RuntimeError("sandbox unreachable"))
        mock_sys_op.code.return_value = mock_code_op

        runner = SandboxCodeRunner(mock_sys_op)
        with pytest.raises(RuntimeError, match="sandbox unreachable"):
            await runner.run(
                user_code="def main(args): return {}",
                inputs={},
                timeout=300,
            )

    @staticmethod
    @pytest.mark.asyncio
    async def test_run_logs_warning():
        mock_sys_op = make_mock_sys_op(exit_code=0, stdout='{"result": 1}')
        runner = SandboxCodeRunner(mock_sys_op)

        with patch(
            "agent_runtime.extension.workflow_node.code_runner.sandbox_code_runner.workflow_logger"
        ) as mock_logger:
            await runner.run(
                user_code="def main(args): return {'result': 1}",
                inputs={},
                timeout=300,
            )
            mock_logger.warning.assert_called_once()
            call_args = mock_logger.warning.call_args[0][0]
            assert "[SandboxCodeRunner]" in call_args


class TestSandboxCodeRunnerWrapUserCode:
    @staticmethod
    def test_wrap_contains_user_code():
        wrapped = build_wrapped_code("def main(args): return {}", {"x": 1})
        assert "def main(args): return {}" in wrapped
        assert "args = {'x': 1}" in wrapped
        assert "json.dumps(result, default=str)" in wrapped

    @staticmethod
    def test_wrap_embeds_inputs():
        wrapped = build_wrapped_code("pass", {"x": 1, "y": "hello"})
        assert "args = {'x': 1, 'y': 'hello'}" in wrapped

    @staticmethod
    def test_wrap_empty_inputs():
        wrapped = build_wrapped_code("pass", {})
        assert "args = {}" in wrapped


class TestSandboxCodeRunnerExecuteWrappedCode:
    @staticmethod
    @pytest.mark.asyncio
    async def test_execute_passes_correct_params():
        mock_sys_op = MagicMock()
        mock_code_op = AsyncMock()
        mock_code_op.execute_code = AsyncMock(return_value=MagicMock())
        mock_sys_op.code.return_value = mock_code_op

        runner = SandboxCodeRunner(mock_sys_op)
        wrapped_code = "print('hello')"
        execute_fn = getattr(runner, "_execute_wrapped_code")
        await execute_fn(wrapped_code, timeout=300)

        mock_code_op.execute_code.assert_called_once_with(
            code=wrapped_code, language="python", timeout=300
        )
