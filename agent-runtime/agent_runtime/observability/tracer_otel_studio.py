# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""OtelWorkflowHandler 的本仓扩展：HTTP/API 节点业务失败标红（Jaeger 可见）。

为什么在 agent-studio 侧继承覆写：openjiuwen 上游 handler 不识别
business_error 标记（组件正常返回但该次调用失败，如 HTTP 4xx/5xx），因此
该场景在 Jaeger 上无错误显示。span 的写权限只在 handler，而 handler 的
实例化/注册点在本仓（agent_runtime/observability/tracer_otel.py），故通过
子类在 agent-studio 侧提供等价能力，openjiuwen 源码零改动（零上游依赖）。

实现要点：
- on_invoke（非异常分支）：识别 business_error 标记 → span 置 ERROR 并记录
  错误信息（只标故障事实轴，不改 openjiuwen.status 业务状态）；
- 错误语义三层落地：status.description 写白名单安全摘要（不含 body/url/headers/
  入参，description 不走内容脱敏）、http.response.status_code 与 error.type 写
  结构化字段供下游筛选聚合、error_message/business_error 保持 redact 脱敏；
- on_call_done：span 已处于 ERROR（business_error 标记或 trace_error 异常路径）
  时保留标红，不为 OK；正常完成（UNSET）才置 OK。

版本绑定与升级核对（重要）：本文件与 openjiuwen 版本强绑定——
1. on_call_done 为整段覆写（上游无扩展点），方法体复制自
   openjiuwen handler.on_call_done；
2. 依赖上游私有符号：_build_error_summary、_extract_retrieval_documents、
   _is_retrieval_component_span、_span_manager / _refresh_inputs_attribute /
   _flush_buffered_data / _set_workflow_end_attrs / _detach_state /
   _layer_root_spans / _component_spans；
3. 覆写点新增 on_invoke（异常挂起 + business_error）、on_post_invoke（降级清除
   未处理异常）与 on_call_done（层根终态判定），上游调整这些钩子的签名或调用
   顺序时须同步；
4. 终态语义：层根 Span 仅在“本层存在未处理异常且 outputs 为空”时写
   ERROR/description + openjiuwen.status=error，其余路径保持 OK/finish。
升级 openjiuwen 时须按清单核对：①上述私有符号是否存在/改名；②on_call_done 上游
是否新增收尾逻辑（清理/属性写入）需同步；③以 tests/unit_tests/observability/
test_tracer_otel_studio.py 全量回归兜底；符号缺失时 tracer_otel.setup_otel_tracer
会回退官方 handler（见 tracer_otel.py），保证不静默停用 OTel。
"""

import json
import re

from openjiuwen.core.common.logging import session_logger
from openjiuwen.core.graph.pregel import GraphInterrupt
from openjiuwen.core.session.tracer.data import NodeStatus
from openjiuwen.extensions.tracer_otel.handler import (
    OtelWorkflowHandler,
    _build_error_summary,
    _extract_retrieval_documents,
    _is_retrieval_component_span,
)
from openjiuwen.extensions.tracer_otel.redaction import redact
from openjiuwen.extensions.tracer_otel.semconv import (
    GEN_AI_RETRIEVAL_DOCUMENTS,
    OJ_PARENT_NODE_ID,
    OJ_STATUS,
    OJ_WORKFLOW_ERROR_MESSAGE,
    OJ_WORKFLOW_OUTPUTS,
)
from opentelemetry.trace import Status, StatusCode

# 业务失败标记使用的 span 属性键（与 HTTP 业务失败上报方约定的键名一致）
OJ_BUSINESS_ERROR = "openjiuwen.workflow.business_error"

# 结构化错误字段（OTel 语义约定，供下游按状态码筛选/聚合；不含业务内容，不参与脱敏）
HTTP_RESPONSE_STATUS_CODE = "http.response.status_code"
OJ_ERROR_TYPE = "error.type"

# status.description 不参与内容脱敏，摘要必须白名单拼装并限长：
# 只允许状态码/错误类别，body、url、headers、业务入参一律不得进入。
_SUMMARY_MAX_LEN = 256
# 用 fullmatch 匹配（等价 \Z）：避免 '$' 放行末尾换行，把内容带进不脱敏的 description
_SAFE_CODE_PATTERN = re.compile(r"[A-Za-z0-9_.\-]{1,32}")
_SAFE_REASON_PATTERN = re.compile(r"[A-Za-z0-9 ._\-]{1,64}")


class StudioOtelWorkflowHandler(OtelWorkflowHandler):
    """在官方 OtelWorkflowHandler 基础上支持 business_error 业务失败标红。"""

    async def on_call_start(
        self,
        invoke_id: str,
        metadata: dict = None,
        inputs=None,
        parent_node_id: str = "",
        **kwargs,
    ):
        """层根 Span 建立后暴露真实 OTel trace_id/span_id（issue 1754）。

        HTTP 层（响应头/SSE）在提交前读取请求级上下文，输出
        X-OTel-Trace-Id / traceresponse；调用方 TraceID 写
        openjiuwen.correlation.id（与 openjiuwen.trace.id 语义分离）。
        """
        await super().on_call_start(
            invoke_id,
            metadata=metadata,
            inputs=inputs,
            parent_node_id=parent_node_id,
            **kwargs,
        )
        state = self._span_manager.get(invoke_id)
        if state is None or self._layer_root_spans.get(invoke_id) is not state:
            return
        span_ctx = state.span.get_span_context()
        if span_ctx is None or not span_ctx.is_valid:
            return
        from agent_runtime.common.otel_trace_context import (
            get_business_trace_id,
            register_session_trace,
            set_otel_trace_context,
        )

        correlation_id = get_business_trace_id()
        trace_hex = format(span_ctx.trace_id, "032x")
        span_hex = format(span_ctx.span_id, "016x")
        set_otel_trace_context(trace_hex, span_hex, correlation_id)
        register_session_trace(
            str(kwargs.get("session_id") or ""),
            trace_hex,
            span_hex,
            correlation_id,
            str((metadata or {}).get("execution_id") or ""),
        )
        if correlation_id:
            state.span.set_attribute("openjiuwen.correlation.id", str(correlation_id))

    async def on_invoke(
        self,
        invoke_id: str,
        on_invoke_data: dict = None,
        exception: Exception = None,
        **kwargs,
    ):
        if exception is not None and not isinstance(exception, GraphInterrupt):
            # 只记录组件异常：层根 Span 自身异常会被 Core 在异常分支提前收尾，
            # 收尾时无法按正常路径清理，若记录会跨轮残留并污染同一 workflow_id
            # 的下一轮根 Span（根与 layer root 都不在 _component_spans 中）。
            state = self._span_manager.get(invoke_id)
            if state is not None and self._component_spans.get(invoke_id) is state:
                scope = self._unhandled_error_scope(invoke_id)
                pending = getattr(self, "_unhandled_errors", None)
                if pending is None:
                    pending = self._unhandled_errors = {}
                pending.setdefault(scope, {})[invoke_id] = _build_error_summary(
                    exception
                )
        await super().on_invoke(
            invoke_id,
            on_invoke_data=on_invoke_data,
            exception=exception,
            **kwargs,
        )
        if (
            exception is None
            and isinstance(on_invoke_data, dict)
            and "business_error" in on_invoke_data
        ):
            self._mark_business_error(invoke_id, on_invoke_data["business_error"])

    async def on_post_invoke(self, invoke_id: str, outputs=None, inputs=None, **kwargs):
        # 组件在异常被处理后继续正常返回（defaultOutputs / errorBranch /
        # 重试成功）：清除该组件在各层的未处理异常标记，避免根 Span 被误标为终止失败。
        self._clear_unhandled_error(invoke_id)
        await super().on_post_invoke(invoke_id, outputs, inputs=inputs, **kwargs)

    async def on_call_done(self, invoke_id: str, outputs=None, **kwargs):
        try:
            state = self._span_manager.get(invoke_id)
            if state is not None and state.recorded:
                self._refresh_inputs_attribute(invoke_id)
                self._flush_buffered_data(invoke_id)

            state = self._span_manager.pop(invoke_id)
            if state is None:
                # Span 已被异常分支提前收尾（重复收尾/根自身异常）：清理该 invoke_id
                # 的残留标记，避免同一 invoke_id 在下一轮被旧异常误标。
                self._clear_unhandled_error(invoke_id)
                return

            is_layer_root = self._layer_root_spans.get(invoke_id) is state
            pending = {}
            if is_layer_root:
                # 只取/清本层作用域的待定异常，避免并发或嵌套层收尾时误标/漏标。
                pending = (getattr(self, "_unhandled_errors", None) or {}).pop(
                    invoke_id, {}
                )
            terminal_summary = (
                next(iter(pending.values())) if outputs is None and pending else None
            )

            if state.recorded:
                if outputs is not None:
                    state.span.set_attribute(
                        OJ_WORKFLOW_OUTPUTS, redact(outputs, self._config)
                    )
                    if _is_retrieval_component_span(state.span):
                        documents = _extract_retrieval_documents(outputs)
                        if documents is not None:
                            state.span.set_attribute(
                                GEN_AI_RETRIEVAL_DOCUMENTS,
                                [redact(doc, self._config) for doc in documents],
                            )

                self._set_workflow_end_attrs(state)
                if terminal_summary is not None:
                    # 组件异常导致本层工作流终止（issue #1749）：根 Span 的
                    # 故障事实轴与业务终态轴同为 error，避免前端失败而 Trace 成功。
                    state.span.set_status(
                        Status(StatusCode.ERROR, description=terminal_summary)
                    )
                    state.span.set_attribute(OJ_STATUS, NodeStatus.ERROR.value)
                else:
                    state.span.set_attribute(OJ_STATUS, NodeStatus.FINISH.value)
                    # 故障事实轴：span 已处于 ERROR（business_error 标记或已降级
                    # 处理的 trace_error 路径）时保留标红；正常完成才置 OK。
                    if state.span.status.status_code != StatusCode.ERROR:
                        state.span.set_status(Status(StatusCode.OK))
            state.span.end()
            self._detach_state(state)

            # Remove from mappings
            self._layer_root_spans.pop(invoke_id, None)
            self._component_spans.pop(invoke_id, None)
            root_state = self._layer_root_spans.get("")
            if root_state is state:
                self._layer_root_spans.pop("", None)
        except Exception as exc:
            session_logger.warning("otel workflow handler: on_call_done failed: %s", exc)

    def _unhandled_error_scope(self, invoke_id: str) -> str:
        """未处理异常归属的 layer root invoke_id。

        进程级 handler 单例被所有工作流共享，未处理异常必须按层作用域隔离：
        优先取组件 Span 的 openjiuwen.parent_node_id（即所属层根 invoke_id），
        取不到时按父 SpanContext 反查 layer root，最后才回落到 invoke_id 自身。
        """
        state = self._span_manager.get(invoke_id)
        if state is not None:
            attrs = getattr(state.span, "attributes", None) or {}
            parent_node_id = attrs.get(OJ_PARENT_NODE_ID)
            if parent_node_id:
                return parent_node_id
            parent = getattr(state.span, "parent", None)
            if parent is not None:
                for root_state in list(self._layer_root_spans.values()):
                    root_ctx = root_state.span.get_span_context()
                    if root_ctx is not None and root_ctx.span_id == parent.span_id:
                        return root_state.invoke_id
        return invoke_id

    def _clear_unhandled_error(self, invoke_id: str) -> None:
        """清除指定组件在所有层作用域中的待定异常（invoke_id 全局唯一）。"""
        pending = getattr(self, "_unhandled_errors", None)
        if not pending:
            return
        for scope in list(pending.keys()):
            pending[scope].pop(invoke_id, None)
            if not pending[scope]:
                pending.pop(scope, None)

    def _mark_business_error(self, invoke_id: str, business_error: dict) -> None:
        """组件正常返回但该次调用失败（如 HTTP 4xx/5xx）：span 标红并保留错误信息。

        仅改故障事实轴（span.status=ERROR），不改变 openjiuwen.status 等
        业务状态属性（仍由引擎按正常完成记为 finish），流程与输出不受影响。

        错误语义分三层落地：
        - status.description：安全可读摘要，只由状态码/错误类别白名单拼装；
        - http.response.status_code / error.type：结构化字段，错误码不混入文本；
        - error_message / business_error：既有属性，继续走 redact 脱敏。
        """
        state = self._span_manager.get(invoke_id)
        if state is None or not state.recorded:
            return

        code = None
        reason = None
        body = None
        if isinstance(business_error, dict):
            code = business_error.get("status_code") or business_error.get("error_code")
            reason = business_error.get("reason")
            body = business_error.get("body")

        safe_code = self._safe_code(code)
        safe_reason = self._safe_reason(reason)

        # description 不走内容脱敏，因此只能用白名单字段拼装，绝不能复用含 body
        # 的 message，否则等于把响应体/业务入参明文写进标准错误位。
        summary = "HTTP request failed"
        if safe_code is not None:
            summary = f"{summary}: status code {safe_code}"
        if safe_reason is not None:
            summary = f"{summary}, {safe_reason}"
        state.span.set_status(
            Status(StatusCode.ERROR, description=summary[:_SUMMARY_MAX_LEN])
        )

        # 结构化字段：状态码保持整数类型，下游可做等值/区间筛选，不必解析文本。
        if isinstance(code, int) and not isinstance(code, bool):
            state.span.set_attribute(HTTP_RESPONSE_STATUS_CODE, code)
        if safe_code is not None:
            state.span.set_attribute(OJ_ERROR_TYPE, safe_code)

        message = str(business_error)
        if isinstance(business_error, dict):
            parts = []
            if code is not None:
                parts.append(f"status code {code}")
            if reason:
                parts.append(str(reason))
            if body:
                parts.append(str(body)[:300])
            if parts:
                message = "HTTP request failed: " + ", ".join(parts)
        # 与 on_call_done 对 outputs 的处理对齐：经 redact 脱敏（开启时哈希）并
        # 受 max_attr_length 限制，避免 body/url 等敏感信息明文落库。
        state.span.set_attribute(OJ_WORKFLOW_ERROR_MESSAGE, redact(message, self._config))
        try:
            safe_business_error = json.dumps(business_error, ensure_ascii=False)
        except (TypeError, ValueError):
            # 非 JSON 可序列化内容（bytes/异常对象等）兜底为字符串，避免观测链路抛错
            safe_business_error = str(business_error)
        state.span.set_attribute(
            OJ_BUSINESS_ERROR,
            redact(safe_business_error, self._config),
        )

    @staticmethod
    def _safe_code(code) -> str | None:
        """把状态码/错误码收敛成白名单短字符串；不合法一律丢弃。"""
        if code is None or isinstance(code, bool):
            return None
        text = str(code)
        return text if _SAFE_CODE_PATTERN.fullmatch(text) else None

    @staticmethod
    def _safe_reason(reason) -> str | None:
        """reason 由对端控制，只接受短英文短语，防止把内容注入不脱敏的 description。"""
        if not isinstance(reason, str):
            return None
        text = reason.strip()
        return text if _SAFE_REASON_PATTERN.fullmatch(text) else None
