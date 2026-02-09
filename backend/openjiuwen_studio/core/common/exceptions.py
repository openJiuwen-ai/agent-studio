#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import time
import copy
import json
import uuid
from typing import Optional, Any, Dict, List, TypeVar, Union
from fastapi import status
from pydantic import BaseModel, Field

from openjiuwen_studio.core.common.dsl import Connection
from openjiuwen.core.common.exception.errors import BaseError as FrameworkBaseError
from openjiuwen.core.common.exception.codes import StatusCode as FrameworkStatusCode


class BaseError(FrameworkBaseError):
    def __init__(self, code: int = None, message: str = None, error_status=None, **kwargs):
        if error_status is None:
            # Fallback to generic error from framework to satisfy type hints/structure
            error_status = FrameworkStatusCode.ERROR
        
        # Framework BaseError expects status object with .code and .errmsg
        super().__init__(error_status, msg=message, **kwargs)

        # Explicitly override code if provided, as super().__init__ sets it from status.code
        if code is not None:
            self.code = code
        # Explicitly override message if provided, ensuring it takes precedence
        if message is not None:
            self.message = message


class JiuWenComponentException(BaseError):
    def __init__(self, code: int, message: str, component_id: str, component_type: int,
                 error_stage: str = "convert") -> None:
        super().__init__(code=code, message=message)
        self._component_id = component_id
        self._component_type = component_type
        self._error_stage = error_stage

    @property
    def component_id(self) -> str:
        return self._component_id

    @property
    def component_type(self) -> int:
        return self._component_type

    @property
    def error_stage(self) -> str:
        return self._error_stage


class ErrorNodeInfo(BaseModel):
    node_id: str = Field(default="")
    connection: Connection = Field(default_factory=Connection)
    error_message: str = Field(default="")
    error_code: int = Field(default=int)


class WorkflowErrorData(BaseModel):
    error_nodes_info: Optional[List[ErrorNodeInfo]] = Field(default_factory=list)
    workflow_id: str = Field("")


class WorkflowFailedResponse(BaseModel):
    data: Optional[WorkflowErrorData] = Field(default_factory=WorkflowErrorData)
    code: int = Field(default=status.HTTP_400_BAD_REQUEST)
    message: str = Field(default="工作流运行失败")


class JiuWenExecuteException(BaseError):
    """workflow图异常"""

    def __init__(self, code: int, message: str, workflow_id="", node_id="", connection=None):
        super().__init__(code=code, message=message)
        self._workflow_id = workflow_id
        self._node_id = node_id
        self._connection = connection

    # 添加公共的setter方法
    def set_workflow_id(self, workflow_id: str) -> None:
        self._workflow_id = workflow_id

    # 添加公共的setter方法
    def set_node_id(self, node_id: str) -> None:
        self._node_id = node_id

    def set_connection(self, connection: Connection) -> None:
        self._connection = connection

    @property
    def workflow_id(self) -> str:
        return self._workflow_id

    @property
    def node_id(self) -> str:
        return self._node_id

    @property
    def connection(self):
        if self._connection is None or (
                isinstance(self._connection, type) and issubclass(self._connection, Connection)):
            self._connection = Connection()
        return self._connection


class DeepSearchClientError(Exception):
    def __init__(self, error_code: str, message: str):
        self.error_code = error_code
        self.message = message
        super().__init__(error_code, message)

    def generate_error_stream(self, conversation_id: str = "") -> list[str]:
        """生成完整的错误事件流（SSE 格式字符串列表）"""
        event_time = int(time.time() * 1000)
        message_id_error = str(uuid.uuid4())
        message_id_summary = str(uuid.uuid4())
        start_id = str(uuid.uuid4())

        base_event = {
            "conversation_id": conversation_id,
            "section_idx": "0",
            "plan_idx": "0",
            "step_idx": "0",
            "message_id": "",
            "agent": "",
            "role": "assistant",
            "content": "",
            "message_type": "message_chunk",
            "event": "",
            "created_time": "",
        }

        # Start event
        event_start = copy.deepcopy(base_event)
        event_start.update({
            "message_id": start_id,
            "agent": "entry",
            "event": "start",
            "created_time": event_time,
        })

        # Message event
        event_message = copy.deepcopy(event_start)
        event_message["event"] = "message"
        event_message["created_time"] = event_time

        # Done event
        event_done = copy.deepcopy(event_message)
        event_done["event"] = "done"
        event_done["created_time"] = event_time

        # Error content
        content_data = {
            "response_content": "",
            "citation_messages": {},
            "infer_messages": [],
            "exception_info": f"Failed to initialize DeepSearch HTTP client: {self.message}"
        }

        # Summary response (error payload)
        error_event = copy.deepcopy(base_event)
        error_event.update({
            "message_id": message_id_error,
            "agent": "end",
            "event": "summary_response",
            "content": json.dumps(content_data, ensure_ascii=False),
            "created_time": event_time,
        })

        # Final end marker
        summary_event = copy.deepcopy(base_event)
        summary_event.update({
            "message_id": message_id_summary,
            "agent": "end",
            "event": "error",
            "content": "ALL END",
            "created_time": event_time,
        })

        events = [event_start, event_message, event_done, error_event, summary_event]
        return [f"data: {json.dumps(e, ensure_ascii=False)}\n\n" for e in events]
