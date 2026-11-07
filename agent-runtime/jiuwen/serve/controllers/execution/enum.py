# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.

"""This module defines the execution Enums."""

from enum import Enum


class IRType(str, Enum):
    """
    Enum of IR types.
    """

    Agent = "agent"
    Workflow = "workflow"
    MultiAgents = "multiagents"
    DeepResearch = "deep_research"


class PlanModeType(str, Enum):
    """
    Enum of IR types.
    """

    ReAct = "ReAct"
    Controller = "Controller"
    ToolUse = "ToolUse"
    PlanExecute = "PlanExecute"


class ResponseMode(str, Enum):
    """
    2 ResponseMode
    - streaming 流式返回
    - blocking  段落返回
    """

    STREAMING = "streaming"
    BLOCKING = "blocking"


class ExecutionMode(str, Enum):
    """
    2 ResponseMode
    - sync   同步执行
    - async  异步执行
    """

    SYNC = "sync"
    ASYNC = "async"


class MessageRole(str, Enum):
    """
    3 message roles
    - user          用户输入的消息
    - assistant     应用返回的消息
    - function      插件调用产生的中间信息
    """

    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"


class ConversationEvent(str, Enum):
    """
    [non-streaming event]
    blocking_response       非流式回复
    async_response          异步执行回复

    [streaming conversation events]
    start                   流式开始标识
    done	                流式结束标识
    message	                正文回复
    error                   流式报错信息

    function_call_end       标识大模型生成工具调用信息完成
    function_call	        工具调用信息
    api_exec_data           工具调用结果
    statistic_data	        统计信息字段，如：请求相应事件，token消耗等
    summary_response	    结果汇总，将所有流式信息拼接成完成字符串

    workflow_begin	        workflow输出中间结果起始标识
    workflow_message_end	workflow一次流式返回的多节点的分割标识
    workflow_end	        workflow输出中间结果终止标识
    """

    # 非流式输出
    BLOCKING_RESPONSE = "blocking_response"
    ASYNC_RESPONSE = "async_response"

    # 流式输出
    START = "start"
    DONE = "done"
    MESSAGE = "message"
    ERROR = "error"
    EXCEPTION = "exception"

    FUNCTION_CALL_END = "function_call_end"
    FUNCTION_CALL = "function_call"
    API_EXEC_DATA = "api_exec_data"
    STATISTIC_DATA = "statistic_data"
    SUMMARY_RESPONSE = "summary_response"

    WORKFLOW_START = "workflow_start"
    MESSAGE_END = "message_end"
    WORKFLOW_END = "workflow_end"
    AGENT_NODE_MSG = "agent_node_message"
    WORKFLOW_NODE_MESSAGE = "workflow_node_message"
    INTERMEDIATE_MESSAGE = "intermediate_message"

    # 控制器新增
    WAITING_USER_INPUT = "waiting_user_input"
    TASK_START = "task_start"
    TASK_END = "task_end"

    # 工作流调测
    WORKFLOW_BLOCKED = "workflow_blocked"
    WORKFLOW_RESUME = "workflow_resume"
    TASK_TERMINATED = "task_terminated"

    # 多Agent
    AGENT_INTERRUPTED = "agent_interrupted"

    # PlanExecute 专属事件
    SCENE_MATCH = "scene_match"
    PLAN_END = "plan_end"
    STEP_START = "step_start"
    STEP_END = "step_end"
    TASK_COMPLETE = "task_complete"
    
    # 意图识别
    INTENT_MSG = "intent"


class AsyncExecutionStatus(Enum):
    """
    Async execution status.
    running     工作流正在执行中
    interacting 工作流单轮执行完毕，等待用户输入
    success     完成一次执行
    failed      工作流执行报错
    canceled    任务被取消
    timeout     工作流执行超时
    """

    RUNNING = "running"
    INTERACTING = "interacting"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELED = "canceled"
    TIMEOUT = "timeout"
