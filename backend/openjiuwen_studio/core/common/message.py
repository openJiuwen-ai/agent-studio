from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from openjiuwen_studio.core.common.dsl import BaseInfo


class ExecuteResponseType(str, Enum):
    Trace = "trace"  # 节点trace消息
    Node = "node"  # 节点内主动流式输出
    Workflow = "workflow"  # 工作流消息
    Agent = "agent"  # Agent 消息
    Interaction = "interaction"  # Interaciton消息
    Plugin = "plugin"


class ExecuteStatus(str, Enum):
    Start = "start"
    Finish = "finish"
    Interrupted = "interrupted"
    Agent = "agent"


class ExecuteResponse(BaseModel):
    type: ExecuteResponseType = Field(ExecuteResponseType.Trace)
    payload: dict = Field(default_factory=dict)

    model_config = {
        "use_enum_values": True,  # 序列化时输出枚举值而非对象
        "json_encoders": {ExecuteResponseType: lambda v: v.value,
                          ExecuteStatus: lambda v: v.value}  # 明确指定枚举序列化方式
    }


class TraceResponse(BaseInfo):
    status: ExecuteStatus = Field(ExecuteStatus.Start)
    inputs: Optional[Dict[str, Any]] = Field(default_factory=dict)
    outputs: Optional[Dict[str, Any]] = Field(default_factory=dict)  # 输出字典
    output_text: Optional[str] = Field("")  # 输出文本
    error: Optional[dict] = Field("")
    start_time: Optional[datetime] = Field(default_factory=datetime.now)
    end_time: Optional[datetime] = Field(default=None)
    parent_id: Optional[str] = Field("")
    loop_index: Optional[int] = Field(None)

    model_config = {
        "use_enum_values": True,  # 序列化时输出枚举值而非对象
        "json_encoders": {ExecuteResponseType: lambda v: v.value,
                          ExecuteStatus: lambda v: v.value}  # 明确指定枚举序列化方式
    }


class InteractionResponse(BaseModel):
    interaction_node: str = Field(default_factory=str)
    interaction_msg: Any = Field(default_factory=str)
