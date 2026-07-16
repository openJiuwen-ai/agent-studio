# coding=utf-8
"""
JiuWen compatibility bridge: full replica of jiuwen.* imports used by agent_builder.

Provides drop-in replacements for all jiuwen classes and functions that
agent_builder depends on, with implementations identical to the originals:
  - JiuWenException, JiuWenBaseException, ErrorBody, InnerException,
    InterruptException, WorkflowAbortException  (from jiuwen.common.exception.base)
  - StatusCode  (from jiuwen.common.exception.status_code)
  - ToolCall, Tool, UsageMetadata, BaseMessage, ChatMessage,
    AIMessage, HumanMessage, SystemMessage, FunctionMessage, ToolMessage
    (from jiuwen.common.llm_service.messages)
  - DATASOURCE_REDIS_TTL_KEY  (from jiuwen.common.configs.env_constants)
  - EXPIRATION_TIME  (from jiuwen.memory.store.history)
  - request_json, request_ctx, request, g  (from jiuwen.serve.common.context)
"""

import abc
import contextvars
import threading
from dataclasses import dataclass
from enum import Enum
from typing import Union, Dict, List, Optional, Any

from pydantic import BaseModel


# ─── jiuwen.common.exception.status_code.StatusCode ────────────────────────────

class StatusCode(Enum):
    """状态码枚举类 — 完整复刻自 jiuwen.common.exception.status_code.StatusCode。"""

    SUCCESS = (0, "success")
    ERROR = (-1, "error")
    REQUEST_TIMEOUT = (408, "request timeout")

    RESOURCE_NOT_FOUND_ERROR = (100000, "Error occur when resource not found")
    AUTH_CHECK_FAILED_ERROR = (100001, "Error occur when authentication failed")
    PARAM_CHECK_FAILED_ERROR = (100002, "Error occur when input parameter verification failed")

    ORCHESTRATION_IR_PARSE_ERROR = (101000, "Error occur when parsing IR JSON")
    ORCHESTRATION_IR_BUILD_ERROR = (101001, "Error occur when building IR")
    ORCHESTRATION_IR_NOT_FOUND_ERROR = (101002, "IR not found")
    ORCHESTRATION_EXECUTION_NOT_FOUND_ERROR = (101003, "Execution not found")
    ORCHESTRATION_SESSION_NOT_FOUND_ERROR = (101004, "Session not found")
    ORCHESTRATION_SESSION_EXPIRED_ERROR = (101005, "Session expired")
    ORCHESTRATION_WORKFLOW_RUNTIME_ERROR = (101006, "Workflow runtime error")
    ORCHESTRATION_WORKFLOW_INTERRUPT_ERROR = (101007, "Workflow interrupt")
    ORCHESTRATION_INTENT_DETECTION_ERROR = (101008, "Intent detection error")
    ORCHESTRATION_AGENT_TYPE_NOT_SUPPORTED = (101009, "Agent type not supported")
    ORCHESTRATION_CONVERSATION_ID_MISSING = (101010, "Conversation ID missing")

    PROMPT_OPTIMIZE_STORAGE_ERROR = (102000, "Prompt optimize storage error: {error_msg}")
    PROMPT_OPTIMIZE_INVALID_PARAMS_ERROR = (102001, "Prompt optimize invalid parameters: {error_msg}")
    PROMPT_LLM_GENERATION_FAILED_ERROR = (102002, "Prompt LLM generation failed: {error_msg}")
    PROMPT_OPTIMIZE_TASK_NOT_FOUND_ERROR = (102003, "Prompt optimize task not found")
    PROMPT_OPTIMIZE_TASK_RUNNING_ERROR = (102004, "Prompt optimize task already running")
    PROMPT_OPTIMIZE_TASK_LIMIT_ERROR = (102005, "Prompt optimize task limit exceeded")
    LLM_FALSE_RESULT_ERROR = (102006, "LLM false result error: {error_msg}")
    PROMPT_OPTIMIZE_TASK_CANCEL_ERROR = (102007, "Prompt optimize task cancel error")
    PROMPT_OPTIMIZE_TASK_STOPPING_ERROR = (102008, "Prompt optimize task is stopping")

    PLANNER_GENERATION_FAILED_ERROR = (103000, "Planner generation failed error")

    EXECUTION_ERROR = (104000, "Execution error")
    EXECUTION_TIMEOUT_ERROR = (104001, "Execution timeout")
    EXECUTION_CODE_ERROR = (104002, "Code execution error")

    PLUGIN_NOT_FOUND_ERROR = (105000, "Plugin not found")
    PLUGIN_CALL_ERROR = (105001, "Plugin call error")
    PLUGIN_CONFIG_ERROR = (105002, "Plugin config error")

    MEMORY_STORE_ERROR = (106000, "Memory store error")
    MEMORY_RETRIEVE_ERROR = (106001, "Memory retrieve error")

    DATA_AUGMENTATION_ERROR = (107000, "Data augmentation error")

    INSIGHT_ERROR = (108000, "Insight error")

    HIGH_INTENT_NODE_ERROR = (109000, "High intent node error")
    DYNAMIC_PLANNING_ERROR = (109011, "Dynamic planning error")

    MEMORY_ENGINE_ERROR = (109300, "Memory engine error")
    CONTEXT_ENGINE_ERROR = (109500, "Context engine error")

    FUNCTION_RESERVED_ERROR = (110000, "Function reserved error")

    MYSQL_CHECK_CONFIG_ERROR = (111000, "MySQL check config error: {errno}, {reason}")
    MYSQL_EXECUTION_ERROR = (111001, "MySQL execution error: {errno}, {reason}")
    MYSQL_SQL_COMMAND_ERROR = (111002, "MySQL SQL command error: {error_msg}")

    WORKFLOW_EXCEPTION_END_ERROR = (112000, "Workflow exception end")
    WORKFLOW_CODE_RETURN_VALUE_UNEXPECTED_ERROR = (120007, "output keys should be in code return values")
    WORKFLOW_CODE_RETURN_VALUE_TYPE_ERROR = (120008, "type of code return values should be dict")

    LOG_MAX_BYTES_ERROR = (100050, "Log max bytes error")

    @property
    def code(self):
        """获取状态码"""
        return self.value[0]

    @property
    def errmsg(self):
        """获取状态码信息"""
        return self.value[1]


# ─── jiuwen.common.exception.base ────────────────────────────────────────────

MAGIC_CODE = "\t"


class JiuWenException(Exception):
    """JiuWen异常类，继承自Python的基类Exception。"""

    def __init__(self, message: str, *args, **kwargs) -> None:
        super().__init__(message, args, kwargs)


class JiuWenBaseException(Exception):
    """JiuWen异常基类，包含状态码。"""

    def __init__(
        self,
        error_code: int,
        message: str,
        node_id: str = None,
        node_name: str = None,
        node_type: str = None,
    ) -> None:
        super().__init__(error_code, message)
        self._error_code = error_code
        self._message = message
        self.node_id = node_id
        self.node_name = node_name
        self.node_type = node_type

    def __str__(self):
        return f"[{self._error_code}]{self._message}{MAGIC_CODE}"

    @property
    def error_code(self):
        return self._error_code

    @property
    def message(self):
        return self._message


@dataclass
class ErrorBody:
    error_message: str
    error_code: str

    def to_alias_dict(self):
        return {"errorMessage": self.error_message, "errorCode": self.error_code}


@dataclass
class InnerException:
    is_success: bool
    error_body: ErrorBody = None

    def to_alias_dict(self):
        return {
            "isSuccess": self.is_success,
            "errorBody": self.error_body.to_alias_dict() if self.error_body else None,
        }


class InterruptException(JiuWenBaseException):
    """InterruptException class with status codes"""

    def __init__(self, error_code: int, message: str) -> None:
        super().__init__(error_code, message)
        self._error_code = error_code
        self._message = message


class WorkflowAbortException(JiuWenBaseException):
    """异常结束组件抛出的异常，用于终止流程"""

    def __init__(
        self,
        data: dict,
        node_id: str = None,
        node_name: str = None,
        node_type: str = None,
    ) -> None:
        super().__init__(
            StatusCode.WORKFLOW_EXCEPTION_END_ERROR.code,
            StatusCode.WORKFLOW_EXCEPTION_END_ERROR.errmsg,
            node_id=node_id,
            node_name=node_name,
            node_type=node_type,
        )
        self.data = data

    def to_payload(self) -> dict:
        return self.data


# ─── jiuwen.common.llm_service.messages ──────────────────────────────────────

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
    tool_calls: Union[ToolCall, List[ToolCall]] = None
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


# ─── jiuwen.common.configs.env_constants ─────────────────────────────────────

DATASOURCE_REDIS_TTL_KEY = "DATASOURCE_REDIS_TTL"

# ─── jiuwen.common.utils.singleton ───────────────────────────────────────────

singleton_lock = threading.Lock()


class Singleton(abc.ABCMeta, type):
    """Singleton metaclass — 完整复刻自 jiuwen.common.utils.singleton.Singleton。"""

    _instances = {}

    def __call__(cls, *args, **kwargs):
        with singleton_lock:
            if cls not in cls._instances:
                cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
            return cls._instances[cls]


# ─── jiuwen.memory.store.history ─────────────────────────────────────────────

EXPIRATION_TIME = 3 * 24 * 60 * 60  # 259200 seconds = 3 days

# ─── jiuwen.serve.common.context ─────────────────────────────────────────────

import asyncio
from functools import wraps
from typing import Callable

from fastapi import Request as _FastAPIRequest

request: contextvars.ContextVar[_FastAPIRequest | None] = contextvars.ContextVar(
    "request", default=None
)

g: contextvars.ContextVar[dict] = contextvars.ContextVar("g", default={})

request_json: contextvars.ContextVar[dict] = contextvars.ContextVar(
    "request_json", default={}
)

request_ctx: contextvars.ContextVar[dict] = contextvars.ContextVar(
    "request_ctx", default={}
)


def copy_current_request_context(func: Callable) -> Callable:
    """copy_current_request_context"""
    current_context = contextvars.copy_context()

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return current_context.run(func, *args, **kwargs)

    @wraps(func)
    async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
        return await current_context.run(func, *args, **kwargs)

    return async_wrapper if asyncio.iscoroutinefunction(func) else wrapper


def is_json(req: _FastAPIRequest) -> bool:
    """is_json"""
    content_type = req.headers.get("Content-Type")
    return content_type is not None and "application/json" in content_type
