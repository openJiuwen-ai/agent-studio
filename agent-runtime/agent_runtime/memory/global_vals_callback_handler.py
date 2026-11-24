#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
import json
import os
from abc import ABC
from typing import Any, Union

from jiuwen.common.exception import JiuWenException
from jiuwen.common.store.redis import get_redis_instance, RedisUtils
from jiuwen.orchestration.callbacks.base import BaseCallbackHandler
from jiuwen.orchestration.flow.bpmn_workflow import convert_to_old_type
from jiuwen.orchestration.flow.constant import (
    CONSTANT_NODE_VARIABLE,
    WORKFLOW_EXECUTE_CONVERSATION_ID,
    WORKFLOW_EXECUTE_USER_ID,
)
from jiuwen.orchestration.flow.enum import NodeType
from jiuwen.orchestration.utils import Output
from utils.constants import (
    DEFAULT_PERMANENT_STORE_TIME,
    DEFAULT_CONVERSATION_STORE_TIME,
    REDIS_GLOBAL_VALS_NAME,
)

redis_client: RedisUtils = (
    get_redis_instance()
    if os.environ.get("EXECUTION_STATE_STORAGE_MEDIUM", "dict") == "redis"
    else None
)


def _store_vals(
    workflow_id: str, obj_id: str, memory_dict: dict, vals: dict, ttl: int
) -> None:
    store_key = f"{REDIS_GLOBAL_VALS_NAME}.{workflow_id}.{obj_id}"
    new_vals = {x: memory_dict.get(x) for x in vals.keys()}
    if new_vals:
        redis_client.set(store_key, json.dumps(new_vals), ttl)


def _save_global_vals(**kwargs) -> None:
    workflow_id = (
        kwargs.get("runtime_context", {})
        .get("workflow_execute_debug_info", {})
        .get("workflow_id")
    )
    user_id = (
        kwargs.get("runtime_context", {})
        .get("workflow_execute_debug_info", {})
        .get(WORKFLOW_EXECUTE_USER_ID)
    )
    conversation_id = (
        kwargs.get("runtime_context", {})
        .get("workflow_execute_debug_info", {})
        .get(WORKFLOW_EXECUTE_CONVERSATION_ID)
    )
    if not (workflow_id and user_id and conversation_id and redis_client):
        return
    new_node_variable = kwargs.get("runtime_context", {}).get(CONSTANT_NODE_VARIABLE)
    memory_dict = new_node_variable.get("node_start", {}).get("memory", {})
    permanent_vars_dict = new_node_variable.get("node_start", {}).get(
        "permanent_vars", {}
    )
    session_vars = new_node_variable.get("node_start", {}).get("session_vars", {})
    _store_vals(
        workflow_id,
        user_id,
        memory_dict,
        permanent_vars_dict,
        int(os.getenv("PERMANENT_VARIABLE_STORE_TIME", DEFAULT_PERMANENT_STORE_TIME)),
    )
    _store_vals(
        workflow_id,
        conversation_id,
        memory_dict,
        session_vars,
        int(
            os.getenv(
                "CONVERSATION_VARIABLE_STORE_TIME", DEFAULT_CONVERSATION_STORE_TIME
            )
        ),
    )


class GlobalVals4CallbackHandler(BaseCallbackHandler, ABC):
    async def on_post_invoke(self, outputs: Output, *args: Any, **kwargs: Any) -> Any:
        if convert_to_old_type.get(NodeType.END.value) == kwargs.get(
            "component_metadata", {}
        ).get("component_type"):
            # 执行到结束节点，保存当前全局变量
            _save_global_vals(**kwargs)

    async def on_invoke(
        self, data: Union[JiuWenException, dict], *args: Any, **kwargs: Any
    ) -> Any:
        if isinstance(data, JiuWenException):
            # 执行报错时，保存当前全局变量
            _save_global_vals(**kwargs)
