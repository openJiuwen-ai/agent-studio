#  Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
"""
utils
"""

import datetime
import json
import os
from typing import Any, Union, Dict, List

from jiuwen.common.configs.env_constants import INSIGHT_SUPPORT_ENCRYPT_KEY
from jiuwen.common.log.base import logger
from jiuwen.common.security.cryptor import Crypt as OriCrypt
from jiuwen.insight.handlers.data import InvokeData

# 盘古公测将insight结果放到内存中存储，现有方式为直接存储在client中
# 通过下方的环境变量作为开关控制
# 同时，当前开关打开时，也会保存extra字段中的内容做后续统计使用
ENVIRONMENT_INSIGHT_MEMORY = "ENVIRONMENT_INSIGHT_MEMORY"

# EI场景下agent调试信息发送
INSIGHT_EI_DEBUG_INFO_ENABLE = "INSIGHT_EI_DEBUG_INFO_ENABLE"


def format_invoke_data(invoke: InvokeData) -> Dict:
    """
    Format invoke data into a dict for insight sending.
    Uses model_dump when available (Pydantic v2), else dict(); only reads from invoke.
    """
    dump_fn = getattr(invoke, "model_dump", None) or getattr(invoke, "dict")
    try:
        invoke_dict = dump_fn(mode="json", exclude={"child_invokes"})
    except Exception:
        invoke_dict = dump_fn(mode="json", exclude={"child_invokes", "serialized"})

    if invoke.end_time is not None:
        invoke_dict["elapsed_time"] = get_elapsed_time(invoke)
    invoke_dict["child_invokes"] = [c.invoke_id for c in invoke.child_invokes]

    inp = invoke_dict.get("inputs")
    invoke_dict["inputs"] = inp.get("input") if inp else None

    out = invoke_dict.get("outputs")
    invoke_dict["outputs"] = out.get("output") if out else None

    err = invoke_dict.get("error")
    invoke_dict["error"] = err.get("error") if err else None

    invoke_dict["invoke_type"] = invoke.invoke_type.value
    invoke_dict["meta_data"] = (
        invoke_dict.pop("serialized") if "serialized" in invoke_dict else {}
    )

    if not os.environ.get(ENVIRONMENT_INSIGHT_MEMORY):
        invoke_dict.pop("extra")
    return invoke_dict


def serialize_json(obj: Any) -> Union[str, dict]:
    """
    serialize json
    """
    if isinstance(obj, datetime.datetime):
        return obj.strftime("%Y-%m-%d %H:%M:%S.%f")

    if hasattr(obj, "mode_dump_json") and callable(obj.mode_dump_json):
        # for pydantic BaseModel, version2
        try:
            return json.loads(obj.mode_dump_json(exculde_none=True))
        except Exception:
            logger.warning("Serialize failed with error.")
            return repr(obj)

    if hasattr(obj, "json") and callable(obj.json):
        # for pydantic BaseModel, version1
        try:
            return json.loads(obj.json(exculde_none=True))
        except Exception:
            logger.warning("Serialize failed with error.")
            return repr(obj)

    return repr(obj)


def get_instance_info(instance: object, blacklist: List[str] = None) -> dict:
    """Get instance info while filtering attributes appearing in the blacklist"""
    class_name = instance.__class__.__name__
    instance_attributes = {}

    if blacklist is None:
        blacklist = []

    for attribute_name in instance.__dict__:
        if attribute_name not in blacklist:
            attribute_value = instance.__dict__[attribute_name]
            instance_attributes[attribute_name] = attribute_value

    return {"class_name": class_name, "instance_attributes": instance_attributes}


def get_agent_identity(agent: Any) -> Union[Dict[str, str], None]:
    """Extract the executing agent's flat identity for openjiuwen telemetry spans.

    id 优先取 AgentMetaData.id（IR 的原始 agentId）：与同 trace 内 core 侧
    LLM 标识 / 工作流组件 span / context_manager 的取值一致，可按 agent
    关联；AgentConfig.agent_id 是 "<agentId>_<agentVersion>" 复合值，仅作
    缺省回退。Name / description come from AgentMetaData (e.g. the studio
    app's real display name like "天气预测"), falling back to the agent id.
    Returns None when the agent carries no id so callers skip identity
    injection entirely.
    """
    metadata = getattr(getattr(agent, "agent_config", None), "metadata", None)
    agent_id = getattr(metadata, "id", None) or getattr(agent, "agent_id", None)
    if not agent_id:
        return None
    return {
        "agent_id": str(agent_id),
        "agent_name": str(getattr(metadata, "name", None) or agent_id),
        "agent_description": str(getattr(metadata, "description", None) or ""),
    }


def get_conversation_facts(session: Any) -> Union[Dict[str, str], None]:
    """Extract flat conversation facts (conversation_id / user_id) from a session.

    openjiuwen core 的 OtelRail 以 session 为会话事实源（conversation_id =
    session_id，user_id 走 session 携带的 source_metadata），双写桥按同一
    取值口径供给，两种模式的 gen_ai.conversation.id / user.id 才可对齐。
    Returns None when the session carries no facts so callers skip injection.
    """
    if session is None:
        return None
    facts: Dict[str, str] = {}
    get_session_id = getattr(session, "get_session_id", None)
    session_id = get_session_id() if callable(get_session_id) else None
    if session_id:
        facts["conversation_id"] = str(session_id)
    # core Session 的公开访问器优先（get_source_metadata 返回副本），
    # 旧版底层无访问器时退回 _source_metadata 私有名——与 core
    # react_agent 取 source_metadata 的探测口径一致，私有名仅作兜底
    source_metadata_getter = getattr(session, "get_source_metadata", None)
    source_metadata = (
        source_metadata_getter()
        if callable(source_metadata_getter)
        else getattr(session, "_source_metadata", None)
    )
    user_id = source_metadata.get("user_id", "") if isinstance(source_metadata, dict) else ""
    if user_id:
        facts["user_id"] = str(user_id)
    return facts or None


def extract_tool_trace_info(kwargs: Dict[str, Any]) -> Dict[str, str]:
    """Pop flat tool-trace keys (tool_call_id / tool_type) out of invoke kwargs.

    插件调用方（task_executor handlers）把 planner tool_call 的标识放进
    ainvoke kwargs 透传进来；本助手将其从 kwargs 中摘出（调用方的 kwargs
    不再残留，避免泄入工具运行时入参），返回可直接并入 instance_info 的
    扁平键——core handler 的 on_plugin_start 按这两个键盖
    gen_ai.tool.call.id / gen_ai.tool.type。空值不产出。
    """
    trace_info: Dict[str, str] = {}
    for key in ("tool_call_id", "tool_type"):
        value = kwargs.pop(key, None)
        if value:
            trace_info[key] = str(value)
    return trace_info


def get_elapsed_time(invoke: Any) -> str:
    """get elapsed time"""
    elapsed_time = invoke.end_time - invoke.start_time
    ms = elapsed_time.total_seconds() * 1000
    if ms < 1000:
        return f"{ms:.0f}ms"
    return f"{(ms / 1000):.2f}s"


def insight_unencrypted_mode() -> bool:
    """insight unsecure mode"""
    return str(os.environ.get(INSIGHT_SUPPORT_ENCRYPT_KEY)).lower() == "false"


class Crypt:
    """
    Crypt switch class
    """

    @staticmethod
    def decrypt(ori: str):
        """decrypt"""
        if insight_unencrypted_mode():
            return ori
        return OriCrypt().decrypt(ori)

    @staticmethod
    def encrypt(ori: str):
        """encrypt"""
        if insight_unencrypted_mode():
            return ori
        return OriCrypt().encrypt(ori)
