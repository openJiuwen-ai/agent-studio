# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2026. All rights reserved.

"""
FlowCode - 代码节点组件
"""

from __future__ import annotations

import json
import os
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Dict, Union
from unittest import mock

from openjiuwen.core.common.constants.constant import USER_FIELDS
from openjiuwen.core.common.exception.codes import StatusCode
from openjiuwen.core.common.exception.errors import build_error
from openjiuwen.core.common.logging import LogEventType, workflow_logger
from openjiuwen.core.context_engine import ModelContext
from openjiuwen.core.graph.executable import Input, Output
from openjiuwen.core.session.node import Session
from openjiuwen.core.workflow.components.component import WorkflowComponent

JIUWEN_CODE_TYPE = "jiuwen.code"


@dataclass
class FlowCodeConfig:
    code: str = ""
    user_fields: dict = field(default_factory=dict)
    exec_env: str = "local"


class FlowCode(WorkflowComponent):
    """工作流代码节点"""

    def __init__(self, conf: Union[FlowCodeConfig, dict, None] = None):
        super().__init__()
        self._conf = None
        # 允许无参初始化，配置验证延迟到 init() 方法
        if conf is not None:
            self._init_conf(conf)

    def _init_conf(self, conf: Union[FlowCodeConfig, dict]):
        """Initialize configuration with validation"""
        try:
            if isinstance(conf, dict):
                self._conf = FlowCodeConfig(
                    code=conf.get("code", ""),
                    user_fields=conf.get("userFields", {}),
                    exec_env=conf.get("exec_env", "local"),
                )
            else:
                self._conf = conf
        except Exception as e:
            raise build_error(
                StatusCode.WORKFLOW_COMPONENT_SCHEMA_INVALID,
                comp_id="flow_code",
                reason=str(e),
                workflow="n/a",
                cause=e,
            )

        if not self._conf.code:
            raise build_error(
                StatusCode.WORKFLOW_COMPONENT_SCHEMA_INVALID,
                comp_id="flow_code",
                reason="code must be a non-empty string",
                workflow="n/a",
            )

        if self._conf.exec_env not in ("local", "sandbox", ""):
            workflow_logger.warning(
                f"Unsupported exec_env: {self._conf.exec_env}, falling back to local",
            )
            self._conf = FlowCodeConfig(
                code=self._conf.code,
                user_fields=self._conf.user_fields,
                exec_env="local",
            )

    def init(self, conf=None, **kwargs):
        """兼容遗留工作流引擎的两阶段初始化"""
        if conf is not None:
            self._init_conf(conf)
        # 调用父类的 init 方法处理其他初始化逻辑
        super().init(**kwargs)

    def component_type(self) -> str:
        return JIUWEN_CODE_TYPE

    def _check_blacklist(self, code: str) -> None:
        clean_code = " ".join(code.split())
        black_list = json.loads(os.environ.get("CODE_BLACK_LIST", "[]"))
        if black_list:
            black_keyword = next((kw for kw in black_list if kw in clean_code), None)
            if black_keyword:
                raise build_error(
                    StatusCode.WORKFLOW_COMPONENT_EXECUTION_ERROR,
                    comp="flow_code",
                    ability="invoke",
                    reason=f"{black_keyword} is in the code black list",
                    workflow="n/a",
                )

    def _build_execution_code(self, user_code: str) -> str:
        return (
            "import sys\n"
            "import io\n"
            "buffer = io.StringIO()\n"
            "original_stdout = sys.stdout\n"
            "sys.stdout = buffer\n" + user_code + "\ntry:\n"
            "    res = main(args)\n"
            "finally:\n"
            "    sys.stdout = original_stdout\n"
            "    console_log = buffer.getvalue()\n"
        )

    async def _execute_code(self, code: str, inputs: dict) -> dict:
        self._check_blacklist(code)
        exec_code = self._build_execution_code(code)
        inputs = deepcopy(inputs)

        with mock.patch("os.system") as mock_system:
            mock_system.return_value = -1
            namespace: Dict[str, Any] = {
                "args": inputs,
                "__builtins__": __builtins__,
                "__name__": "__main__",
            }
            exec_exception = None
            try:
                exec(exec_code, namespace, namespace)
            except Exception as e:
                exec_exception = e

            res = namespace.get("res", {})
            console_log = namespace.get("console_log", "")

            if console_log:
                workflow_logger.debug(
                    "FlowCode console output",
                    console_log=console_log[:500],
                )

            if exec_exception is not None:
                raise exec_exception

            if not isinstance(res, dict):
                raise build_error(
                    StatusCode.WORKFLOW_COMPONENT_SCHEMA_INVALID,
                    comp_id="flow_code",
                    reason="Code must return a dict from main()",
                    workflow="n/a",
                )

            return res

    async def _async_execute_in_security_sandbox(
        self, cur_code: str, inputs: dict
    ) -> dict:
        """
        在安全沙箱中执行代码片段
        参数：
            cur_code：待执行的代码片段
            inputs：代码片段的入参
        """

        workflow_logger.warning(
            f"Unsupported exec_env: {self._conf.exec_env}, falling back to local",
        )
        return await self._execute_code(cur_code, inputs)

    async def invoke(
        self, inputs: Input, session: Session, context: ModelContext
    ) -> Output:
        try:
            workflow_logger.debug(
                "FlowCode component invoke started",
                event_type=LogEventType.WORKFLOW_COMPONENT_START,
                component_id=session.get_component_id(),
                component_type_str=JIUWEN_CODE_TYPE,
                session_id=session.get_session_id(),
            )

            user_fields = inputs.get(USER_FIELDS, inputs) if inputs else {}

            if self.config.exec_env == "sandbox":
                result = await self._async_execute_in_security_sandbox(
                    self._conf.code, user_fields
                )
            else:
                result = await self._execute_code(self._conf.code, user_fields)

            workflow_logger.debug(
                "FlowCode component invoke succeeded",
                event_type=LogEventType.WORKFLOW_COMPONENT_END,
                component_id=session.get_component_id(),
                component_type_str=JIUWEN_CODE_TYPE,
                session_id=session.get_session_id(),
            )

            return {USER_FIELDS: result}

        except Exception as e:
            workflow_logger.error(
                "FlowCode invoke failed",
                event_type=LogEventType.WORKFLOW_COMPONENT_ERROR,
                component_id=session.get_component_id(),
                component_type_str=JIUWEN_CODE_TYPE,
                session_id=session.get_session_id(),
                exception=e,
            )
            raise build_error(
                StatusCode.WORKFLOW_COMPONENT_EXECUTION_ERROR,
                comp=session.get_component_id(),
                ability="invoke",
                reason=str(e),
                workflow=session.get_workflow_id(),
                cause=e,
            )

    async def stream(
        self, inputs: Input, session: Session, context: ModelContext
    ) -> AsyncIterator[Output]:
        result = await self.invoke(inputs, session, context)
        yield result

    @property
    def node_type(self) -> str:
        return JIUWEN_CODE_TYPE

    @property
    def config(self) -> FlowCodeConfig:
        return self._conf


__all__ = [
    "FlowCode",
    "FlowCodeConfig",
    "JIUWEN_CODE_TYPE",
]
