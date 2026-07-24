#  Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
"""
工作流起始节点模块

该模块提供了工作流起始节点的实现，主要负责处理工作流的输入验证、
默认值填充、全局变量处理、内存变量管理和会话级变量持久化等功能。

主要功能包括:
1. 输入参数验证和默认值填充
2. 会话级变量从 Redis 读取并合并到 memory
3. 内存变量管理和继承
4. 数据类型转换和格式化

类:
    Start: 工作流起始节点类

常量:
    USER_FIELDS: 用户字段标识
    SYSTEM_FIELDS: 系统字段标识
    PRE_DEFINED_FIELDS: 预定义字段标识
    MEMORY: 内存字段标识
    ASSIGNMENT: 赋值操作标识
    ASSIGNMENT_SESSION: 会话级别赋值
    ASSIGNMENT_PERMANENT: 永久级别赋值
    REDIS_GLOBAL_VALS_NAME: Redis全局值存储键名前缀
"""

import json
from copy import deepcopy
from enum import Enum
from typing import Any

from agent_runtime.common.config import settings
from common_utils.redis_manager import get_redis_client
from agent_runtime.common.session_state_access import get_state_info
from jiuwen.extension.workflow_node.utils import get_workflow_param
from jiuwen.orchestration.flow.constant import REQUEST_VARIABLES
from openjiuwen.core.common.logging import workflow_logger
from openjiuwen.core.context_engine.base import ModelContext
from openjiuwen.core.graph.executable import Input, Output
from openjiuwen.core.session.internal.workflow import NodeSession
from openjiuwen.core.session.node import Session
from openjiuwen.core.workflow import WorkflowComponent

USER_FIELDS = "userFields"
SYSTEM_FIELDS = "systemFields"
PRE_DEFINED_FIELDS = "preDefinedFields"
MEMORY = "memory"
ASSIGNMENT = "assignment"
ASSIGNMENT_SESSION = "session"
ASSIGNMENT_PERMANENT = "permanent"

# Redis存储相关常量
REDIS_GLOBAL_VALS_NAME = "global.vals"  # Redis全局值存储键名前缀
# 会话变量过期时间（秒），默认3天，通过 CONVERSATION_VARIABLE_STORE_TIME 环境变量配置
_DEFAULT_CONVERSATION_VARIABLE_TTL = settings.conversation_variable.ttl_seconds


class DataType(Enum):
    """支持的数据类型枚举"""

    INTEGER = "integer"
    BOOLEAN = "boolean"
    NUMBER = "number"
    STRING = "string"
    OBJECT = "object"
    ARRAY = "array"


DATA_TYPE_CONVERSION = {
    DataType.INTEGER.value: int,
    DataType.BOOLEAN.value: bool,
    DataType.NUMBER.value: (float, int, complex),
    DataType.STRING.value: str,
    DataType.OBJECT.value: dict,
    DataType.ARRAY.value: list,
}


class Start(WorkflowComponent):
    """
    工作流开始节点组件

    职责:
    1. 验证必需的输入变量
    2. 填充默认值
    3. 初始化工作流上下文
    4. 会话级变量从 Redis 读取并合并到 memory
    """

    def __init__(self, conf: dict):
        super().__init__()
        self._config = conf or {}
        self._node_name: str = self._config.get("name") or None

    async def invoke(
        self, inputs: Input, session: Session, context: ModelContext
    ) -> Output:
        """
        执行开始节点逻辑

        Args:
            inputs: 用户输入数据
            session: 工作流会话
            context: 模型上下文

        Returns:
            包含系统字段、用户字段和 memory 的输出字典
        """
        # 0. 获取 workflow_id 和 conversation_id
        workflow_id = self._get_workflow_id(inputs, session)
        conversation_id = self._get_conversation_id(inputs, session)

        # 1. 验证必需变量
        self._validate_inputs(inputs)

        # 2. 填充默认值
        inputs_with_defaults = self._fill_default_values(inputs)

        # 3. 获取 preDefinedFields 中定义的会话级变量
        assignment_inputs = self._get_assignment_inputs()
        session_var_defs = self._extract_assignment_values(
            assignment_inputs, ASSIGNMENT_SESSION
        )

        # 4. 将会话级变量定义写入 global_state，供 SetVariable 节点使用
        if session_var_defs:
            inner_session = getattr(session, "_inner", None)
            node_id = getattr(inner_session.state(), "_node_id", None).split(".")[-1]
            node_session = NodeSession(inner_session.parent(), node_id)
            session_vars_config = {"_session_var_defs": session_var_defs}
            node_session.state().update_global(session_vars_config)

        # 5. 从 Redis 读取会话级变量值
        redis_session_vars = await self._get_redis_session_vars(
            workflow_id, conversation_id, session_var_defs
        )

        # 6. 构建 memory
        user_input_memory = self._user_input_memory_var(inputs)
        default_memory = dict(session_var_defs)
        memory = default_memory | redis_session_vars | user_input_memory

        # 7. 将 memory 写入 session 的 io_state，供后续节点通过 generate_value 读取
        inner_session = getattr(session, "_inner", None)
        node_id = getattr(inner_session.state(), "_node_id", None).split(".")[-1]
        node_session = NodeSession(inner_session.parent(), node_id)
        # 写入 io_state，memory 在 userFields 下面（路径格式: node_start.userFields.memory.var）
        node_session.state().set_outputs(
            {"userFields": {**inputs_with_defaults, "memory": memory}}
        )
        # 将 memory 变量写入 global_state，使 ${MEMORY_VARIABLE.xxx} 引用可解析
        # 只写入 preDefinedFields 中定义的记忆变量，排除输入参数
        if memory:
            memory_var_keys = self._get_predefined_var_keys()
            memory_global = {
                f"MEMORY_VARIABLE.{k}": v
                for k, v in memory.items()
                if k in memory_var_keys
            }
            if memory_global:
                node_session.state().update_global(memory_global)
        node_session.state().commit()

        # 8. 组装输出
        start_result = self._assemble_output(inputs_with_defaults, session)
        start_result["memory"] = memory

        # 9. 将 userFields 写入 global_state，供下游交互组件（如 Questioner）中断时读取
        # 匹配旧框架 final_output 累积行为：旧框架中 Start 写入 final_output 后，
        # Questioner 中断不会覆盖，FINISH 保留了 Start 的 userFields
        user_fields = self._config.get(USER_FIELDS, {}).get("outputs", {})
        start_user_fields = {}
        if user_fields:
            for field in user_fields:
                start_user_fields[field.get("id", "")] = field.get("default_value", "")
            session.update_global_state({"start_user_fields": start_user_fields})

        # 10. user_input_memory有值，更新redis
        if user_input_memory:
            await self._save_redis_session_vars(
                workflow_id, conversation_id, session_var_defs, user_input_memory
            )

        return start_result

    def _get_assignment_inputs(self) -> dict:
        """
        获取节点赋值的 inputs 配置数据

        从工作流节点配置中提取 preDefinedFields.inputs 配置信息。

        Returns:
            dict: 赋值输入配置字典，如果没有配置则返回空列表
        """
        if self._config is None:
            return {}
        if PRE_DEFINED_FIELDS not in self._config:
            return {}
        if "inputs" not in self._config[PRE_DEFINED_FIELDS]:
            return {}
        return self._config[PRE_DEFINED_FIELDS]["inputs"]

    def _get_predefined_var_keys(self) -> set[str]:
        """
        从 preDefinedFields.inputs 中提取所有顶层记忆变量名

        遍历 preDefinedFields.inputs，对于 id 为 "memory" 的对象类型，
        提取其 schema 中每个字段的顶层 id（不递归展开 object 子字段）。

        Returns:
            set[str]: 记忆变量名集合
        """
        keys = set()
        assignment_inputs = self._get_assignment_inputs()
        for item in assignment_inputs:
            if isinstance(item, dict) and item.get("id") == MEMORY:
                for field in item.get("schema", []):
                    if isinstance(field, dict) and "id" in field:
                        keys.add(field["id"])
        return keys

    @staticmethod
    def _extract_assignment_values(data, time_type: str) -> dict:
        """
        提取特定时间类型的赋值值数据定义

        从配置数据中提取指定时间类型（会话级或永久级）的变量定义，
        包括 id 和 default_value。

        Args:
            data: 配置数据，可以是列表、字典或其他类型
            time_type (str): 时间类型，必须是 ASSIGNMENT_SESSION 或 ASSIGNMENT_PERMANENT

        Returns:
            dict: 提取后的变量定义字典，格式为 {var_id: default_value}
        """
        result = {}
        if isinstance(data, list):
            for item in data:
                result.update(Start._extract_assignment_values(item, time_type))
        elif isinstance(data, dict):
            aging_level = data.get("aging_level")
            # 兼容：permanent 视同 session 处理
            if aging_level == ASSIGNMENT_PERMANENT:
                aging_level = ASSIGNMENT_SESSION
            if (
                data.get("storage_method") == ASSIGNMENT
                and aging_level == time_type
            ):
                if "schema" not in data:
                    # 基本类型处理，需要根据 type 进行类型转换
                    if "default_value" in data and "type" in data:
                        var_id = data.get("id", "")
                        default_val = data.get("default_value", "")
                        if var_id:
                            # 根据 type 进行类型转换
                            result[var_id] = Start._transform_type(
                                data["type"].lower(), default_val, var_id
                            )
                else:
                    # 对象或数组类型处理，递归提取内层定义
                    result.update(
                        Start._extract_assignment_values(
                            data.get("schema", []), time_type
                        )
                    )
            # 递归处理 schema
            if "schema" in data and not data.get("storage_method") == ASSIGNMENT:
                result.update(
                    Start._extract_assignment_values(data["schema"], time_type)
                )
        return result

    @staticmethod
    def _transform_type(data_type: str, data_value: Any, data_id: str = "") -> Any:
        """
        数据类型转换方法

        根据指定类型将输入值转换为对应类型。

        Args:
            data_type: 目标数据类型字符串
            data_value: 需要转换的输入值
            data_id: 数据项ID，用于错误信息

        Returns:
            转换后的数据值，转换失败时返回原值
        """
        res = data_value
        if data_type != "string" and (data_value == "" or data_value is None):
            return None
        try:
            conversion_func = DATA_TYPE_CONVERSION.get(data_type)
            if conversion_func:
                return conversion_func(data_value)
        except Exception as e:
            workflow_logger.error(
                f"Failed to transform start node vars type: {e}", exc_info=True
            )
        return res

    @staticmethod
    async def _get_redis_session_vars(
        workflow_id: str, conversation_id: str, values_define: dict
    ) -> dict:
        """
        从 Redis 读取会话级变量值

        Args:
            workflow_id: 工作流 ID
            conversation_id: 会话 ID
            values_define: 变量定义字典，格式为 {var_id: default_value}

        Returns:
            dict: 从 Redis 读取的会话级变量值（仅包含 values_define 中定义的变量）
        """
        try:
            if not (workflow_id and conversation_id and values_define):
                return {}
            redis_client = get_redis_client()
            store_key = f"{REDIS_GLOBAL_VALS_NAME}.{workflow_id}.{conversation_id}"
            memory_values = await redis_client.get(store_key)
            if memory_values:
                # 处理 Redis 返回的 bytes 或 str 类型
                if isinstance(memory_values, bytes):
                    memory_values = memory_values.decode("utf-8")
                if isinstance(memory_values, str):
                    stored_data = json.loads(memory_values)
                    if isinstance(stored_data, dict):
                        # 只返回 values_define 中定义的变量，且使用 Redis 中的值
                        return {
                            k: stored_data.get(k, v) for k, v in values_define.items()
                        }
            return {}
        except Exception as e:
            workflow_logger.error(
                f"Failed to get session vars from redis: {e}", exc_info=True
            )
            return {}

    async def _save_redis_session_vars(
        self,
        workflow_id: str,
        conversation_id: str,
        values_define: dict,
        memory_vars: dict,
    ):
        """
        从 Redis 存入会话级变量值

        Args:
            workflow_id: 工作流 ID
            conversation_id: 会话 ID
            values_define: 变量定义字典，格式为 {var_id: default_value}
            memory_vars: 待存入的变量

        Returns:
            dict: 从 Redis 读取的会话级变量值（仅包含 values_define 中定义的变量）
        """
        try:
            if not (workflow_id and conversation_id and values_define):
                return None
            redis_client = get_redis_client()
            store_key = f"{REDIS_GLOBAL_VALS_NAME}.{workflow_id}.{conversation_id}"
            # 只存values_define中的变量和memory_vars中的值
            new_memory_vars = {
                k: memory_vars[k] for k in values_define if k in memory_vars
            }

            old_values = await self._get_redis_session_vars(
                workflow_id, conversation_id, values_define
            )
            if old_values:
                # 合并数据
                new_memory_vars = {**old_values, **new_memory_vars}
            await redis_client.set(
                store_key, json.dumps(new_memory_vars, ensure_ascii=False),
                ex=_DEFAULT_CONVERSATION_VARIABLE_TTL,
            )
        except Exception as e:
            workflow_logger.error(
                f"Failed to save memory vars to redis: {e}", exc_info=True
            )
            return {}

    def _user_input_memory_var(self, inputs: dict) -> dict:
        """
        提取用户输入中的内存变量

        从用户输入中提取当前应该存入内存的变量，
        排除已知的系统字段和不需要内存化的字段。

        Args:
            inputs: 用户输入字典

        Returns:
            dict: 内存变量字典，键为变量名，值为变量值
        """
        # 排除不需要存储为内存变量的字段
        not_vars = ["query", "sys", "conversationId", "userId", "conversationHistory"]
        global_vars = inputs.get("global_variables") or {}
        memory_variables = {}
        for key, value in global_vars.items():
            if key not in not_vars:
                memory_variables[key] = value
        return memory_variables

    def _get_workflow_id(self, inputs: Input, session: Session) -> str:
        """获取 workflow_id"""
        # 优先从 global_state 获取
        workflow_id = get_workflow_param(session, "workflow_id")
        if workflow_id:
            return workflow_id
        # 从 session.get_workflow_id() 获取
        if hasattr(session, "get_workflow_id"):
            workflow_id = session.get_workflow_id()
            if workflow_id:
                return workflow_id
        # 从 inputs 的 global_variables 中获取
        global_variables = (
            inputs.get("global_variables", {}) if isinstance(inputs, dict) else {}
        )
        if isinstance(global_variables, dict):
            app_id = global_variables.get("appId")
            if app_id:
                return app_id
        return ""

    def _get_conversation_id(self, inputs: Input, session: Session) -> str:
        """获取 conversation_id"""
        # 优先从 global_state 获取
        conversation_id = get_workflow_param(session, "conversation_id")
        if conversation_id:
            return conversation_id
        # 从 session.get_session_id() 获取
        if hasattr(session, "get_session_id"):
            conversation_id = session.get_session_id()
            if conversation_id:
                return conversation_id
        # 从 inputs 的 global_variables 中获取
        global_variables = (
            inputs.get("global_variables", {}) if isinstance(inputs, dict) else {}
        )
        if isinstance(global_variables, dict):
            conv_id = global_variables.get("conversationId")
            if conv_id:
                return conv_id
        return ""

    def _validate_inputs(self, inputs: dict) -> None:
        """验证必需的输入变量"""
        user_defined_variables = self._config.get(USER_FIELDS, {}).get("inputs", [])
        variables_not_given = []
        for variable in [
            var for var in user_defined_variables if var.get("required", False)
        ]:
            variable_name = variable.get("id", "")
            if variable_name not in inputs:
                variables_not_given.append(variable_name)

        if variables_not_given:
            raise ValueError(f"Missing required variables: {variables_not_given}")

    def _fill_default_values(self, inputs: dict) -> dict:
        """填充默认值"""
        user_defined_variables = self._config.get(USER_FIELDS, {}).get("inputs", [])
        default_maps = {
            var["id"]: var["default_value"]
            for var in user_defined_variables
            if "id" in var
            and var.get("default_value") is not None
            and var.get("default_value") != ""
        }
        if not inputs:
            return default_maps
        return default_maps | inputs

    @staticmethod
    def _assemble_output(inputs: dict, session: Session) -> dict:
        """组装输出，分离系统字段和用户字段"""
        io_state = get_state_info(session, "io_state") or {}
        envs = get_workflow_param(session, REQUEST_VARIABLES) or {}
        inputs_copy = deepcopy(inputs)
        inputs_copy.pop("sys", None)
        # _REQUEST 补充 inputs 中缺失或值为 null 的字段（openjiuwen schema 解析会给未赋值的
        # 用户字段填充 null，需要用 _REQUEST 中的实际值覆盖）；
        # 不覆盖已有非空值（避免并行相同子工作流共享 global_state[_REQUEST] 时数据污染）；
        # 布尔类型字段特殊处理：False 是有效值不应被覆盖
        for key, value in envs.items():
            if key not in inputs_copy or inputs_copy[key] is None:
                inputs_copy[key] = value
        # 当前用户输入加入历史
        # deepcopy sys 以避免直接 mutate session 内部状态：get_state_info 返回的是
        # 底层 dict 的直接引用，否则 conversationHistory 的 append 会污染同轮/跨轮的
        # session 内部历史（回归 bug）
        sys = deepcopy(io_state.get("global_variables", {}).get("sys", {}))
        sys.get("conversationHistory", []).append(
            {"role": "user", "content": inputs_copy.get("query", "")}
        )
        # 优先使用 inputs_copy（当前轮次的新输入），fallback 到 io_state（checkpoint 恢复的旧值）
        # 修复：恢复场景下 io_state.get("query") 保留的是首轮旧值，会覆盖当前轮次的新 query
        resolved_query = inputs_copy.get("query", "") or io_state.get("query", "")
        return {
            SYSTEM_FIELDS: {
                "query": resolved_query,
                "dialogueHistory": io_state.get("dialogueHistory", []),
                "sys": sys,
                "conversationHistory": sys.get("conversationHistory", []),
            },
            USER_FIELDS: inputs_copy,
        }
