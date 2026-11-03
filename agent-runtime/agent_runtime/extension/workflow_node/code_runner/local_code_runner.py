# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2026. All rights reserved.

"""本地代码执行器模块 - 基于 subprocess 的代码执行实现"""

from typing import Any

from openjiuwen.core.sys_operation.local.utils import OperationUtils

from .base_code_runner import CodeRunner, CodeRunResult, build_wrapped_code, parse_execution_result


class LocalCodeRunner(CodeRunner):
    """本地代码执行器 - 使用 CodeOperation LOCAL mode（subprocess）

    将用户代码包装为独立的 Python 子进程执行，提供进程级别的安全隔离。
    """

    def __init__(self, code_operation):
        self._code_operation = code_operation
        self.function_log: str = ""

    async def run(self, user_code: str, inputs: dict, timeout: int = 900) -> CodeRunResult:
        wrapped_code = build_wrapped_code(user_code, inputs)
        result = await self._execute_wrapped_code(wrapped_code, timeout)
        result_dict, function_log = parse_execution_result(result, runner_name="Code")
        self.function_log = function_log
        return CodeRunResult(result=result_dict, function_log=function_log)

    async def _execute_wrapped_code(self, wrapped_code: str, timeout: int) -> Any:
        """通过 CodeOperation 执行包装后的代码（subprocess 方式）"""
        env = OperationUtils.prepare_environment(None)

        return await self._code_operation.execute_code(
            code=wrapped_code,
            language="python",
            timeout=timeout,
            environment=env,
            options={"encoding": "utf-8"},
        )


def create_local_code_runner(code_operation) -> LocalCodeRunner:
    """工厂函数 - 创建 LocalCodeRunner 实例"""
    return LocalCodeRunner(code_operation)
