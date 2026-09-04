"""会话工作台用户单/多智能体适配层。

只组合 agent-runtime 现有 runner，不修改官方执行模块；对外统一输出 TeamEvent。
"""

import json
import logging
from typing import Any, AsyncGenerator

from agent_runtime.serve.apis.orchestration import _get_runner_by_type, prepare_params
from agent_runtime.schemas.orchestration_mgr import ExecutionRequest, ExecutionParams
from jiuwen.serve.controllers.execution.open_utils import async_ir_load
from agent_runtime.supervisor.event.adapt import (
    build_error,
    build_message,
    build_reasoning,
    build_run_done,
    build_tool_call,
    build_tool_result,
)

logger = logging.getLogger(__name__)


def _event_payload(raw: Any) -> dict | None:
    """把官方 runner 输出统一成事件 dict。"""
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, (bytes, bytearray)):
        text = bytes(raw).decode("utf-8", errors="replace")
        if not text.startswith("data: "):
            return None
        try:
            payload = json.loads(text[6:].strip())
        except json.JSONDecodeError:
            return None
        return payload if isinstance(payload, dict) else None
    return None


def _text(data: dict) -> str:
    for key in ("delta", "answer", "content", "text", "output"):
        value = data.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def _answer_data(data: Any) -> dict:
    if isinstance(data, dict):
        answer = data.get("answer")
        if isinstance(answer, dict):
            return answer
        return data
    return {}


def _adapt_event(raw: Any, execution_id: str) -> dict | None:
    """将 ReAct/Controller runner 的单帧输出映射到 TeamEvent。"""
    payload = _event_payload(raw)
    if not payload:
        return None
    event = payload.get("event", "")
    data = payload.get("data") or {}
    if not isinstance(data, dict):
        data = {"content": str(data)}

    if event in {"message", "message_end", "agent_node_message", "intermediate_message"}:
        answer = _answer_data(data)
        if answer.get("isReasoning") or answer.get("think"):
            content = answer.get("think") or answer.get("content") or ""
            return build_reasoning(execution_id, str(content)) if content else None
        content = _text(answer)
        return build_message(execution_id, content) if content else None

    if event in {"function_call", "pe_function_call"}:
        answer = _answer_data(data)
        call = answer.get("function_call") or answer.get("functionCall") or {}
        if not isinstance(call, dict):
            return None
        name = str(call.get("name") or "tool")
        call_id = str(call.get("tool_call_id") or call.get("toolCallId") or name)
        arguments = call.get("arguments")
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError:
                arguments = {"raw": arguments}
        return build_tool_call(execution_id, call_id, name, arguments if isinstance(arguments, dict) else None)

    if event in {"api_exec_data", "function_call_end", "pe_api_exec_data"}:
        answer = _answer_data(data)
        call_id = str(answer.get("tool_call_id") or answer.get("toolCallId") or "tool")
        name = str(answer.get("name") or answer.get("tool_name") or "tool")
        result = answer.get("result") or answer.get("content") or answer.get("answer") or ""
        return build_tool_result(execution_id, call_id, name, str(result))

    if event == "agent_handoff":
        target = data.get("target_agent") or {}
        target_id = str(target.get("id") or "unknown") if isinstance(target, dict) else "unknown"
        call_id = str(data.get("task_id") or target_id)
        return build_tool_call(
            execution_id,
            call_id,
            f"transfer_to_{target_id[:8]}",
            {"query": data.get("query", "")},
        )

    if event == "done":
        return build_run_done(execution_id, _text(data))

    if event in {"error", "exception", "task_terminated"}:
        message = data.get("message") or data.get("error") or str(data)
        return build_error(execution_id, event, str(message))

    # 无法映射到现有 TeamEvent 的执行事件（task_start/task_end/agent_interrupted/workflow_node_message 等）
    # 不伪造 subExecutionId，不拆分归属；保留主流程可用性，记录 debug 便于后续核对。
    logger.debug(
        "conversation app event dropped (no TeamEvent mapping): event=%s executionId=%s",
        event,
        execution_id,
    )
    return None


async def stream_application(
    req: Any,
    execution_id: str,
) -> AsyncGenerator[dict, None]:
    """执行用户 APP 并输出统一 TeamEvent。"""
    ir_path = f"agent/ir/{req.app_id}/{req.app_id}.json"
    ir_data = await async_ir_load(ir_path)
    mode = (ir_data.get("configs") or {}).get("mode", "ReAct")
    if mode not in {"ReAct", "Controller", "PlanExecute"}:
        raise ValueError(f"unsupported conversation app mode: {mode}")

    history = req.conversation_history or []
    params = ExecutionParams(
        conversationHistory=history,
        globalVariables={
            "sys": {
                "conversationHistory": history,
                "conversationId": req.conversation_id,
                "userId": req.user_id,
            },
            "conversationId": req.conversation_id,
            "userId": req.user_id,
        },
        pluginConfigs=[],
        toolSwitchDict={},
        isDebug=False,
    )
    execution_request = ExecutionRequest(
        conversationId=req.conversation_id,
        userId=req.user_id,
        irPath=ir_path,
        query=req.query,
        params=params,
        headers={},
    )
    execution_request.params = prepare_params(execution_request)
    runner = _get_runner_by_type(mode)
    raw_stream = runner.run_streaming(execution_request, execution_id)
    async for raw in raw_stream:
        event = _adapt_event(raw, execution_id)
        if event is not None:
            yield event
