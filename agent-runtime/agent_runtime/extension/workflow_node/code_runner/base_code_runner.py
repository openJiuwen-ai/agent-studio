"""代码执行器统一接口与公共逻辑"""

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from openjiuwen.core.common.exception.codes import StatusCode
from openjiuwen.core.common.exception.errors import build_error


@dataclass
class CodeRunResult:
    """代码执行结果（含 function_log），避免依赖实例级共享状态。

    所有 runner 的 run() 统一返回此对象，调用方从返回值获取 function_log，
    而非读取 self.function_log——后者在并发调用下会被覆盖。
    向后兼容：runner 仍会同步设置 self.function_log 供未改造的调用方使用。
    """

    result: dict
    function_log: str = ""


class CodeRunner(ABC):
    """代码执行器统一接口

    所有代码执行器（本地、沙箱、Wasm等）都实现此接口。
    上层调用方只需要知道 run() 方法，不关心底层实现。
    """

    @abstractmethod
    async def run(self, user_code: str, inputs: dict, timeout: int = 900) -> CodeRunResult:
        """
        执行用户代码并返回结果

        Args:
            user_code: 用户源代码（包含 main 函数定义）
            inputs: 输入参数字典，传递给 main 函数
            timeout: 超时时间（秒）

        Returns:
            CodeRunResult: 包含 result(dict) 和 function_log(str) 的结果对象

        Raises:
            Exception: 执行失败或返回值非法
        """
        pass


def build_wrapped_code(user_code: str, inputs: dict) -> str:
    """将用户代码包装为可执行的 Python 脚本

    包装逻辑：
    1. import sys, json, io
    2. 将用户 stdout 重定向到 StringIO，避免 print() 污染 JSON 输出
    3. 注入用户代码
    4. 将输入数据序列化为 Python 字面量并赋值给 args 变量
    5. 调用 main(args)，恢复 stdout，将 print 输出写入 stderr
    6. 将结果以 JSON 格式输出到 stdout

    注意：输入数据直接嵌入脚本中，避免 stdin 通信导致的死锁问题。
    """
    inputs_literal = repr(inputs)

    return f"""
import sys
import json
import io

# 将用户 stdout 重定向到 StringIO，避免 print() 污染 JSON 输出
_console_buffer = io.StringIO()
_original_stdout = sys.stdout
sys.stdout = _console_buffer

# ===== 用户代码开始 =====
{user_code}
# ===== 用户代码结束 =====

# 输入参数（直接嵌入脚本，避免 stdin 通信问题）
args = {inputs_literal}

# 调用 main 函数
try:
    result = main(args)
finally:
    # 恢复 stdout，将 print 输出写入 stderr（作为 function_log）
    sys.stdout = _original_stdout
    _console_log = _console_buffer.getvalue()
    if _console_log:
        sys.stderr.write(_console_log)

# 输出 JSON 结果到 stdout（default=str 处理 Decimal 等非标准 JSON 类型）
print(json.dumps(result, default=str))
"""


def parse_execution_result(raw_result: Any, runner_name: str = "Code") -> tuple[dict, str]:
    """解析代码执行结果，提取 JSON 输出和 function_log

    Args:
        raw_result: CodeOperation.execute_code() 的返回值
        runner_name: 执行器名称，用于错误信息（如 "Code", "Sandbox code"）

    Returns:
        (result_dict, function_log) 元组

    Raises:
        BuildError: 执行失败或返回值非法
    """
    if raw_result.code != StatusCode.SUCCESS.code:
        raise build_error(
            StatusCode.WORKFLOW_COMPONENT_EXECUTION_ERROR,
            comp="flow_code",
            ability="execute",
            reason=raw_result.message,
            workflow="n/a",
        )

    function_log = (raw_result.data.stderr or "").strip()

    if raw_result.data.exit_code != 0:
        raise build_error(
            StatusCode.WORKFLOW_COMPONENT_EXECUTION_ERROR,
            comp="flow_code",
            ability="execute",
            reason=f"{runner_name} exited with status {raw_result.data.exit_code}: {raw_result.data.stderr}",
            workflow="n/a",
        )

    try:
        result_dict = json.loads(raw_result.data.stdout.strip())
    except json.JSONDecodeError as e:
        raise build_error(
            StatusCode.WORKFLOW_COMPONENT_EXECUTION_ERROR,
            comp="flow_code",
            ability="execute",
            reason=f"Failed to parse {runner_name.lower()} output as JSON: {e}",
            workflow="n/a",
        ) from e

    if not isinstance(result_dict, dict):
        raise build_error(
            StatusCode.WORKFLOW_COMPONENT_SCHEMA_INVALID,
            comp_id="flow_code",
            reason=f"{runner_name} must return a dict from main()",
            workflow="n/a",
        )

    return result_dict, function_log
