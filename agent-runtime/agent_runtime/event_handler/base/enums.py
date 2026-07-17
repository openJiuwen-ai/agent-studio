# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Event handler enums"""

from enum import Enum


class OriginStatus(Enum):
    """Jiuwen original status."""
    START = "start"
    ERROR = "error"
    FINISH = "finish"
    RUNNING = "running"


class CustomNode(Enum):
    """Custom node types."""
    CONTAINER = "EI.IntentDetectionContainer"
    COMPLEX_INTENT = "EI.ComplexIntentDetection"
    EXTRACTION = "jiuwen.paramExtraction"
    PLANNER = "jiuwen.planner"
    LOOP_INPUT = "jiuwen.loopInput"
    LOOP_OUTPUT = "jiuwen.loopOutput"
    PARAM_OUTPUT = "EI.ParamOutput"
    HTTP = "EI.http"
    LTM = "EI.LTM"
    SQL = "EI.sql"


class NodeStatus(Enum):
    """Workflow node status."""
    STARTED = "node_started"
    FINISHED = "node_finished"
    WAITING = "node_wait"
    # ERROR is intentionally an alias of FINISHED for commercial compatibility
    # (commercial event handler uses "node_finished" for both success and error states)
    ERROR = "node_finished"


class EventStatus(Enum):
    """Event status with code/desc."""
    SUCCESS = {"code": 0, "desc": "succeeded"}
    WAITING = {"code": 1, "desc": "waiting"}
    ERROR = {"code": 2, "desc": "failed"}
    UNKNOWN = {"code": -1, "desc": "unknown type received"}


class EventMapping(Enum):
    """Jiuwen internal event → external event mapping."""
    WORKFLOW_START = "workflow_started"
    MESSAGE_END = "message"
    WORKFLOW_END = "workflow_finished"
    DONE = "end"
    FUNCTION_CALL = "plugin_start"
    API_EXEC_DATA = "plugin_end"


class ToolType(Enum):
    """Tool invocation types."""
    PLUGIN = "plugin"
    MCP = "mcp"
    WORKFLOW = "workflow"
