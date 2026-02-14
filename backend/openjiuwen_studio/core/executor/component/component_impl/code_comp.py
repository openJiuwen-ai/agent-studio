#!/usr/bin/python3.10
# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved
import textwrap
from datetime import datetime
from typing import Any, Callable, Dict, List, Tuple, Union

from openjiuwen_studio.core.common.exceptions import BaseError
from openjiuwen.core.workflow import BranchRouter
from openjiuwen.core.workflow.components.condition.condition import Condition
from openjiuwen.core.graph.base import Graph
from openjiuwen.core.session import BaseSession

from openjiuwen.core.workflow import WorkflowComponent, Input, Output
from openjiuwen.core.context_engine import ModelContext
from openjiuwen.core.workflow.components import Session

from openjiuwen_studio.core.common.dsl import CodeLanguage, ExceptHandlingMethod, ExceptConfig, CodeConfig, ErrorBody
from openjiuwen_studio.core.executor.component.code_runner.base import CodeRunner
from openjiuwen_studio.core.executor.component.code_runner.remote import remote_code_runner
from openjiuwen_studio.core.common.exceptions import JiuWenExecuteException
from openjiuwen_studio.core.common.status_code import StatusCode


class ExceptedCondition(Condition):
    def __init__(self, excepted: bool = False) -> None:
        super().__init__()
        self.excepted: bool = excepted

    def set_excepted(self, excepted: bool) -> None:
        self.excepted = excepted

    def invoke(self, inputs: Input, session: BaseSession) -> bool:
        return self.excepted


class DefaultCondition(Condition):
    def __init__(self, excepted_condition: ExceptedCondition) -> None:
        super().__init__()
        self.excepted_condition = excepted_condition

    def invoke(self, inputs: Input, session: BaseSession) -> bool:
        return not self.excepted_condition.invoke(inputs, session)


DEFAULT_PY_CODE = """
class Args:
    def __init__(self, params):
        self.params = params

class Outputs(dict):
    pass
"""

DEFAULT_JS_CODE = """
class Args {
    constructor(params) {
        this.params = params;
    }
}
"""


class CodeComponent(WorkflowComponent):
    def __init__(self, node_id: str, conf: CodeConfig) -> None:
        self.conf = conf
        self.node_id = node_id
        self._router = BranchRouter()
        self.excepted_condition: ExceptedCondition = None

    def set_excepted_condition(self, excepted_condition: ExceptedCondition) -> None:
        self.excepted_condition = excepted_condition

    def add_branch(self, condition: Union[str, Callable[[], bool], Condition], target: Union[str, List[str]],
                   branch_id: str = None) -> None:
        if isinstance(target, str):
            target = [target]
        self._router.add_branch(condition, target, branch_id=branch_id)

    def add_component(self, graph: Graph, node_id: str, wait_for_all: bool = False) -> None:
        graph.add_node(node_id, self.to_executable(), wait_for_all=wait_for_all)
        graph.add_conditional_edges(node_id, self._router)

    async def invoke(self, inputs: Input, session: Session, context: ModelContext) -> Output:
        self._router.set_session(session)
        code = self.conf.code
        language = self.conf.language
        execute_type = self.conf.execute_type
        exception_config = self.conf.exception_config

        if not code.strip():
            raise JiuWenExecuteException(
                StatusCode.CODE_COMPONENT_INVOKE_ERROR.code,
                StatusCode.CODE_COMPONENT_INVOKE_ERROR.errmsg.format(msg="No code provided for execution"),
                node_id=self.node_id
            )

        error_body, response = await self._run(language, code, inputs, exception_config, execute_type)

        final_result = self._process_output(error_body, response, exception_config)
        return final_result

    @staticmethod
    async def _run(language: str, code: str, params: Input, except_config: ExceptConfig,
                   execute_type: str) -> Tuple[ErrorBody, Any]:
        # 只支持remote执行，移除local支持
        run_func = remote_code_runner.run

        if language in [CodeLanguage.PYTHON, CodeLanguage.PYTHON3]:
            language = CodeLanguage.PYTHON
            dedented_code = textwrap.dedent(DEFAULT_PY_CODE + "\n" + code)
        else:
            language = CodeLanguage.JAVASCRIPT
            dedented_code = DEFAULT_JS_CODE + "\n" + code

        return await CodeRunner.run_with_retry(except_config.max_retries, run_func,
                                               code_language=language,
                                               code_str=dedented_code,
                                               timeout=except_config.timeout_seconds,
                                               params=params)

    def _process_output(self, error_body: ErrorBody, response: Any, except_config: ExceptConfig) -> Dict[str, Any]:
        output_params = self.conf.output_params
        response_result: Dict[str, Any] = {}

        if error_body.error_code:
            response_result = self._process_error_body(except_config, error_body, self.excepted_condition,
                                                       response_result)
        else:
            if response:
                for param in output_params:
                    raw_value = response.get(param.name)
                    if not raw_value and param.type != "bool":
                        response_result[param.name] = None
                        continue
                    # 按 ParamConfig.type 做类型校验和强制转换
                    response_result[param.name] = self._convert_output_value(
                        param_name=param.name,
                        value=raw_value,
                        expect_type=param.type,
                    )
            response_result["is_success"] = True

        return response_result

    def _convert_output_value(self, param_name: str, value: Any, expect_type: str) -> Any:
        """
        根据 ParamConfig.type 对输出参数做类型校验和强制转换。
        转换失败时抛 JiuWenExecuteException。
        """
        try:
            if expect_type == "string":
                # 任意值都可转成字符串
                return str(value)

            if expect_type == "bool" or expect_type == "boolean":
                if not isinstance(value, bool):
                    raise ValueError(f"expected boolean, but got {type(value).__name__}")
                return value

            if expect_type == "int" or expect_type == "integer":
                # int类型：支持int、float、数字字符串转换
                if isinstance(value, int):
                    return value
                elif isinstance(value, float):
                    # 浮点数转int，会截断小数部分
                    return int(value)
                elif isinstance(value, str):
                    # 字符串转int，先尝试直接转int，失败则尝试转float再转int
                    try:
                        return int(value)
                    except ValueError:
                        try:
                            # 处理浮点数字符串
                            return int(float(value))
                        except (ValueError, TypeError) as e:
                            raise ValueError(f"can not convert '{value}' into integer") from e
                else:
                    raise ValueError(f"expected integer, but got {type(value).__name__}")

            if expect_type == "float" or expect_type == "number":
                # float类型：支持int、float、数字字符串转换
                if isinstance(value, (int, float)):
                    return float(value)
                elif isinstance(value, str):
                    try:
                        return float(value)
                    except (ValueError, TypeError) as e:
                        raise ValueError(f"can not convert '{value}' into float") from e
                else:
                    raise ValueError(f"expected float, but got {type(value).__name__}")

            if expect_type == "list" or expect_type == "array":
                if not isinstance(value, list):
                    raise ValueError(f"expected list, but got {type(value).__name__}")
                return value

            if expect_type == "object":
                if isinstance(value, dict):
                    return value
                raise ValueError(f"expected dict, got {type(value).__name__}")

            if expect_type == "date-time":
                if isinstance(value, str):
                    try:
                        # 返回字符串更安全，避免后续状态序列化 datetime 对象时出现兼容问题
                        normalized = value.replace("Z", "+00:00")
                        dt = datetime.fromisoformat(normalized)
                        return dt.isoformat()
                    except Exception as e:
                        raise ValueError(f"can not convert '{value}' into datetime") from e
                raise ValueError(f"expected date-time, got {type(value).__name__}")

            # 未知类型：直接返回原值或按需抛错，这里选择抛错更安全
            raise ValueError(f"unsupported expect_type '{expect_type}'")

        except Exception as e:
            # 转换失败时抛执行异常，便于前端/调用方感知
            message = (
                f"{StatusCode.CODE_COMPONENT_INVOKE_ERROR.errmsg}: "
                f"output param '{param_name}' {e.args} "
                f"value={value!r}"
            )
            raise JiuWenExecuteException(
                code=StatusCode.CODE_COMPONENT_INVOKE_ERROR.code,
                message=message,
                node_id=self.node_id,
            ) from e

    @staticmethod
    def _process_error_body(except_config: ExceptConfig, error_body: ErrorBody, excepted_condition: ExceptedCondition,
                            response_result: Dict[str, Any]) -> Dict[str, Any]:
        # 处理异常策略
        if except_config.except_handling_method == ExceptHandlingMethod.BREAK:
            raise BaseError(
                code=error_body.error_code,
                message=error_body.error_message,
            )
        elif except_config.except_handling_method == ExceptHandlingMethod.EXECUTE_EXCEPT_STEP:
            excepted_condition.set_excepted(True)
        else:
            response_result = except_config.return_content

        response_result["error_body"] = error_body.model_dump()
        response_result["is_success"] = False

        return response_result
