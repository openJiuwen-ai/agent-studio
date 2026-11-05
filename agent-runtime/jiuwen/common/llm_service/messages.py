#  Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
"""
Message
"""

from typing import Union, Dict, List, Optional, Any

from pydantic import BaseModel


class ToolCall(BaseModel):
    """ToolCall class"""

    name: str = ""
    args: Dict[str, Any] = {}
    id: Optional[str] = ""


class Tool(BaseModel):
    """Tool class"""

    name: str
    description: str
    parameters: Dict
    principle: str
    results: Any


class UsageMetadata(BaseModel):
    """UsageMetadata class"""

    code: int = -1
    errmsg: str = "Model request exception, please try again."
    prompt: str = ""
    task_id: str = ""
    model_name: str = ""
    finish_reason: str = ""
    total_latency: float = 0.0
    model_stats: dict = {}
    first_token_time: str = ""
    requests_start_time: str = ""
    type: Optional[str] = ""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


class BaseMessage(BaseModel):
    """BaseMessage class"""

    type: str

    content: Union[str, List[Union[str, Dict]]]

    name: Optional[str] = None

    id: Optional[str] = None


class ChatMessage(BaseMessage):
    """ChatMessage class"""

    type: str = "chat"

    role: str


class AIMessage(BaseMessage):
    """AIMessage class"""

    type: str = "assistant"

    tool_calls: Union[ToolCall, List[ToolCall]] = None  # 兼容多工具调用和历史版本

    usage_metadata: Optional[UsageMetadata] = None

    raw_content: str = None

    reasoning_content: str = None


class HumanMessage(BaseMessage):
    """HumanMessage class"""

    type: str = "user"


class SystemMessage(BaseMessage):
    """SystemMessage class"""

    type: str = "system"


class FunctionMessage(BaseMessage):
    """FunctionMessage class"""

    type: str = "function"

    name: str


class ToolMessage(BaseMessage):
    """ToolMessage class"""

    type: str = "tool"

    tool_call_id: str
