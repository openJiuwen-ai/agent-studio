# coding: utf-8
"""进程内代码执行器 - 使用 exec() 在当前进程内执行代码

对齐旧版 custom_code.py 的 _execute_code_safely() 实现。
无子进程开销，适用于 exec_env=local 且 LOCAL_CODE_EXEC_MODE=inprocess 的场景。
"""

import copy
import threading
import traceback
from unittest import mock

from agent_runtime.extension.workflow_node.code_runner.base_code_runner import CodeRunner
from openjiuwen.core.common.exception.codes import StatusCode
from openjiuwen.core.common.exception.errors import build_error


class InprocessCodeRunner(CodeRunner):
    """进程内代码执行器 - 使用 exec() 在当前进程内执行代码

    无子进程开销，适用于 exec_env=local 且 LOCAL_CODE_EXEC_MODE=inprocess 的场景。
    """

    # stdout 重定向前缀：exec 体内先建 StringIO 并接管 sys.stdout
    _PROLOGUE = (
        "import sys\n"
        "import io\n"
        "buffer = io.StringIO()\n"
        "original_stdout = sys.stdout\n"
        "sys.stdout = buffer\n"
    )
    # stdout 恢复 + console_log 提取后缀：在 try/finally 中还原并收集 print 输出
    _EPILOGUE = (
        "\ntry:\n"
        "    res = main(args)\n"
        "finally:\n"
        "    sys.stdout = original_stdout\n"
        "    console_log = buffer.getvalue()\n"
    )

    def __init__(self):
        self.function_log: str = ""
        # 复用 os.system patcher：实例级单例，避免每次 run() 重建 _patch 对象。
        # os.system 为进程级全局属性，patch 期间影响全进程；用 _exec_lock 串行
        # start/stop，使并发调用下全局补丁不竞争，并保持与旧版同步 exec 等价的串行语义。
        self._os_system_patcher = mock.patch('os.system', return_value=-1)
        self._exec_lock = threading.Lock()

    async def run(self, user_code: str, inputs: dict, timeout: int = 300) -> dict:
        """在进程内执行用户代码

        Args:
            user_code: 用户源代码（包含 main 函数定义）
            inputs: 输入参数字典，传递给 main 函数
            timeout: 超时时间（秒），进程内模式不使用此参数

        Returns:
            dict: main 函数的返回值

        Raises:
            Exception: 执行失败时抛出原始异常
            BuildError: 返回值非 dict 时抛出

        Note:
            exec() 与 deepcopy 均为同步 CPU 活，此处直接在 event loop 线程同步执行，
            会阻塞 event loop, 但可以降低代码节点单次执行延迟
            同步 exec 无法被硬中断，timeout 仍不生效 —— 需硬超时请走
            subprocess 模式（LocalCodeRunner）。
        """
        return self._exec_sync(user_code, inputs)

    def _exec_sync(self, user_code: str, inputs: dict) -> dict:
        """同步执行用户代码（由 run() 在 event loop 线程直接同步调用）"""
        # 1. 深拷贝 inputs 防止污染
        inputs = copy.deepcopy(inputs)

        # 2. 构建执行代码：stdout 重定向 + 用户代码 + try/finally 恢复
        exec_code = self._PROLOGUE + user_code + self._EPILOGUE

        # 3. 执行代码（复用 os.system patcher）
        env = {
            "args": inputs,
            "__builtins__": __builtins__,
            "__name__": "__main__",
        }
        global_namespace = env
        local_namespace = env
        exec_exception = None
        error_log = None

        with self._exec_lock:
            self._os_system_patcher.start()
            try:
                exec(exec_code, global_namespace, local_namespace)
            except Exception as e:
                error_log = traceback.format_exc()
                exec_exception = e
            finally:
                self._os_system_patcher.stop()

        # 4. 提取结果
        res = local_namespace.get("res", {})
        console_log = local_namespace.get("console_log", "")

        # 5. 错误 traceback 追加到 console_log（对齐旧版截取逻辑）
        # +17 = len('local_namespace')，截取变量名之后的 traceback 部分
        if error_log is not None:
            console_log += error_log[error_log.find('local_namespace') + 17:]

        # 6. 记录 function_log
        self.function_log = console_log

        # 7. 重新抛出异常
        if exec_exception is not None:
            raise exec_exception

        # 8. 返回值类型校验
        if not isinstance(res, dict):
            raise build_error(
                StatusCode.WORKFLOW_COMPONENT_SCHEMA_INVALID,
                comp_id="flow_code",
                reason="main() must return a dict",
                workflow="n/a",
            )

        return res
