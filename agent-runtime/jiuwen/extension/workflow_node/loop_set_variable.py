#  !/usr/bin/env python
#  -*- coding: UTF-8 -*-
#  Copyright c) Huawei Technologies Co. Ltd. 2025-2025

"""
增强版 LoopSetVariable 组件

在 openjiuwen 原生 LoopSetVariableComponent 的基础上，增加了对会话级变量持久化的支持。

会话级变量持久化流程：
1. Start 节点从 Redis 读取会话级变量值，与 memory 合并后输出
2. SetVariable 修改变量时，如果变量在 global_state[_request] 中定义（由 Start 写入），
   则同步写入 Redis（key: global.vals.{workflow_id}.{conversation_id}）
3. 下次工作流执行时，Start 节点从 Redis 读取上次的变量值

写入路径对照：
  旧框架 SetVariable: _request.xxx → REQUEST_VARIABLES（runtime_context 中的全局 dict）
  新框架 SetVariable: xxx → io_state + Redis（仅会话级变量）
"""

import json

from agent_runtime.common.config import settings
from agent_runtime.common.redis_manager import get_redis_client
from jiuwen.extension.workflow_node.utils import get_workflow_param
from openjiuwen.core.common.exception.codes import StatusCode
from openjiuwen.core.common.exception.errors import build_error
from openjiuwen.core.common.logging import workflow_logger
from openjiuwen.core.context_engine.base import ModelContext
from openjiuwen.core.graph.executable import Input, Output
from openjiuwen.core.session import extract_origin_key, NESTED_PATH_SPLIT
from openjiuwen.core.session.internal.workflow import NodeSession
from openjiuwen.core.session.node import Session
from openjiuwen.core.workflow.components.flow.loop.loop_comp import (
    LoopSetVariableComponent,
)
from openjiuwen.core.session.utils import is_ref_path

# Redis存储相关常量
REDIS_GLOBAL_VALS_NAME = "global.vals"  # Redis全局值存储键名前缀
# 会话变量过期时间（秒），默认3天，通过 CONVERSATION_VARIABLE_STORE_TIME 环境变量配置
_DEFAULT_CONVERSATION_VARIABLE_TTL = settings.conversation_variable.ttl_seconds
# ${MEMORY_VARIABLE.xxx} 引用前缀
GLOBAL_REF_PREFIX = "MEMORY_VARIABLE."
# 会话变量的 io_state 路径前缀
MEMORY_VAR_PATH_PREFIX = "node_start.userFields.memory"


class LoopSetVariable(LoopSetVariableComponent):
    """增强版 LoopSetVariable 组件，支持自增/自减操作和会话级变量持久化。

    会话级变量判断逻辑：
    - Start 节点在 preDefinedFields 中定义了会话级变量后，会将其变量名写入
      global_state[REQUEST_VARIABLES]（即 global_state["_request"]）
    - SetVariable 修改变量时，检查变量路径是否在 global_state["_request"] 中定义
    - 如果是会话级变量，则写入 Redis 持久化
    """

    # 会话级变量路径中的标识
    MEMORY_VAR_INDICATOR = "memory"

    def __init__(self, variable_mapping: dict, operator_mapping: dict | None = None):
        """
        Args:
            variable_mapping: 变量映射 {"${node.key}": value}
            operator_mapping: 操作类型映射 {"${node.key}": "increment"|"decrement"|"empty"|..."}
        """
        super().__init__(variable_mapping)
        self._operator_mapping = operator_mapping or {}

    async def invoke(
        self, inputs: Input, session: Session, context: ModelContext
    ) -> Output:
        root_session = getattr(session, "_inner").parent()

        # 获取会话级变量定义（由 Start 节点写入）
        session_var_defs = get_workflow_param(session, "_session_var_defs", {})

        for left, right in self._variable_mapping.items():
            left_ref_str = extract_origin_key(left)
            # 获取原始值
            value = LoopSetVariableComponent.generate_value(session, right)

            # Handle ${global.xxx} references: write directly to global_state
            if is_ref_path(left) and left_ref_str.startswith(GLOBAL_REF_PREFIX):
                # Handle increment/decrement for global vars
                operator = self._operator_mapping.get(left, "")
                if operator == "increment":
                    current = session.get_global_state(left_ref_str) or 0
                    if isinstance(current, str):
                        current = int(current)
                    value = current + 1
                elif operator == "decrement":
                    current = session.get_global_state(left_ref_str) or 0
                    if isinstance(current, str):
                        current = int(current)
                    value = current - 1
                elif operator == "empty":
                    value = None
                elif operator == "empty_str":
                    value = ""
                elif operator == "empty_arr":
                    value = []
                # Use left_ref_str (e.g. "global.is_valid") as key so update_dict
                # stores at state["global"]["is_valid"] matching get_global path
                root_session.state().update_global({left_ref_str: value})

                # MEMORY_VARIABLE refs that correspond to session vars need Redis persistence
                var_name = left_ref_str[len(GLOBAL_REF_PREFIX):]
                if session_var_defs and var_name in session_var_defs:
                    await self._save_to_redis(session, f"{MEMORY_VAR_PATH_PREFIX}.{var_name}", {var_name: value})

                continue
            keys = left_ref_str.split(NESTED_PATH_SPLIT)

            if len(keys) == 0:
                raise build_error(
                    StatusCode.COMPONENT_LOOP_SET_VAR_EXECUTION_ERROR,
                    comp=session.get_component_descrip(),
                    reason=f"key[{left}] not supported format",
                )

            # 获取原始值
            value = LoopSetVariableComponent.generate_value(session, right)

            # 处理自增/自减操作
            operator = self._operator_mapping.get(left, "")
            if operator == "increment":
                current_value = (
                    LoopSetVariableComponent.generate_value(session, left) or 0
                )
                # 类型转换：支持字符串数字转换为 int
                if isinstance(current_value, str):
                    current_value = int(current_value)
                value = current_value + 1
            elif operator == "decrement":
                current_value = (
                    LoopSetVariableComponent.generate_value(session, left) or 0
                )
                # 类型转换：支持字符串数字转换为 int
                if isinstance(current_value, str):
                    current_value = int(current_value)
                value = current_value - 1
            elif operator == "empty":
                value = None
            elif operator == "empty_str":
                value = ""
            elif operator == "empty_arr":
                value = []

            output_data = LoopSetVariableComponent.generate_output(keys[1:], value)

            node_id = keys[0]
            node_session = NodeSession(root_session, node_id)
            node_session.state().set_outputs(output_data)

            # 检查是否是会话级变量
            # 变量路径格式: node_start.userFields.memory.var
            # keys 格式: ["node_start", "userFields", "memory", "var"]
            # memory 在 keys[2] 位置，var_name 在 keys[3] 位置
            if self._is_session_var(left_ref_str, session_var_defs, keys):
                # 写入 Redis 持久化
                await self._save_to_redis(session, left_ref_str, output_data)
        return None

    def _is_session_var(
        self, left_ref_str: str, session_var_defs: dict, keys: list
    ) -> bool:
        """
        判断变量是否是会话级变量

        Args:
            left_ref_str: 变量引用字符串，如 "node_start.userFields.memory.var"
            session_var_defs: 会话级变量定义字典
            keys: 变量引用切分后的键列表

        Returns:
            bool: 是否是会话级变量
        """
        if not session_var_defs or not isinstance(session_var_defs, dict):
            return False

        # 变量路径格式: node_start.userFields.memory.var
        # keys 格式: ["node_start", "userFields", "memory", "var"]
        # memory 在 keys[2] 位置，var_name 在 keys[3] 位置
        if len(keys) >= 4 and keys[2] == self.MEMORY_VAR_INDICATOR:
            var_name = keys[-1]
            return var_name in session_var_defs

        return False

    async def _save_to_redis(
        self, session: Session, left_ref_str: str, output_data: dict
    ):
        """将会话级变量写入 Redis 持久化

        Args:
            session: 工作流会话
            left_ref_str: 变量引用字符串，如 "node_start.userFields.memory.var"
            output_data: 要写入的变量数据
        """
        try:
            # 使用 session 的方法获取 workflow_id 和 conversation_id
            workflow_id = ""
            conversation_id = ""
            if hasattr(session, "get_workflow_id"):
                workflow_id = session.get_workflow_id() or ""
            if hasattr(session, "get_session_id"):
                conversation_id = session.get_session_id() or ""
            if not (workflow_id and conversation_id):
                return

            redis_client = get_redis_client()
            store_key = f"{REDIS_GLOBAL_VALS_NAME}.{workflow_id}.{conversation_id}"

            # 提取变量名（从 "node_start.userFields.memory.var" 中提取 "var"）
            var_name = self._extract_var_name(left_ref_str)
            if not var_name:
                return

            # 构造写入数据：{var_name: value}
            # output_data 格式: {'userFields': {'memory': {'var': 1}}}
            var_value = None
            if isinstance(output_data, dict):
                user_fields = output_data.get("userFields", {})
                if isinstance(user_fields, dict):
                    memory = user_fields.get("memory", {})
                    if isinstance(memory, dict):
                        var_value = memory.get(var_name)
            if var_value is None:
                var_value = output_data.get(var_name, output_data)
            save_data = {var_name: var_value}

            # 读取 Redis 中现有的值
            existing_data = await redis_client.get(store_key)
            if existing_data:
                try:
                    # 处理 Redis 返回的 bytes 或 str 类型
                    if isinstance(existing_data, bytes):
                        existing_data = existing_data.decode("utf-8")
                    merged_data = json.loads(existing_data)
                    if isinstance(merged_data, dict):
                        merged_data.update(save_data)
                    else:
                        merged_data = save_data
                except (json.JSONDecodeError, TypeError):
                    merged_data = save_data
            else:
                merged_data = save_data

            # 写入 Redis
            await redis_client.set(
                store_key, json.dumps(merged_data, ensure_ascii=False),
                ex=_DEFAULT_CONVERSATION_VARIABLE_TTL,
            )
        except Exception as e:
            workflow_logger.error(
                f"Failed to save memory vars to redis: {e}", exc_info=True
            )

    def _extract_var_name(self, left_ref_str: str) -> str:
        """
        从变量引用字符串中提取变量名

        Args:
            left_ref_str: 变量引用字符串，如 "node_start.userFields.memory.var"

        Returns:
            str: 变量名，如 "var"
        """
        keys = left_ref_str.split(NESTED_PATH_SPLIT)
        # 变量路径格式: node_start.userFields.memory.var
        # keys 格式: ["node_start", "userFields", "memory", "var"]
        if len(keys) >= 4 and keys[2] == self.MEMORY_VAR_INDICATOR:
            return keys[-1]
        return ""
