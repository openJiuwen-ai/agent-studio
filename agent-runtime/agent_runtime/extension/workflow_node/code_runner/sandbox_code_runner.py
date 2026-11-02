# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2026. All rights reserved.

"""Sandbox code runner module - executes code via SysOperation SANDBOX mode."""

from typing import Any

from openjiuwen.core.common.logging import workflow_logger

from .base_code_runner import CodeRunner, CodeRunResult, build_wrapped_code, parse_execution_result


class SandboxCodeRunner(CodeRunner):
    """Sandbox code runner - executes code via SysOperation SANDBOX mode.

    Uses AIO sandbox container for isolated code execution.
    The SysOperation must be registered at startup with SANDBOX mode.
    """

    def __init__(self, sys_operation):
        self._sys_operation = sys_operation
        self.function_log: str = ""

    async def run(self, user_code: str, inputs: dict, timeout: int = 900) -> CodeRunResult:
        wrapped_code = build_wrapped_code(user_code, inputs)
        workflow_logger.warning("[SandboxCodeRunner] Executing code in sandbox mode")
        result = await self._execute_wrapped_code(wrapped_code, timeout)
        result_dict, function_log = parse_execution_result(result, runner_name="Sandbox code")
        self.function_log = function_log
        return CodeRunResult(result=result_dict, function_log=function_log)

    async def _execute_wrapped_code(self, wrapped_code: str, timeout: int) -> Any:
        code_op = self._sys_operation.code()
        return await code_op.execute_code(
            code=wrapped_code, language="python", timeout=timeout
        )
