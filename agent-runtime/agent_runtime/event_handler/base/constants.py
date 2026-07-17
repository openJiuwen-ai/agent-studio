# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Event handler constants"""

from jiuwen.orchestration.flow.enum import NodeType
from agent_runtime.event_handler.base.enums import CustomNode

# 全局常量

EVENT_THROUGH = "event_through"
NODE_TYPE_KEY = "node_type"
DEBUG_NODE_KEY = "componentType"
CODE = 121007
INTERACTION_NODE = ["jiuwen.questioner", "jiuwen.input", "EI.qa"]
FIELD_VALUES = ["userFields", "systemFields", "environmentFields"]
DEFAULT_STATUS = {"code": 0, "desc": "succeeded"}
TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%f%z"
EXCEPTION_NO_KEY = "jiuwen_exception_node_id"
RESPONSE_CONTENT = "responseContent"

# 包含 NodeType 枚举值（如 jiuwen.LLMComponent）和组件类名（如 LLMChain）两种格式

node_type_mapping = {
    # NodeType enum values (from jiuwen engine)
    NodeType.START.value: "Start",
    NodeType.END.value: "End",
    NodeType.LLM.value: "LLM",
    NodeType.AGENT.value: "Agent",
    NodeType.API.value: "KnowledgeRepo",
    NodeType.MESSAGE.value: "Message",
    NodeType.CARD.value: "Card",
    NodeType.TASK.value: "TaskFlow",
    NodeType.BRANCH.value: "Branch",
    NodeType.CODE.value: "Code",
    NodeType.INTENT_DETECTION.value: "IntentDetection",
    NodeType.SUB_WORKFLOW.value: "Workflow",
    NodeType.QUESTIONER.value: "Questioner",
    NodeType.INPUT.value: "Input",
    NodeType.AGGREGATE.value: "Aggregation",
    NodeType.LOOP.value: "Loop",
    NodeType.SET_VARIABLE.value: "SetVariable",
    NodeType.MCP.value: "Mcp",
    NodeType.QA.value: "QA",
    NodeType.FLOW_AGENT.value: "Agent",
    NodeType.EXTRACTOR.value: "ParamExtraction",
    NodeType.STREAM_TRANSFORM.value: "ParamExtraction",
    NodeType.ERROR_END.value: "Exception",
    # CustomNode values
    CustomNode.CONTAINER.value: "IntentDetectionContainer",
    CustomNode.COMPLEX_INTENT.value: "ComplexIntentDetection",
    CustomNode.EXTRACTION.value: "ParamExtraction",
    CustomNode.PLANNER.value: "Planner",
    CustomNode.LOOP_INPUT.value: "LoopInput",
    CustomNode.LOOP_OUTPUT.value: "LoopOutput",
    CustomNode.PARAM_OUTPUT.value: "ParamOutput",
    CustomNode.HTTP.value: "Http",
    CustomNode.LTM.value: "LTM",
    CustomNode.SQL.value: "DataQuery",
    # Component class names (from workflow_stream_data_wrapper)
    "LLMChain": "LLM",
    "FlowQA": "QA",
    "SubWorkflow": "Workflow",
    "BranchComponent": "Branch",
    "LoopComponent": "Loop",
    "FlowCode": "Code",
    "FlowApi": "KnowledgeRepo",
    "FlowInput": "Input",
    "FlowMcp": "Mcp",
    "Aggregate": "Aggregation",
    "LoopSetVariable": "SetVariable",
    "ExceptionInfo": "Exception",
    "ComplexIntentDetection": "ComplexIntentDetection",
    "FlowStreamTransform": "ParamExtraction",
    "_RoutedIntentDetection": "IntentDetection",
    # Fallback
    "unknown": "Unknown",
}
