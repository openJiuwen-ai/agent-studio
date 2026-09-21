# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.

"""
FlowSql - SQL 执行组件

通过 HTTP 调用 Java manager 的 SQL 执行 API，实现工作流中的数据库访问能力。
Python 侧无需安装数据库驱动或管理连接池，全部由 Java manager 处理。

支持两种模式（IR 适配器转换后统一为 sql + conditions）：
- 直接 SQL 模式：用户直接编写 SQL 语句
- 可视化查询模式：IR 适配器已构建为完整 SQL + conditions 参数列表
"""

import os
import re
import time
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import aiohttp

from jiuwen.extension.workflow_node.utils import JiuWenBaseException
from openjiuwen.core.common.logging import workflow_logger, LogEventType
from openjiuwen.core.context_engine import ModelContext
from openjiuwen.core.graph.executable import Input, Output
from openjiuwen.core.session.node import Session
from openjiuwen.core.workflow.components.component import WorkflowComponent

MANAGER_ENDPOINT = os.getenv("AGENT_MANAGER_ENDPOINT", "")
SQL_EXECUTE_URL_TEMPLATE = "{}/v1/studio/datasources/{}/execute"
REQUEST_TIMEOUT = int(os.getenv("DATASOURCE_EXECUTE_TIMEOUT", "25"))

USER_FIELDS = "userFields"


class FlowSqlStatusCode(Enum):
    """FlowSql 组件专用错误码"""

    SUCCESS = (0, "success")
    SQL_INIT_ERROR = (101750, "Sql component init error. msg={msg}")
    SQL_EXECUTE_ERROR = (101751, "Sql component execute error")
    DATASOURCE_NOT_FOUND = (101753, "Datasource not found: {datasourceId}")


class FlowSql(WorkflowComponent):
    """SQL 执行组件

    通过 HTTP 调用 Java manager 的 SQL 执行 API。
    支持两种模式（IR 转换后统一为 sql + conditions）：
    - 直接 SQL 模式：用户直接编写 SQL 语句
    - 可视化查询模式：IR 适配器已构建为完整 SQL
    """

    def __init__(self, conf: dict = None):
        super().__init__()
        self._conf = conf or {}
        self._datasource_id: Optional[str] = None
        self._sql: Optional[str] = None
        self._conditions: list = []
        if conf:
            self.init(conf)

    def init(self, conf: dict, **kwargs):
        self._conf = conf
        self._datasource_id = conf.get("id")
        self._sql = conf.get("sql")
        self._conditions = conf.get("conditions", [])

    def component_type(self) -> str:
        return "jiuwen.sql"

    @staticmethod
    def _render_template(template: str, variables: Dict[str, Any]) -> str:
        """替换模板中的 {{variable}} 占位符。"""
        if not isinstance(template, str) or not variables:
            return template
        result = template
        for key, value in variables.items():
            if value is not None:
                result = result.replace("{{" + key + "}}", str(value))
        return result

    _PARAM_PATTERN = re.compile(r"""['"]?\{\{(\w+)\}\}['"]?""")

    @classmethod
    def _parameterize_template(
        cls, template: str, variables: Dict[str, Any]
    ) -> Tuple[str, List[str]]:
        """将模板中的 {{variable}} 替换为 ? 占位符，并按出现顺序收集参数值。

        去除占位符两侧可能存在的引号，使 ? 成为 PreparedStatement 的裸占位符。
        对于可视化查询模式（SQL 已含 ? 且无 {{}}），返回结果不变。
        """
        if not isinstance(template, str) or not variables:
            return template, []

        params: List[str] = []

        def replace_match(match: re.Match) -> str:
            key = match.group(1)
            value = variables.get(key)
            if value is not None:
                params.append(str(value))
                return "?"
            return match.group(0)

        result = cls._PARAM_PATTERN.sub(replace_match, template)
        return result, params

    async def invoke(
        self, inputs: Input, session: Session, context: ModelContext
    ) -> Output:
        start_time = time.perf_counter()
        workflow_logger.info(
            "FlowSql invoke started",
            event_type=LogEventType.WORKFLOW_COMPONENT_START,
            component_type_str="FlowSql",
            metadata={"datasource_id": self._datasource_id},
        )

        try:
            user_fields = self._extract_user_fields(inputs)
            result = await self._call_execute_api(user_fields)
            outputs = {
                USER_FIELDS: {
                    "output_list": result.get("outputList", []),
                    "row_num": result.get("rowNum", 0),
                }
            }

            duration = round((time.perf_counter() - start_time) * 1000)
            workflow_logger.info(
                "FlowSql invoke completed",
                event_type=LogEventType.WORKFLOW_COMPONENT_END,
                component_type_str="FlowSql",
                metadata={
                    "datasource_id": self._datasource_id,
                    "duration_ms": duration,
                },
            )
            return outputs

        except Exception as e:
            if isinstance(e, JiuWenBaseException):
                raise
            workflow_logger.error(
                "FlowSql invoke error: %s: %s",
                type(e).__name__,
                e,
                event_type=LogEventType.WORKFLOW_COMPONENT_ERROR,
                component_type_str="FlowSql",
            )
            raise JiuWenBaseException(
                error_code=FlowSqlStatusCode.SQL_EXECUTE_ERROR.value[0],
                message=FlowSqlStatusCode.SQL_EXECUTE_ERROR.value[1],
            ) from e

    @staticmethod
    def _extract_user_fields(inputs: Input) -> dict:
        """从 inputs 中提取 userFields。"""
        if inputs is None:
            return {}
        if isinstance(inputs, dict):
            if USER_FIELDS in inputs:
                user_fields = inputs[USER_FIELDS]
                return user_fields if isinstance(user_fields, dict) else {}
            return inputs
        return {}

    async def _call_execute_api(self, user_fields: dict) -> dict:
        """调用 Java manager 的 SQL 执行 API"""
        url = SQL_EXECUTE_URL_TEMPLATE.format(
            MANAGER_ENDPOINT, self._datasource_id
        )
        sql, sql_params = self._parameterize_template(self._sql, user_fields)
        rendered_conditions = [
            self._render_template(c, user_fields) for c in self._conditions
        ]
        conditions = sql_params + rendered_conditions
        body = {
            "query": sql,
            "conditions": conditions or None,
        }
        timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
        async with aiohttp.ClientSession(timeout=timeout) as http_session:
            async with http_session.post(url, json=body) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    raise JiuWenBaseException(
                        error_code=FlowSqlStatusCode.SQL_EXECUTE_ERROR.value[0],
                        message=f"Manager execute API failed: {resp.status}: {error_text}",
                    )
                return await resp.json()
