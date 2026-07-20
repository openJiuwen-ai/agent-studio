# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""流式审核 generator wrapper — 审核层的核心入口。

提供三个公共函数：
- init_moderation_from_ir(): 从 IR 配置初始化审核引擎并存入请求上下文
- apply_stream_moderation(): 输出审核 async generator wrapper
- block_event_generator(): 输入审核阻断事件生成器

事件审核通过 handler registry 管理，每种事件类型注册一个审核函数，
新增事件只需实现 handler 并注册即可，无需修改主循环。
"""

import json
import time
from typing import Any, AsyncGenerator, Callable

from agent_runtime.context.request_context import _request_ctx
from agent_runtime.moderation.engine import ModerationEngineDynamicAC
from agent_runtime.moderation.schema import normalize_content_review
from agent_runtime.moderation.stream_state import StreamModeratorState
from openjiuwen.core.common.logging import workflow_logger

# ── Handler 约定 ──────────────────────────────────────────────────────
# 每个 handler 签名:
#   (chunk: dict, engine: ModerationEngineDynamicAC, ctx: _ModerationCtx) -> dict | None
#
# 返回值:
#   dict  — 审核后的事件（可能被修改），由主循环 yield
#   None  — 事件被吞掉（不应继续下发）
#
# 当需要中断流（REPLY 阻断）时，通过 ctx.interrupt(fallback_msg) 设置中断信号，
# 主循环会在 handler 返回后检查并 emit sensitive 事件 + break。
#
# 重要：handler 调用 ctx.interrupt() 后必须 return None，否则主循环会同时
# yield 残留事件和 sensitive 事件。
# ──────────────────────────────────────────────────────────────────────


class _ModerationCtx:
    """单次流式审核的上下文状态，在 apply_stream_moderation 内部使用。"""

    __slots__ = (
        "mods", "last_created_time", "interrupted", "int_msg",
        "int_node_id", "int_node_type", "int_node_name", "int_index",
    )

    def __init__(self, engine: ModerationEngineDynamicAC):
        self.mods = {
            "think": StreamModeratorState(engine),
            "answer": StreamModeratorState(engine),
        }
        self.last_created_time = 0
        self.interrupted = False
        self.int_msg = ""
        # 中断时从触发 chunk 携带的节点上下文
        self.int_node_id = ""
        self.int_node_type = ""
        self.int_node_name = ""
        self.int_index = 0

    def interrupt(self, fallback_msg: str, chunk: dict | None = None) -> None:
        """标记流被阻断，同时从触发 chunk 提取节点上下文。"""
        self.interrupted = True
        self.int_msg = fallback_msg
        if chunk is not None:
            data = chunk.get("data", {})
            self.int_node_id = data.get("node_id", "")
            self.int_node_type = data.get("node_type", "")
            self.int_node_name = data.get("node_name", "")
            self.int_index = chunk.get("index", 0)


# ── 辅助函数 ──────────────────────────────────────────────────────────

def _clean_text_and_check_interrupt(
    engine: ModerationEngineDynamicAC,
    text: str,
    ctx: _ModerationCtx,
    chunk: dict | None = None,
) -> str | None:
    """全量审核文本，REPLY 阻断时设置 ctx.interrupt() 并返回 None。

    Returns:
        str  — 审核后的安全文本（FILTER/REPLACE 场景）
        None — 命中 REPLY 阻断，调用方应 return None
    """
    is_int, result = engine.clean_full_text(text)
    if is_int:
        ctx.interrupt(result, chunk)
        return None
    return result


# ── Handler 实现 ──────────────────────────────────────────────────────

def _handle_message(chunk: dict, engine: ModerationEngineDynamicAC, ctx: _ModerationCtx) -> dict | None:
    """审核 message / message_end 事件的 think/answer/origin_answer。

    think 和 answer 使用流式状态机（跨 chunk 边界匹配），
    origin_answer 使用全量审核（非流式）。
    """
    data = chunk.get("data", {})
    think_chunk = data.get("think", "") or ""
    answer_chunk = data.get("answer", "") or ""

    safe_think, int_think = ctx.mods["think"].process_chunk(think_chunk)
    safe_answer, int_answer = ctx.mods["answer"].process_chunk(answer_chunk)

    if int_think or int_answer:
        ctx.interrupt(int_answer or int_think, chunk)
        return None

    data["think"] = safe_think
    data["answer"] = safe_answer

    # message_end 的 origin_answer 也需审核（含 REPLY 阻断检查）
    origin_answer = data.get("origin_answer")
    if origin_answer:
        safe_origin = _clean_text_and_check_interrupt(engine, origin_answer, ctx, chunk)
        if safe_origin is None:
            return None
        data["origin_answer"] = safe_origin

    return chunk


def _handle_workflow_end(chunk: dict, engine: ModerationEngineDynamicAC, ctx: _ModerationCtx) -> dict | None:
    """审核 workflow_end 事件的 answer/origin_answer（全量审核）。"""
    data = chunk.get("data", {})
    answer_text = data.get("answer", "") or ""
    origin_answer = data.get("origin_answer", "")

    safe_answer = _clean_text_and_check_interrupt(engine, answer_text, ctx, chunk)
    if safe_answer is None:
        return None
    data["answer"] = safe_answer

    if origin_answer:
        safe_origin = _clean_text_and_check_interrupt(engine, origin_answer, ctx, chunk)
        if safe_origin is None:
            return None
        data["origin_answer"] = safe_origin

    return chunk


def _handle_agent_node_message(chunk: dict, engine: ModerationEngineDynamicAC, ctx: _ModerationCtx) -> dict | None:
    """审核 ReAct 模式 agent_node_message 事件的 outputs（模型输出）。

    inputs 是用户输入回显，输入审核阶段已处理，此处不再审核。
    """
    data = chunk.get("data", {})
    outputs = data.get("outputs")

    if isinstance(outputs, dict):
        content = outputs.get("content", "")
        if isinstance(content, str) and content:
            safe_content = _clean_text_and_check_interrupt(engine, content, ctx, chunk)
            if safe_content is None:
                return None
            outputs["content"] = safe_content

        # reasoning_content 使用 REPLACE/FILTER 清洗，不触发 REPLY 阻断
        # （think 不应因审核而中断流，只需清洗）
        reasoning = outputs.get("reasoning_content", "")
        if isinstance(reasoning, str) and reasoning:
            _, safe_reasoning = engine.clean_full_text(reasoning)
            outputs["reasoning_content"] = safe_reasoning

    elif isinstance(outputs, str) and outputs:
        safe_outputs = _clean_text_and_check_interrupt(engine, outputs, ctx, chunk)
        if safe_outputs is None:
            return None
        data["outputs"] = safe_outputs

    return chunk


def _handle_workflow_node_message(chunk: dict, engine: ModerationEngineDynamicAC, ctx: _ModerationCtx) -> dict | None:
    """审核 Workflow/Controller 模式 workflow_node_message 事件的 outputs。

    workflow_node_message 是节点级 trace 事件，outputs 可能包含 LLM 节点的输出文本。
    """
    data = chunk.get("data", {})
    outputs = data.get("outputs")

    if isinstance(outputs, str) and outputs:
        safe_outputs = _clean_text_and_check_interrupt(engine, outputs, ctx, chunk)
        if safe_outputs is None:
            return None
        data["outputs"] = safe_outputs
    elif isinstance(outputs, dict):
        # dict 形式的 outputs 递归清洗字符串值（与 intermediate_message 类似）
        _clean_dict_outputs(outputs, engine, ctx)
        if ctx.interrupted:
            # dict outputs 不应触发 REPLY 阻断，但如果意外触发了，
            # 仍需从 chunk 提取节点上下文
            if not ctx.int_node_id:
                data = chunk.get("data", {})
                ctx.int_node_id = data.get("node_id", "")
                ctx.int_node_type = data.get("node_type", "")
                ctx.int_node_name = data.get("node_name", "")
                ctx.int_index = chunk.get("index", 0)
            return None

    return chunk


def _handle_intermediate_message(chunk: dict, engine: ModerationEngineDynamicAC, ctx: _ModerationCtx) -> dict | None:
    """审核 ReAct 模式 intermediate_message 事件的 answer 列表。"""
    data = chunk.get("data", {})
    answer_val = data.get("answer")

    if isinstance(answer_val, list):
        for item in answer_val:
            if isinstance(item, dict):
                content = item.get("content", "")
                if isinstance(content, str) and content:
                    safe_content = _clean_text_and_check_interrupt(engine, content, ctx, chunk)
                    if safe_content is None:
                        return None
                    item["content"] = safe_content
    elif isinstance(answer_val, str) and answer_val:
        safe_answer = _clean_text_and_check_interrupt(engine, answer_val, ctx, chunk)
        if safe_answer is None:
            return None
        data["answer"] = safe_answer

    return chunk


def _handle_summary_response(chunk: dict, engine: ModerationEngineDynamicAC, ctx: _ModerationCtx) -> dict | None:
    """审核 summary_response 事件的 answer.content。"""
    answer_data = chunk.get("data", {}).get("answer", {})
    if isinstance(answer_data, dict):
        content = answer_data.get("content", "")
        if isinstance(content, str) and content:
            safe_content = _clean_text_and_check_interrupt(engine, content, ctx, chunk)
            if safe_content is None:
                return None
            answer_data["content"] = safe_content
    return chunk


def _clean_dict_outputs(d: dict, engine: ModerationEngineDynamicAC, ctx: _ModerationCtx) -> None:
    """递归审核 dict outputs 中的字符串值（仅清洗，不阻断）。

    对于 dict 形式的 outputs，字段结构不确定，保守地清洗所有字符串值。
    不触发 REPLY 阻断，因为 trace 事件中的输出不应因审核而中断流。
    """
    for k, v in d.items():
        if isinstance(v, str) and v:
            _, safe = engine.clean_full_text(v)
            d[k] = safe
        elif isinstance(v, dict):
            _clean_dict_outputs(v, engine, ctx)


# ── Handler Registry ──────────────────────────────────────────────────

# 事件类型 → 审核函数映射
# 新增事件类型只需在此注册即可，无需修改主循环
_EVENT_HANDLERS: dict[str, Callable[[dict, ModerationEngineDynamicAC, _ModerationCtx], dict | None]] = {
    "message": _handle_message,
    "message_end": _handle_message,
    "workflow_end": _handle_workflow_end,
    "agent_node_message": _handle_agent_node_message,
    "workflow_node_message": _handle_workflow_node_message,
    "intermediate_message": _handle_intermediate_message,
    "summary_response": _handle_summary_response,
}


# ── 公共 API ──────────────────────────────────────────────────────────

def init_moderation_from_ir(ir_json: dict) -> ModerationEngineDynamicAC | None:
    """从 IR 配置初始化审核引擎，未启用则返回 None。

    引擎实例同时存入 RequestContext.moderation_engine，
    供后续 stream_response() 取出使用。
    """
    content_review = (ir_json.get("configs") or {}).get("content_review", {})
    if not content_review or not content_review.get("enabled"):
        return None

    try:
        normalized = normalize_content_review(content_review)
    except Exception:
        workflow_logger.warning("Failed to normalize content_review config, moderation disabled")
        return None

    engine = ModerationEngineDynamicAC(normalized)

    # 存入请求上下文
    try:
        _ctx = _request_ctx.get()
        _ctx.moderation_engine = engine
        _request_ctx.set(_ctx)
    except Exception:
        workflow_logger.warning("Failed to set moderation engine in request context")

    return engine


async def apply_stream_moderation(
    raw_gen: AsyncGenerator,
    engine: ModerationEngineDynamicAC | None,
) -> AsyncGenerator[Any, None]:
    """流式审核代理：拦截 runner 输出，对含模型输出文本的事件做审核。

    审核层在 dict 层操作（事件包装层之前），审核改内容，包装改格式，两者正交。
    仅审核模型生成内容，不审核用户输入字段（输入审核在 check_input_query 阶段完成）。

    事件审核通过 _EVENT_HANDLERS 注册表分发，新增事件只需：
    1. 实现 handler 函数
    2. 在 _EVENT_HANDLERS 中注册一行

    Args:
        raw_gen: runner.run_streaming() 产出的原始 async generator
        engine: 审核引擎实例，None 时直接透传
    """
    if not engine:
        async for chunk in raw_gen:
            yield chunk
        return

    ctx = _ModerationCtx(engine)

    async for chunk in raw_gen:
        if chunk is None or not isinstance(chunk, dict):
            yield chunk
            continue

        event_type = chunk.get("event", "")
        ctx.last_created_time = chunk.get("createdTime", ctx.last_created_time)

        handler = _EVENT_HANDLERS.get(event_type)
        if handler is None:
            # 未注册的事件类型，直接透传
            yield chunk
            continue

        result = handler(chunk, engine, ctx)

        # handler 标记了中断（REPLY 阻断）
        if ctx.interrupted:
            # 1. sensitive 事件：携带 node_id/index 等上下文，前端据此匹配并替换文本
            yield engine.build_sensitive_event(
                ctx.int_msg,
                ctx.last_created_time,
                node_id=ctx.int_node_id,
                node_type=ctx.int_node_type,
                node_name=ctx.int_node_name,
                index=ctx.int_index,
            )
            # 2. message_end 事件：标记当前节点的消息为已完成，
            #    前端据此设置 isFinished=true 并停止 loading 指示
            yield {
                "event": "message_end",
                "data": {
                    "answer": ctx.int_msg,
                    "node_id": ctx.int_node_id,
                    "node_type": ctx.int_node_type,
                    "node_name": ctx.int_node_name,
                },
                "createdTime": ctx.last_created_time,
            }
            # 3. workflow_end 事件：通知前端工作流执行结束
            yield {
                "event": "workflow_end",
                "data": {"answer": ctx.int_msg},
                "createdTime": ctx.last_created_time,
            }
            break

        # handler 返回 None 表示吞掉该事件
        if result is not None:
            yield result

    # 流正常结束时，flush 流式状态机中残留的 buffer
    if not ctx.interrupted:
        rem_think = ctx.mods["think"].flush()
        rem_answer = ctx.mods["answer"].flush()
        if rem_think or rem_answer:
            yield {
                "event": "message",
                "data": {"think": rem_think, "answer": rem_answer},
                "createdTime": ctx.last_created_time,
            }


async def block_event_generator(
    fallback_msg: str,
    mode: str,
    execution_id: str,
) -> AsyncGenerator[dict, None]:
    """输入审核阻断事件生成器。

    根据 Runner 类型生成不同的终止事件序列，
    使用 runtime 内部格式（非 event_handler 包装后格式）。

    Args:
        fallback_msg: 阻断兜底话术
        mode: IR 中的 mode 字段 (workflow / ReAct / Controller 等)
        execution_id: 执行 ID
    """
    ts = int(time.time() * 1000)

    # 与 stream_response 一致，dict 序列化为 SSE 帧（data: <json>\n\n）后再 yield，
    # 否则 StreamingResponse 会对 dict 调用 .encode() 报 AttributeError。
    def _sse(d: dict) -> str:
        return f"data: {json.dumps(d, ensure_ascii=False)}\n\n"

    # 消息事件
    yield _sse({
        "event": "message",
        "data": {"answer": fallback_msg},
        "executionId": execution_id,
        "index": 0,
        "createdTime": ts,
    })

    # workflow 模式额外发送 workflow_end
    if mode == "workflow":
        yield _sse({
            "event": "workflow_end",
            "data": {"answer": fallback_msg},
            "executionId": execution_id,
            "index": 1,
            "createdTime": ts,
        })

    # done 事件
    yield _sse({
        "event": "done",
        "data": {},
        "executionId": execution_id,
        "index": 2 if mode == "workflow" else 1,
        "createdTime": ts,
    })
