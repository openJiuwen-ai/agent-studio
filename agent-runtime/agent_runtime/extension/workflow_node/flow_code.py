# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2026. All rights reserved.

"""
FlowCode - 代码节点组件（基于 LocalCodeRunner，subprocess 执行）
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import AsyncIterator, Optional, Union

from agent_runtime.extension.workflow_node.code_runner import (
    CodeRunner,
)
from agent_runtime.extension.workflow_node.code_runner.result_cache import (
    get_code_result_cache,
    make_cache_key,
)
from openjiuwen.core.common.constants.constant import USER_FIELDS
from openjiuwen.core.common.exception.codes import StatusCode
from openjiuwen.core.common.exception.errors import build_error
from openjiuwen.core.common.logging import LogEventType, workflow_logger
from openjiuwen.core.context_engine import ModelContext
from openjiuwen.core.graph.executable import Input, Output
from openjiuwen.core.session.node import Session
from openjiuwen.core.workflow.components.component import WorkflowComponent

JIUWEN_CODE_TYPE = "jiuwen.code"

_TYPE_COERCION_MAP: dict[str, type] = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
    "object": dict,
    "array": list,
}

_ARRAY_ITEM_TYPE_MAP: dict[str, type] = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
    "object": dict,
}


def _coerce_value(value, target_type: str, *, input_mode: bool = False):
    """根据 schema type 定义对值做强制类型转换。

    Args:
        value: 原始值
        target_type: IR schema 中的 type 字段值（如 "integer", "array<number>" 等）
        input_mode: 输入模式，为 True 时对 None 做默认值填充（如 string → ""）

    Returns:
        转换后的值；转换失败时返回原值不做变更
    """
    if value is None:
        if input_mode:
            if target_type == "string":
                return ""
            if target_type == "array" or target_type.startswith("array<"):
                return []
            if target_type == "object":
                return {}
        return value

    # 处理 array<T> 类型，如 "array<string>", "array<number>", "array<integer>"
    if target_type.startswith("array<") and target_type.endswith(">"):
        item_type_str = target_type[6:-1].strip()
        item_type = _ARRAY_ITEM_TYPE_MAP.get(item_type_str)
        # 如果值是字符串，先尝试 JSON 解析为列表
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                return value
        if not isinstance(value, list):
            return value
        if item_type is None:
            return value
        return [_coerce_value(item, item_type_str) for item in value]

    # 基础类型转换
    coercion_fn = _TYPE_COERCION_MAP.get(target_type)
    if coercion_fn is None:
        return value

    try:
        # bool 必须在 int 之前判断，因为 bool 是 int 的子类
        if target_type == "boolean":
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.lower() in ("true", "1", "yes")
            return bool(value)

        if target_type == "integer":
            if isinstance(value, bool):
                return int(value)
            if isinstance(value, int):
                return value
            return int(value)

        if target_type == "number":
            if isinstance(value, bool):
                return float(value)
            return float(value)

        if target_type == "string":
            if isinstance(value, bool):
                return str(value)
            return coercion_fn(value)

        if target_type == "object":
            if isinstance(value, dict):
                return value
            if isinstance(value, str):
                return json.loads(value)
            return value

        if target_type == "array":
            if isinstance(value, list):
                return value
            if isinstance(value, str):
                return json.loads(value)
            return value

        return coercion_fn(value)
    except (ValueError, TypeError):
        return value


def _resolve_field_type(field_def: dict) -> str | None:
    """从 IR 字段定义中解析完整类型。

    当 type 为 "array" 时，从 schema 子字段读取元素类型，合成为 "array<T>" 格式。

    Args:
        field_def: IR 字段定义，包含 id, type, 可选 schema 等字段

    Returns:
        解析后的完整类型字符串，如 "integer", "array<integer>" 等
    """
    field_type = field_def.get("type")
    if not field_type:
        return None

    if field_type == "array":
        schema = field_def.get("schema")
        if isinstance(schema, dict) and schema.get("type"):
            return f"array<{schema['type']}>"

    return field_type


def _coerce_outputs(result_dict: dict, outputs_schema: list[dict]) -> dict:
    """根据 output schema 对 Code 节点的输出结果做类型转换。

    Args:
        result_dict: 代码执行返回的原始结果字典
        outputs_schema: IR 中定义的 outputs schema 列表，每项包含 id, type 等字段

    Returns:
        类型转换后的结果字典
    """
    if not outputs_schema or not isinstance(result_dict, dict):
        return result_dict

    type_map: dict[str, str] = {}
    for field_def in outputs_schema:
        if isinstance(field_def, dict) and "id" in field_def:
            resolved = _resolve_field_type(field_def)
            if resolved:
                type_map[field_def["id"]] = resolved

    if not type_map:
        return result_dict

    coerced = {}
    for key, value in result_dict.items():
        target_type = type_map.get(key)
        if target_type:
            coerced[key] = _coerce_value(value, target_type)
        else:
            coerced[key] = value
    return coerced


def _coerce_inputs(user_fields: dict, inputs_schema: list[dict]) -> dict:
    """根据 input schema 对 Code 节点的输入做类型转换（含 None 默认值填充）。

    当上游节点未提供值导致输入为 None 时，根据 schema 类型做合理默认值填充：
    - string 类型: None → ""
    - 其他类型: 保持 None 不变

    Args:
        user_fields: 上游传入的原始输入字典
        inputs_schema: IR 中定义的 inputs schema 列表，每项包含 id, type 等字段

    Returns:
        类型转换后的输入字典
    """
    if not inputs_schema or not isinstance(user_fields, dict):
        return user_fields

    type_map: dict[str, str] = {}
    for field_def in inputs_schema:
        if isinstance(field_def, dict) and "id" in field_def:
            resolved = _resolve_field_type(field_def)
            if resolved:
                type_map[field_def["id"]] = resolved

    if not type_map:
        return user_fields

    coerced = {}
    for key, value in user_fields.items():
        target_type = type_map.get(key)
        if target_type:
            coerced[key] = _coerce_value(value, target_type, input_mode=True)
        else:
            coerced[key] = value
    return coerced


@dataclass
class FlowCodeConfig:
    """FlowCode 节点配置"""

    code: str = ""
    user_fields: dict = field(default_factory=dict)
    exec_env: str = "local"


class FlowCode(WorkflowComponent):
    """工作流代码节点 - 基于 LocalCodeRunner（subprocess 执行）

    执行用户提供的 Python 代码，代码必须定义 main(args: dict) -> dict 函数。
    返回值自动包装为 {USER_FIELDS: result_dict} 格式。
    """

    def __init__(self, conf: Union[FlowCodeConfig, dict, None] = None):
        super().__init__()
        self._conf: Optional[FlowCodeConfig] = None
        self._code_runner: Optional[CodeRunner] = None
        if conf is not None:
            self._init_conf(conf)

    # ==================== 配置初始化 ====================

    def _init_conf(self, conf: Union[FlowCodeConfig, dict]):
        """初始化配置并校验

        Args:
            conf: 配置对象或字典

        Raises:
            BuildError: 配置无效时抛出异常
        """
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

    def init(self, conf=None, **kwargs):
        """兼容遗留工作流引擎的两阶段初始化"""
        if conf is not None:
            self._init_conf(conf)
        super().init(**kwargs)

    @property
    def config(self) -> FlowCodeConfig:
        """获取节点配置"""
        return self._conf

    @property
    def node_type(self) -> str:
        """获取节点类型标识"""
        return JIUWEN_CODE_TYPE

    def component_type(self) -> str:
        """获取组件类型标识"""
        return JIUWEN_CODE_TYPE

    def _check_blacklist(self, code: str) -> None:
        """黑名单检查

        检查用户代码中是否包含禁止使用的关键字。

        Args:
            code: 用户源代码

        Raises:
            BuildError: 发现黑名单关键字时抛出异常
        """
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

    def _get_local_runner(self) -> "CodeRunner":
        """Helper to create a local runner. Used by fallback logic.

        Returns:
            A new InprocessCodeRunner 或 LocalCodeRunner instance.

        Raises:
            BuildError: If SysOperation not found (subprocess 模式).
        """
        from agent_runtime.common.config import settings
        from agent_runtime.extension.workflow_node.code_runner.runner import (
            CodeRunnerFactory,
        )

        # inprocess 模式不需要 sys_operation
        if settings.code_execution.local_exec_mode == "inprocess":
            from agent_runtime.extension.workflow_node.code_runner.inprocess_code_runner import InprocessCodeRunner
            return InprocessCodeRunner()

        # subprocess 模式需要 sys_operation
        from openjiuwen.core.runner import Runner

        sys_op_id = "flow_code_sys_op"
        sys_op = Runner.resource_mgr.get_sys_operation(sys_op_id)
        if sys_op is None:
            raise build_error(
                StatusCode.WORKFLOW_COMPONENT_EXECUTION_ERROR,
                comp_id="flow_code",
                reason=f"SysOperation '{sys_op_id}' not found. Must be registered at startup.",
                workflow="n/a",
            )

        code_op = sys_op.code()
        local_runner = CodeRunnerFactory.get_runner("local")
        return local_runner.create(code_op)

    def _ensure_code_runner(self):
        """Lazy-load CodeRunner instance using Runner pattern.

        Selects the appropriate CodeRunner based on exec_env configuration and LOCAL_CODE_EXEC_MODE:
        - 'local' + inprocess: InprocessCodeRunner（进程内 exec，不依赖 sys_operation）
        - 'local' + subprocess: LocalCodeRunner（子进程执行，依赖 sys_operation）
        - 'sandbox': SandboxCodeRunner (with fallback to local if not configured)

        Raises:
            BuildError: SysOperation not found or critical failure.
        """
        if self._code_runner is not None:
            return

        from agent_runtime.common.config import settings

        exec_env = self._conf.exec_env or "local"

        # inprocess 模式直接创建，不依赖 sys_operation
        if exec_env == "local" and settings.code_execution.local_exec_mode == "inprocess":
            from agent_runtime.extension.workflow_node.code_runner.inprocess_code_runner import InprocessCodeRunner
            self._code_runner = InprocessCodeRunner()
            return

        # 原有逻辑：subprocess/sandbox 需要依赖 sys_operation
        from openjiuwen.core.runner import Runner
        from agent_runtime.extension.workflow_node.code_runner.runner import (
            CodeRunnerFactory,
        )

        sys_op_id = "flow_code_sys_op"
        sys_op = Runner.resource_mgr.get_sys_operation(sys_op_id)
        if sys_op is None:
            raise build_error(
                StatusCode.WORKFLOW_COMPONENT_EXECUTION_ERROR,
                comp_id="flow_code",
                reason=f"SysOperation '{sys_op_id}' not found. Must be registered at startup.",
                workflow="n/a",
            )

        code_op = sys_op.code()

        try:
            runner_strategy = CodeRunnerFactory.get_runner(exec_env)
            self._code_runner = runner_strategy.create(code_op)
        except Exception as e:
            workflow_logger.debug(
                f"Failed to create runner for '{exec_env}': {e}, fallback to local"
            )
            self._code_runner = self._get_local_runner()

    async def invoke(
        self, inputs: Input, session: Session, context: ModelContext
    ) -> Output:
        """同步调用代码节点

        Args:
            inputs: 输入数据，包含 USER_FIELDS
            session: 会话上下文
            context: 模型上下文

        Returns:
            Output: {USER_FIELDS: result_dict} 格式的输出

        Raises:
            BuildError: 执行失败时抛出异常
        """
        try:
            workflow_logger.debug(
                "FlowCode component invoke started",
                event_type=LogEventType.WORKFLOW_COMPONENT_START,
                component_id=session.get_component_id(),
                component_type_str=JIUWEN_CODE_TYPE,
                session_id=session.get_session_id(),
            )

            # 1. 黑名单检查
            self._check_blacklist(self._conf.code)

            # 2. 懒加载 CodeRunner
            self._ensure_code_runner()

            # 3. 获取用户输入
            user_fields = inputs.get(USER_FIELDS, inputs) if inputs else {}

            # 3.5 根据 input schema 做类型转换（None → 默认值）
            inputs_schema = self._conf.user_fields.get("inputs", [])
            if inputs_schema:
                user_fields = _coerce_inputs(user_fields, inputs_schema)

            # 3.6 结果缓存查询：基于 (code, exec_env, inputs, outputs_schema) hash，
            # 命中则跳过执行（CODE_EXECUTION_RESULT_CACHE_ENABLE 控制，默认开启）
            outputs_schema = self._conf.user_fields.get("outputs", [])
            result_cache = get_code_result_cache()
            cache_key = None
            cached = None
            if result_cache is not None:
                cache_key = make_cache_key(
                    self._conf.code,
                    self._conf.exec_env,
                    user_fields,
                    outputs_schema,
                )
                cached = result_cache.get(cache_key)

            if cached is not None:
                # 缓存命中：结果已含 outputs 类型转换，直接返回
                # （HIT 日志由 CodeResultCache.get 输出，key 前缀一致可关联）
                result_dict, function_log = cached
            else:
                # 4. 执行代码（带 sandbox 失败 fallback 到 local）
                from agent_runtime.common.config import settings

                exec_timeout = settings.security_sandbox.timeout_seconds
                workflow_logger.info(
                    "[FlowCode] exec_timeout=%s (from SECURITY_SANDBOX_TIMEOUT)",
                    exec_timeout,
                )
                active_runner = self._code_runner
                try:
                    result_dict = await self._code_runner.run(
                        user_code=self._conf.code,
                        inputs=user_fields,
                        timeout=exec_timeout,
                    )
                except Exception as e:
                    # Sandbox execution failed, fallback to local
                    exec_env = self._conf.exec_env or "local"
                    if exec_env == "sandbox":
                        if "timeout" in str(e).lower():
                            # 超时不应 fallback 到本地，否则同样的代码会再次超时
                            raise RuntimeError(
                                f"代码执行超时（已超过 {exec_timeout} 秒限制），"
                                f"请优化代码或调整 SECURITY_SANDBOX_TIMEOUT 配置"
                            ) from e
                        workflow_logger.warning(
                            f"Sandbox execution failed: {e}, fallback to local"
                        )
                        active_runner = self._get_local_runner()
                        # 回退执行结果不缓存，避免 sandbox 恢复后命中 local 结果
                        cache_key = None
                        result_dict = await active_runner.run(
                            user_code=self._conf.code,
                            inputs=user_fields,
                            timeout=exec_timeout,
                        )
                    else:
                        raise  # Re-raise for non-sandbox environments

                # 4.5 提取 function_log（用户 print 输出）
                function_log = getattr(active_runner, "function_log", "")

                # 5. 根据 output schema 做类型转换
                if outputs_schema:
                    result_dict = _coerce_outputs(result_dict, outputs_schema)

                # 5.2 写入结果缓存（仅缓存成功结果）
                if result_cache is not None and cache_key is not None:
                    result_cache.put(cache_key, result_dict, function_log)

            # 4.6 将 function_log（用户 print 输出）通过 tracer 发送到 onInvokeData
            if function_log:
                try:
                    await session.trace(data={"function_log": function_log})
                except Exception as e:
                    workflow_logger.warning(f"Fail record function log. {e}")

            workflow_logger.debug(
                "FlowCode component invoke succeeded",
                event_type=LogEventType.WORKFLOW_COMPONENT_END,
                component_id=session.get_component_id(),
                component_type_str=JIUWEN_CODE_TYPE,
                session_id=session.get_session_id(),
            )

            # 5.5 记录代码执行信息到 on_invoke_data
            if hasattr(session, 'trace'):
                await session.trace(data={
                    "code_info": {
                        "inputs": user_fields,
                        "outputs": result_dict,
                    }
                })

            # 6. 包装返回格式
            return {USER_FIELDS: result_dict}

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
        """流式输出（当前实现为单次yield）

        Args:
            inputs: 输入数据
            session: 会话上下文
            context: 模型上下文

        Yields:
            Output: invoke() 的返回值
        """
        result = await self.invoke(inputs, session, context)
        yield result


__all__ = [
    "FlowCode",
    "FlowCodeConfig",
    "JIUWEN_CODE_TYPE",
]
