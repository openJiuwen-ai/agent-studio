#!/usr/bin/env python
# coding=utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

"""
React Stream Data Adapter — 将 openjiuwen OutputSchema 和 TraceSchema 转换为 SSE 格式
"""

from __future__ import annotations

import json
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional


# 事件类型常量
class EventType:
    START = "start"
    AGENT_NODE_MESSAGE = "agent_node_message"
    FUNCTION_CALL = "function_call"
    FUNCTION_CALL_END = "function_call_end"
    API_EXEC_DATA = "api_exec_data"
    MESSAGE = "message"
    MESSAGE_END = "message_end"
    AGENT_INTERRUPTED = "agent_interrupted"
    INTERMEDIATE_MESSAGE = "intermediate_message"
    STATISTIC_DATA = "statistic_data"
    SUMMARY_RESPONSE = "summary_response"
    DONE = "done"
    ERROR = "error"


# OutputSchema 类型到处理方法的映射
OUTPUT_TYPE_HANDLERS = {
    "llm_output": "_handle_llm_output",
    "llm_reasoning": "_handle_llm_reasoning",
    "llm_usage": "_handle_llm_usage",
    "answer": "_handle_answer",
    "function_result": "_handle_function_result",
    "__interaction__": "_handle_interaction",
    "done": "_handle_done",
}


class ReactStreamDataAdapter:
    """将 ReActAgent 的 OutputSchema 和 TraceSchema 转换为目标 SSE 格式"""

    def __init__(self, execution_id: str = ""):
        self._execution_id = execution_id or str(uuid.uuid4())
        self._index = 0
        self._start_time: Optional[int] = None
        self._chain_id: Optional[str] = None
        self._agent_node_id: Optional[str] = None
        self._llm_invoke_id: Optional[str] = None
        self._llm_start_time: Optional[datetime] = None
        self._llm_inputs: Optional[List[Dict]] = None
        self._llm_meta_data: Optional[Dict] = None
        self._accumulated_text = ""
        self._child_invoke_ids: List[str] = []
        self._final_output = ""
        self._is_llm_call_started = False
        # 用于累积工具调用和结果
        self._tool_calls: List[Dict] = []
        self._tool_results: List[Dict] = []

    @property
    def start_time(self) -> Optional[int]:
        return self._start_time

    @start_time.setter
    def start_time(self, value: int) -> None:
        self._start_time = value

    @property
    def final_output(self) -> str:
        return self._final_output

    @property
    def child_invoke_ids(self) -> List[str]:
        return self._child_invoke_ids

    def set_chain_and_agent_ids(self, chain_id: str, agent_node_id: str) -> None:
        """设置 chain 和 agent 节点 ID"""
        self._chain_id = chain_id
        self._agent_node_id = agent_node_id

    def set_llm_invoke_id(self, invoke_id: str) -> None:
        """设置 LLM 调用 ID"""
        self._llm_invoke_id = invoke_id
        self._llm_start_time = datetime.now()

    def add_child_invoke_id(self, invoke_id: str) -> None:
        """添加子调用 ID"""
        self._child_invoke_ids.append(invoke_id)

    def set_llm_inputs(self, inputs: List[Dict]) -> None:
        """设置 LLM 输入消息"""
        self._llm_inputs = inputs

    def set_llm_meta_data(self, meta_data: Dict) -> None:
        """设置 LLM 元数据（模型参数）"""
        self._llm_meta_data = meta_data

    def adapt(self, chunk: Any) -> List[Dict]:
        """将 OutputSchema 或 TraceSchema 转换为 SSE 事件列表"""
        if chunk is None:
            return []

        if self._start_time is None:
            self._start_time = int(time.time() * 1000)

        chunk_type = getattr(chunk, "type", None)

        if chunk_type in OUTPUT_TYPE_HANDLERS:
            handler_name = OUTPUT_TYPE_HANDLERS[chunk_type]
            handler = getattr(self, handler_name)
            return handler(chunk)

        if chunk_type == "tracer_agent":
            return self._handle_tracer_agent(chunk)

        return []

    def _handle_llm_output(self, output: Any) -> List[Dict]:
        """处理 LLM 流式输出"""
        events = []
        payload = getattr(output, "payload", {}) or {}
        content = payload.get("content", "") or ""

        if content:
            self._accumulated_text += content
            events.append(self._create_event(EventType.MESSAGE, {"answer": content}))

        return events

    def _handle_llm_reasoning(self, output: Any) -> List[Dict]:
        """处理 LLM 推理输出"""
        events = []
        payload = getattr(output, "payload", {}) or {}
        reasoning = payload.get("content", "") or ""

        if reasoning:
            events.append(self._create_event(EventType.MESSAGE, {"think": reasoning, "isReasoning": True}))

        return events

    def _handle_llm_usage(self, output: Any) -> List[Dict]:
        """处理 LLM 使用统计"""
        events = []
        payload = getattr(output, "payload", {}) or {}
        usage_metadata = payload.get("usage_metadata", {})

        if self._llm_invoke_id and self._is_llm_call_started:
            llm_end_time = datetime.now()
            elapsed = self._calc_elapsed_time(self._llm_start_time, llm_end_time)

            outputs = {
                "role": "assistant",
                "content": self._accumulated_text,
                "latency": {
                    "total_latency": usage_metadata.get("total_latency", 0),
                    "model_latency": None,
                    "wait_latency": None,
                },
                "function_call_list": [],
                "reasoning_content": "",
                "model_stats": {},
                "model_usage": {
                    "input_tokens": usage_metadata.get("input_tokens", 0),
                    "output_tokens": usage_metadata.get("output_tokens", 0),
                    "total_tokens": usage_metadata.get("total_tokens", 0),
                },
            }

            events.append(
                self._create_agent_node_event(
                    invoke_id=self._llm_invoke_id,
                    invoke_type="llm",
                    name="Openai",
                    start_time=self._llm_start_time,
                    end_time=llm_end_time,
                    elapsed=elapsed,
                    inputs=self._llm_inputs,
                    outputs=outputs,
                    meta_data=self._llm_meta_data,
                )
            )

            events.append(self._create_event(EventType.FUNCTION_CALL_END, {}))
            self._is_llm_call_started = False

        return events

    def _handle_answer(self, output: Any) -> List[Dict]:
        """处理最终回答"""
        events = []
        payload = getattr(output, "payload", {}) or {}
        output_text = payload.get("output", "") or ""

        if payload.get("result_type", "") == "error":
            return [self.adapt_error(error_msg=output_text, error_code=103004)]

        if output_text:
            self._final_output = output_text

        elapsed = round((time.time() * 1000 - self._start_time) / 1000, 2) if self._start_time else 0

        events.append(self._create_event(EventType.DONE, {}))
        events.append(self._create_event(EventType.STATISTIC_DATA, {"answer": {"overall_latency": elapsed}}))
        events.append(
            self._create_event(EventType.SUMMARY_RESPONSE, {"answer": {"role": "assistant", "content": output_text}}))

        # 构建完整的 intermediate_message，包含工具调用信息
        answer_content = []
        # 如果有工具调用，添加 assistant 的 tool_calls
        if self._tool_calls:
            answer_content.append({
                "role": "assistant",
                "content": self._accumulated_text,
                "tool_calls": self._tool_calls,
            })
            # 添加工具结果
            answer_content.extend(self._tool_results)
        # 添加最终回复
        if output_text:
            answer_content.append({
                "role": "assistant",
                "content": output_text,
            })

        if answer_content:
            events.append(self._create_event(EventType.INTERMEDIATE_MESSAGE, {"answer": answer_content}))

        return events

    def _handle_function_result(self, output: Any) -> List[Dict]:
        """处理函数执行结果（预留，未来可能使用）"""
        return []

    def _handle_interaction(self, output: Any) -> List[Dict]:
        """将 ReActAgent 的交互中断转换为前端可识别的消息事件。

        原生 Workflow ability 在需要用户输入时输出
        ``OutputSchema(type="__interaction__")``。其 payload 通常是
        ``InteractionOutput(id=<component_id>, value=<question>)``。
        """
        payload = getattr(output, "payload", None)
        if isinstance(payload, dict):
            interaction_id = payload.get("id", "")
            value = payload.get("value", "")
        else:
            interaction_id = getattr(payload, "id", "")
            value = getattr(payload, "value", "")

        if isinstance(value, dict):
            answer = (
                value.get("answer")
                or value.get("question")
                or value.get("content")
                or json.dumps(value, ensure_ascii=False)
            )
        elif value is None:
            answer = ""
        else:
            answer = str(value)

        self._final_output = answer
        data = {
            "answer": answer,
            "node_id": interaction_id,
            "interaction_id": interaction_id,
            "should_interrupt": True,
        }
        return [
            self._create_event(EventType.MESSAGE, dict(data)),
            self._create_event(
                EventType.MESSAGE_END,
                {**data, "enable_history": True},
            ),
            self._create_event(
                EventType.AGENT_INTERRUPTED,
                {
                    "reason": "waiting_user_input",
                    "state": "interrupted",
                    "task_id": self._execution_id,
                    "interaction_id": interaction_id,
                    "node_id": interaction_id,
                },
            ),
        ]

    def _handle_done(self, output: Any) -> List[Dict]:
        """处理 done 事件"""
        return [self._create_event(EventType.DONE, {})]

    def _handle_tracer_agent(self, chunk: Any) -> List[Dict]:
        """处理 tracer_agent 事件（工具调用追踪）"""
        events = []
        payload = getattr(chunk, "payload", {}) or {}

        invoke_id = payload.get("invokeId", str(uuid.uuid4()))
        invoke_type = payload.get("invokeType", "chain")
        name = payload.get("name", "Agent")
        status = payload.get("status", "")
        inputs = payload.get("inputs", {})
        outputs = payload.get("outputs", {})
        meta_data = payload.get("metaData", {})

        if invoke_type != "plugin":
            return events

        if status == "start":
            plugin_name = meta_data.get("class_name", name)
            tool_inputs = inputs.get("inputs", {}) if isinstance(inputs, dict) else inputs

            # 记录工具调用信息，用于生成完整的 intermediate_message
            self._tool_calls.append({
                "type": "function",
                "id": invoke_id,
                "function": {
                    "name": plugin_name,
                    "arguments": tool_inputs,
                }
            })

            events.append(
                self._create_event(
                    EventType.FUNCTION_CALL,
                    {
                        "answer": {
                            "function_call": {
                                "name": plugin_name,
                                "arguments": json.dumps(tool_inputs, ensure_ascii=False) if tool_inputs else "{}",
                                "tool_call_id": invoke_id,
                            },
                            "time_consumption": {
                                "total_latency": 0,
                                "model_latency": None,
                                "wait_latency": None,
                                "overall_latency": 0,
                            },
                            "is_workflow": False,
                        }
                    },
                )
            )

            self.add_child_invoke_id(invoke_id)
            events.append(
                self._create_agent_node_event(
                    invoke_id=invoke_id,
                    invoke_type="plugin",
                    name=plugin_name,
                    start_time=datetime.now(),
                    inputs=tool_inputs,
                    meta_data={
                        "instance_attributes": {
                            "plugin_name": plugin_name,
                        }
                    },
                )
            )

        elif status == "finish":
            plugin_name = meta_data.get("class_name", name)
            output_data = outputs.get("outputs", {}) if isinstance(outputs, dict) else outputs
            tool_inputs = inputs.get("inputs", {}) if isinstance(inputs, dict) else inputs

            # 记录工具结果，用于生成完整的 intermediate_message
            self._tool_results.append({
                "role": "tool",
                "name": plugin_name,
                "content": json.dumps(output_data, ensure_ascii=False) if isinstance(output_data, dict) else str(
                    output_data),
                "tool_call_id": invoke_id,
            })

            events.append(
                self._create_event(
                    EventType.API_EXEC_DATA,
                    {
                        "answer": {
                            "role": "function",
                            "name": plugin_name,
                            "content": {
                                "error_code": output_data.get("errCode", 0) if isinstance(output_data, dict) else 0,
                                "result": output_data.get("data", {}) if isinstance(output_data, dict) else output_data,
                                "latency": 0,
                            },
                            "time_consumption": {"plugin_latency": 0, "overall_latency": 0},
                        }
                    },
                )
            )

            events.append(
                self._create_agent_node_event(
                    invoke_id=invoke_id,
                    invoke_type="plugin",
                    name=plugin_name,
                    start_time=datetime.now(),
                    end_time=datetime.now(),
                    elapsed="0.00s",
                    inputs=tool_inputs,
                    outputs=output_data,
                    meta_data={
                        "instance_attributes": {
                            "plugin_name": plugin_name,
                        }
                    },
                )
            )

        return events

    def _calc_elapsed_time(self, start: Any, end: Any) -> Optional[str]:
        """计算耗时"""
        if not start or not end:
            return None

        if isinstance(start, str):
            try:
                start = datetime.fromisoformat(start.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                return None

        if isinstance(end, str):
            try:
                end = datetime.fromisoformat(end.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                return None

        if not isinstance(start, datetime) or not isinstance(end, datetime):
            return None

        delta = end - start
        return f"{delta.total_seconds():.2f}s"

    def _create_event(self, event_type: str, data: Dict) -> Dict:
        """创建 SSE 事件"""
        event = {
            "event": event_type,
            "data": data,
            "executionId": self._execution_id,
            "index": self._index,
            "createdTime": int(time.time() * 1000),
            "isStructMessage": False,
        }
        self._index += 1
        return event

    def _create_agent_node_event(
            self,
            invoke_id: Optional[str] = None,
            invoke_type: str = "chain",
            name: str = "Agent",
            start_time: Optional[datetime] = None,
            end_time: Optional[datetime] = None,
            elapsed: Optional[str] = None,
            inputs: Any = None,
            outputs: Any = None,
            child_invokes: Optional[List[str]] = None,
            meta_data: Optional[Dict] = None,
    ) -> Dict:
        """创建 agent_node_message 事件"""
        invoke_id = invoke_id or str(uuid.uuid4())
        chain_id = self._chain_id or invoke_id
        start_time = start_time or datetime.now()

        # 只有当 end_time 有值时才设置，避免开始事件也被添加到 invokeList
        if end_time and elapsed is None:
            elapsed = self._calc_elapsed_time(start_time, end_time) or "0.00s"

        node_data = {
            "invokeId": invoke_id,
            "parentInvokeId": self._agent_node_id if invoke_type != "chain" else None,
            "chainId": chain_id,
            "invokeType": invoke_type,
            "name": name,
            "startTime": start_time.isoformat() if isinstance(start_time, datetime) else start_time,
            "endTime": end_time.isoformat() if isinstance(end_time, datetime) and end_time else None,
            "elapsedTime": elapsed,
            "inputs": inputs,
            "outputs": outputs,
            "error": None,
            "childInvokes": child_invokes or [],
            "metaData": meta_data or {},
        }

        return self._create_event(EventType.AGENT_NODE_MESSAGE, node_data)

    def create_start_event(self, execution_id: str = "") -> Dict:
        """创建 start 事件"""
        return {
            "event": EventType.START,
            "data": {},
            "executionId": execution_id or self._execution_id,
            "index": self._index,
            "createdTime": int(time.time() * 1000),
            "isStructMessage": False,
        }

    def create_agent_node_start_event(
            self,
            invoke_id: str = "",
            chain_id: str = "",
            invoke_type: str = "chain",
            name: str = "Agent",
            inputs: Any = None,
            child_invokes: Optional[List[str]] = None,
            meta_data: Optional[Dict] = None,
    ) -> Dict:
        """创建 agent_node_message 开始事件"""
        return self._create_agent_node_event(
            invoke_id=invoke_id or str(uuid.uuid4()),
            invoke_type=invoke_type,
            name=name,
            start_time=datetime.now(),
            inputs=inputs,
            child_invokes=child_invokes,
            meta_data=meta_data,
        )

    def create_agent_node_end_event(
            self,
            invoke_id: str,
            chain_id: str = "",
            invoke_type: str = "chain",
            name: str = "Agent",
            inputs: Any = None,
            outputs: Any = None,
            child_invokes: Optional[List[str]] = None,
    ) -> Dict:
        """创建 agent_node_message 结束事件"""
        return self._create_agent_node_event(
            invoke_id=invoke_id,
            invoke_type=invoke_type,
            name=name,
            start_time=datetime.now(),
            end_time=datetime.now(),
            elapsed="0.00s",
            inputs=inputs,
            outputs=outputs,
        )

    def adapt_error(self, error_msg: str, execution_id: str = "", error_code: int = 103104,
                    node_name: str = "Agent") -> Dict:
        """创建错误事件

        Args:
            error_msg: 原始错误消息（会被统一格式包装）
            execution_id: 执行ID
            error_code: 应用级错误码（默认 103104 = 通用执行错误）
            node_name: 发生错误的节点显示名称
        """
        from jiuwen.orchestration.flow.constant import WORKFLOW_UNIFIED_ERROR_INFORMATION_UNSAFE
        formatted_msg = WORKFLOW_UNIFIED_ERROR_INFORMATION_UNSAFE.format(error_code, error_msg)
        return {
            "event": EventType.ERROR,
            "data": {
                "code": error_code,
                "message": formatted_msg,
                "node_name": node_name,
            },
            "executionId": execution_id or self._execution_id,
            "index": self._index,
            "createdTime": int(time.time() * 1000),
            "isStructMessage": False,
        }
